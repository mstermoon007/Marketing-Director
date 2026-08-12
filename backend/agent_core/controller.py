"""
主控 Agent（Main Controller）
================================

对外统一入口。职责：
1. 管理会话（SessionManager），维护多轮上下文与追问状态；
2. 调度 LangGraph 状态图，根据意图路由到对应子 Agent；
3. 在每轮结束后持久化对话历史到记忆库（ChromaDB），实现上下文保持；
4. 把本轮解析出的 business_id / pending_intent 写回会话，支撑跨轮连续对话。

设计：进程级单例（``get_controller()``），共享同一个 ChromaDB 客户端与知识库。
"""

from __future__ import annotations

import logging
from datetime import date

from backend.agent_core.config import agent_core_config
from backend.agent_core.graph import build_agent_graph
from backend.agent_core.knowledge import KnowledgeBase
from backend.agent_core.memory import MemoryStore
from backend.agent_core.sessions import SessionManager
from backend.agent_core.state import (
    INTENT_CHAT,
    INTENT_DIAGNOSE,
    INTENT_LABELS,
    INTENT_PLAN,
    INTENT_REVIEW,
    INTENT_SCHEDULE,
)
from backend.agent_core.intent import classify_intent
from backend.agent_core.sub_agents.chat_agent import run_chat
from backend.agent_core.sub_agents.diagnosis_agent import run_diagnose
from backend.agent_core.sub_agents.planner_agent import run_plan
from backend.agent_core.sub_agents.reviewer_agent import run_review
from backend.agent_core.sub_agents.scheduler_agent import run_schedule


logger = logging.getLogger(__name__)

_DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _day_name(date_str: str, fallback_index: int) -> str:
    """由 ISO 日期推导中文星期名；解析失败时按序号回退。"""
    try:
        return _DAY_NAMES[date.fromisoformat(str(date_str)).weekday()]
    except (ValueError, TypeError):
        idx = max(1, int(fallback_index or 1))
        return _DAY_NAMES[(idx - 1) % 7]


def normalize_payload(tool_results: dict) -> dict:
    """把各子 Agent 异构的 ``tool_results`` 规整为前端稳定契约。

    子 Agent 内部键各不相同（diagnose / plan / schedule / review_parse / kpi），
    直接透传会让小程序侧写满 if-else 且极易因后端改名而静默失效。
    这里统一收敛为：

    ``{diagnosis, plan, plan_id, schedule, reminders, review, kpi, business_id}``

    未产出的部分一律省略（而非给 None），便于前端用「键存在」判断卡片类型。
    """
    if not tool_results:
        return {}

    out: dict = {}

    # ① 诊断：{"diagnose": {"ok": True, "report": {...}}}
    diag = tool_results.get("diagnose")
    if isinstance(diag, dict) and diag.get("ok") and diag.get("report"):
        out["diagnosis"] = diag["report"]

    # ② 计划：{"plan": {"ok": True, "plan": {...}, "diagnosis": {...}}}
    plan_res = tool_results.get("plan")
    if isinstance(plan_res, dict) and plan_res.get("ok") and plan_res.get("plan"):
        plan = plan_res["plan"]
        out["plan"] = plan
        if isinstance(plan, dict) and plan.get("id"):
            out["plan_id"] = plan["id"]
        # 计划里内嵌的诊断也一并暴露（诊断卡片优先取独立诊断结果）
        if "diagnosis" not in out and plan_res.get("diagnosis"):
            out["diagnosis"] = plan_res["diagnosis"]

    # ③ 排期：{"schedule": {"ok": True, "schedule": [...], "reminders": [...]}}
    sched_res = tool_results.get("schedule")
    if isinstance(sched_res, dict) and sched_res.get("ok"):
        days = []
        for d in sched_res.get("schedule", []) or []:
            if not isinstance(d, dict):
                continue
            days.append({
                "day_index": d.get("day_index"),
                "date": d.get("date", ""),
                "day_name": _day_name(d.get("date", ""), d.get("day_index", 1)),
                "focus": sched_res.get("goal") or "",
                "tasks": d.get("tasks", []) or [],
            })
        if days:
            out["schedule"] = days
        if sched_res.get("reminders"):
            out["reminders"] = sched_res["reminders"]
        if sched_res.get("business_id"):
            out["business_id"] = sched_res["business_id"]

    # ④ 复盘：由 review_parse + kpi 合成一个复盘卡片结构
    kpi = tool_results.get("kpi")
    if isinstance(kpi, dict) and kpi.get("rows") is not None:
        out["kpi"] = kpi
        parsed = tool_results.get("review_parse") or {}
        numbers = parsed.get("merged_numbers", {}) if isinstance(parsed, dict) else {}
        worked, didnt = [], []
        for row in kpi.get("rows", []):
            rate = row.get("achievement_rate")
            if rate is None:
                continue
            label = f"{row.get('metric')}（{row.get('actual')}/{row.get('target')}）"
            (worked if rate >= 100 else didnt).append(
                ("达标 " if rate >= 100 else "未达标 ") + label
            )
        out["review"] = {
            "summary": kpi.get("summary", ""),
            "numbers": numbers,
            "vs_target": kpi.get("rows", []),
            "what_worked": worked,
            "what_didnt": didnt,
            "suggestions": [],
        }

    return out


class MainController:
    """多 Agent 协作层主控。"""

    def __init__(self):
        self.memory = MemoryStore()
        self.kb = KnowledgeBase()
        self.sessions = SessionManager()
        self.graph = build_agent_graph(self.memory, self.kb)
        # 首次确保知识库已入库（为空则自动 ingest；rebuild 环境变量可强制重建）
        if agent_core_config.rebuild_knowledge:
            self.kb.ingest(force=True)
        else:
            self.kb.ensure_loaded()
        logger.info("主控 Agent 已就绪：知识库 %d 张卡片", self.kb.count())

    async def chat(
        self,
        session_id: str,
        user_id: str,
        message: str,
        business_id: str | None = None,
        files: list | None = None,
    ) -> dict:
        """处理一轮对话。

        Parameters
        ----------
        session_id : str
            会话 ID（多轮上下文键）。
        user_id : str
            用户 ID（记忆键）。
        message : str
            用户自然语言输入。
        business_id : str | None
            可选企业 ID；缺省时尝试复用会话已绑定企业。
        files : list | None
            上传文件路径列表（复盘用）。

        Returns
        -------
        dict：{response, intent, business_id, needs_clarification, data}
        """
        session = self.sessions.get_or_create(session_id, user_id)
        biz = business_id or session.business_id

        state = {
            "user_id": user_id,
            "business_id": biz or "",
            "session_id": session_id,
            "pending_intent": session.pending_intent or "",
            "user_message": message,
            "intent": "",
            "files": files or [],
            "memory_context": "",
            "knowledge_context": "",
            "tool_results": {},
            "response": "",
            "needs_clarification": False,
            "clarify_question": "",
            "error": "",
        }

        result = await self.graph.ainvoke(state)

        if result.get("business_id"):
            session.business_id = result["business_id"]

        if result.get("needs_clarification"):
            intent = result.get("intent") or ""
            session.pending_intent = (
                intent if intent in (INTENT_DIAGNOSE, INTENT_PLAN, INTENT_SCHEDULE, INTENT_REVIEW)
                else None
            )
        else:
            session.pending_intent = None

        # 持久化对话历史（上下文保持）
        self.memory.append_history(session_id, user_id, "user", message)
        self.memory.append_history(session_id, user_id, "assistant", result.get("response", ""))

        payload = normalize_payload(result.get("tool_results", {}))
        if result.get("business_id"):
            payload.setdefault("business_id", result["business_id"])

        return {
            "response": result.get("response", ""),
            "intent": result.get("intent", ""),
            "business_id": result.get("business_id", ""),
            "needs_clarification": result.get("needs_clarification", False),
            "data": payload,
        }

    async def chat_stream(
        self,
        session_id: str,
        user_id: str,
        message: str,
        business_id: str | None = None,
        files: list | None = None,
    ):
        """流式处理一轮对话，逐段 yield 思考事件（SSE 友好）。

        事件类型：
          - {"type": "intent", "intent", "intent_label"}
          - {"type": "thinking", "step"}            # Agent 思考过程提示
          - {"type": "tool", "name"}                 # 正在调用的标准化 Tool
          - {"type": "done", "response", "intent", "business_id", "needs_clarification", "data"}
          - {"type": "error", "message"}
        """
        session = self.sessions.get_or_create(session_id, user_id)
        biz = business_id or session.business_id

        state = {
            "user_id": user_id,
            "business_id": biz or "",
            "session_id": session_id,
            "pending_intent": session.pending_intent or "",
            "user_message": message,
            "intent": "",
            "files": files or [],
            "memory_context": "",
            "knowledge_context": "",
            "tool_results": {},
            "response": "",
            "needs_clarification": False,
            "clarify_question": "",
            "error": "",
        }

        try:
            intent = classify_intent(message, session.pending_intent or "")
            state["intent"] = intent
            yield {
                "type": "intent",
                "intent": intent,
                "intent_label": INTENT_LABELS.get(intent, ""),
            }
            yield {"type": "thinking", "step": f"已识别意图：{INTENT_LABELS.get(intent, intent)}，正在调度对应能力…"}

            runners = {
                INTENT_DIAGNOSE: run_diagnose,
                INTENT_PLAN: run_plan,
                INTENT_SCHEDULE: run_schedule,
                INTENT_REVIEW: run_review,
                INTENT_CHAT: run_chat,
            }
            runner = runners.get(intent, run_chat)
            result = await runner(state, self.memory, self.kb)

            if result.get("knowledge_context"):
                yield {"type": "thinking", "step": "已检索营销知识库（RAG），匹配相关方法卡片…"}
            for tool_name in result.get("tool_results", {}).keys():
                yield {"type": "tool", "name": str(tool_name)}
            yield {"type": "thinking", "step": "正在整理回复…"}

            # 汇总（与 graph._compose 一致）
            if result.get("needs_clarification"):
                result["response"] = result.get("clarify_question") or "需要更多信息才能继续。"
            elif result.get("error"):
                result["response"] = f"⚠️ {result['error']}"
            elif not result.get("response"):
                result["response"] = "（暂无结果）"

            # 写回会话状态（跨轮连续对话）
            if result.get("business_id"):
                session.business_id = result["business_id"]
            if result.get("needs_clarification"):
                session.pending_intent = (
                    intent if intent in (INTENT_DIAGNOSE, INTENT_PLAN, INTENT_SCHEDULE, INTENT_REVIEW)
                    else None
                )
            else:
                session.pending_intent = None

            # 持久化对话历史（上下文保持）
            self.memory.append_history(session_id, user_id, "user", message)
            self.memory.append_history(session_id, user_id, "assistant", result.get("response", ""))

            payload = normalize_payload(result.get("tool_results", {}))
            if result.get("business_id"):
                payload.setdefault("business_id", result["business_id"])
            if result.get("needs_clarification"):
                payload["needs_clarification"] = True
                payload["clarify_question"] = result.get("clarify_question", "")

            yield {
                "type": "done",
                "response": result.get("response", ""),
                "intent": result.get("intent", intent),
                "business_id": result.get("business_id", ""),
                "needs_clarification": result.get("needs_clarification", False),
                "data": payload,
            }
        except Exception as e:  # noqa: BLE001
            logger.exception("流式对话异常")
            yield {"type": "error", "message": str(e)}


_controller = None


def get_controller() -> MainController:
    """返回（惰性创建）进程级主控单例。"""
    global _controller
    if _controller is None:
        _controller = MainController()
    return _controller
