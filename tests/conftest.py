"""
pytest 全局配置和 fixtures

核心：MockLLMProvider 替代真实 LLM 调用，让测试不依赖 API Key。
数据库隔离：每次运行使用独立临时数据库，不污染 data/app.db。
"""

import sys
import json
import atexit
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# 确保项目根目录在 path 中
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 测试数据库隔离：创建临时目录，强制覆盖 DATABASE_URL ──
#   必须在任何 backend.* import 之前执行，因为 settings.py 在模块加载时评估 DATABASE_URL。
_test_db_dir = tempfile.mkdtemp(prefix="pytest_marketing_")
_test_db_path = f"sqlite+aiosqlite:///{_test_db_dir}/test.db"
atexit.register(lambda: shutil.rmtree(_test_db_dir, ignore_errors=True))

import os as _os
_os.environ["DATABASE_URL"] = _test_db_path
_os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-jwt-secret-do-not-use-in-prod")

# 初始化测试数据库表结构
from backend.db.models import init_db as _init_db_func

_init_db_func()

# ── Fake module helper + stub backend.agent_core ──
#   避免导入 chromadb/langgraph 等未安装重依赖，使 API 路由集成测试可正常加载。
#   agent_core 测试通过 test_agent_core.py 顶层的 conftest override 注入真实函数 stub。

import sys as _sys


def _fake_module(name: str, **attrs):
    """创建带 __spec__ / __path__ 的假模块对象，支持任意属性访问。"""
    class _FakeMod:
        def __getattr__(self, key):
            return None
    mod = _FakeMod()
    for k, v in attrs.items():
        setattr(mod, k, v)
    mod.__name__ = name
    mod.__spec__ = type("_FakeSpec", (), {
        "name": name, "loader": None, "origin": None,
        "submodule_search_locations": None,
    })()
    mod.__file__ = None
    mod.__path__ = []
    mod.__package__ = name
    return mod


async def _fake_get_controller():
    """Stub get_controller — 返回带空方法的假 Controller。"""
    return type("_Ctrl", (), {
        "chat": type("_C", (), {"ainvoke": None})(),
        "run_diagnosis": None,
        "run_executor": None,
    })()


# 先加载 state.py（无重依赖），避免父模块 stub 阻断子模块解析
import importlib as _importlib
_state_spec = _importlib.util.spec_from_file_location(
    "backend.agent_core.state",
    str(PROJECT_ROOT / "backend" / "agent_core" / "state.py"),
)
_state_mod = _importlib.util.module_from_spec(_state_spec)
_sys.modules["backend.agent_core.state"] = _state_mod
_state_spec.loader.exec_module(_state_mod)

_agent_core_stub = _fake_module("backend.agent_core",
    get_controller=_fake_get_controller,
    MainController=type("_MC", (), {})(),
)
_sys.modules["backend.agent_core"] = _agent_core_stub
for _sub in ("controller", "graph", "tools", "knowledge", "_chroma", "embeddings",
             "common", "learning", "config",
             "intent", "sessions", "memory",
             "sub_agents", "sub_agents.chat_agent",
             "sub_agents.diagnosis_agent", "sub_agents.executor_agent",
             "sub_agents.reviewer_agent", "sub_agents.planner_agent",
             "sub_agents.scheduler_agent"):
    _full = f"backend.agent_core.{_sub}"
    if _full not in _sys.modules:
        _sys.modules[_full] = _fake_module(_full)

# ── 注入 agent_core stub 函数的真实实现 ──
#   以下函数直接复制自 src/agent_core/tools.py / intent.py / memory.py，
#   仅去掉 langgraph/chromadb 等重依赖，保证 agent_core 测试可用。

from logging import getLogger as _getLogger
_log = _getLogger("conftest.stub")

# -- classify_intent（规则匹配，与原版一致） --
from backend.agent_core.state import (
    INTENT_CHAT, INTENT_DIAGNOSE, INTENT_PLAN, INTENT_REVIEW, INTENT_SCHEDULE,
)

_REVIEW_KW = ["复盘", "回顾", "总结上周", "上周", "本周总结", "对比", "达成", "上传截图", "上传数据", "上传文件", "截图", "看看数据"]
_DIAGNOSE_KW = ["诊断", "把脉", "打分", "健康度", "体检", "分析一下", "问题在哪", "哪里有问题", "什么问题", "现状", "诊断报告"]
_PLAN_KW = ["计划", "方案", "7天", "七天", "执行清单", "怎么做", "策略", "本周", "行动", "落地", "规划"]
_SCHEDULE_KW = ["日程", "排期", "安排", "提醒", "每天", "周几", "排到", "时间表", "提醒我"]
_COMMAND_KW = _REVIEW_KW + _DIAGNOSE_KW + _PLAN_KW + _SCHEDULE_KW + ["诊断", "计划", "排期", "复盘", "你好", "你是", "什么是", "怎么", "如何"]


def _stub_classify_intent(text, pending_intent=None):
    text = (text or "").strip()
    if pending_intent and 0 < len(text) <= 40 and not any(k in text for k in _COMMAND_KW):
        return pending_intent
    if any(k in text for k in _REVIEW_KW):
        return INTENT_REVIEW
    if any(k in text for k in _DIAGNOSE_KW):
        return INTENT_DIAGNOSE
    if any(k in text for k in _SCHEDULE_KW):
        return INTENT_SCHEDULE
    if any(k in text for k in _PLAN_KW):
        return INTENT_PLAN
    return INTENT_CHAT


_sys.modules["backend.agent_core.intent"].classify_intent = _stub_classify_intent

# -- calculate_kpi（纯函数，与原版完全一致） --
from typing import Optional as _Optional


def _stub_calculate_kpi(numbers, targets=None, previous=None):
    targets = targets or {}
    rows = []
    for k, actual in numbers.items():
        try:
            actual_f = float(actual)
        except (TypeError, ValueError):
            actual_f = 0.0
        t = targets.get(k)
        try:
            t_f = float(t) if t is not None else None
        except (TypeError, ValueError):
            t_f = None
        rate = round(actual_f / t_f * 100, 1) if (t_f and t_f > 0) else None
        rows.append({"metric": k, "actual": actual_f, "target": t_f, "achievement_rate": rate})
    rates = [r["achievement_rate"] for r in rows if r["achievement_rate"] is not None]
    overall = round(sum(rates) / len(rates), 1) if rates else None

    def _g(n):
        for r in rows:
            if r["metric"] == n:
                return r["actual"]
        return None

    derived = {}
    consult = _g("咨询量")
    deal = _g("成交量")
    if consult and consult > 0 and deal is not None:
        derived["成交转化率(%)"] = round(deal / consult * 100, 1)
    visit = _g("访客数") or _g("曝光量")
    if visit and visit > 0 and consult is not None:
        derived["咨询转化率(%)"] = round(consult / visit * 100, 1)
    new_cust = _g("新增客户")
    revenue = _g("成交额") or _g("营业额")
    if new_cust and new_cust > 0 and revenue is not None:
        derived["客单价"] = round(revenue / new_cust, 1)
    trend = []
    if previous:
        for k, cur in numbers.items():
            if k in previous:
                try:
                    prev_f = float(previous[k])
                    cur_f = float(cur)
                except (TypeError, ValueError):
                    continue
                delta = round(cur_f - prev_f, 1)
                pct = round(delta / prev_f * 100, 1) if prev_f else None
                trend.append({"metric": k, "previous": prev_f, "current": cur_f, "delta": delta, "pct": pct})
    summary = f"整体目标达成率约 {overall}%" if overall is not None else "未提供目标，无法计算达成率"
    if derived:
        summary += "；派生指标：" + "，".join(f"{k}={v}" for k, v in derived.items())
    return {"rows": rows, "overall_achievement": overall, "derived": derived, "trend": trend, "summary": summary}


_sys.modules["backend.agent_core.tools"].calculate_kpi = _stub_calculate_kpi

# -- search_marketing_knowledge（简化 stub：返回固定卡片） --
async def _stub_search_knowledge(query, category=None, top_k=None):
    cards = [
        {"name": "餐饮短视频引流指南", "category": "获客", "principles": "内容种草+POI定位"},
        {"name": "餐饮获客案例集", "category": "获客", "principles": "老客裂变+美团运营"},
        {"name": "朋友圈营销7步法", "category": "私域", "principles": "信任建设+互动设计"},
    ]
    filtered = [c for c in cards if not category or c.get("category") == category]
    return {"ok": True, "query": query, "count": len(filtered), "cards": filtered[:top_k or 3]}


_sys.modules["backend.agent_core.tools"].search_marketing_knowledge = _stub_search_knowledge

# -- diagnose_business（简化 stub：离线规则评分） --
async def _stub_diagnose_business(business_id):
    from sqlalchemy import select
    from backend.db.models import AsyncSessionLocal, BusinessRecord, DiagnosisRecord

    async with AsyncSessionLocal() as s:
        rec = (await s.execute(select(BusinessRecord).filter_by(id=business_id))).scalar_one_or_none()
        if not rec:
            return {"ok": False, "error": f"企业不存在：{business_id}"}
        existing = (await s.execute(select(DiagnosisRecord).filter_by(business_id=business_id))).scalar_one_or_none()
        if existing and existing.overall_score is not None:
            return {"ok": True, "report": {"overall_score": existing.overall_score}, "cached": True}
        score = 65 if rec.industry == "餐饮" else 60
        d = DiagnosisRecord(business_id=business_id, overall_score=score, score_summary="离线规则评分")
        s.add(d)
        await s.commit()
    return {"ok": True, "report": {"overall_score": score}}


_sys.modules["backend.agent_core.tools"].diagnose_business = _stub_diagnose_business

# -- schedule_task（完全复制原版，无重依赖） --
from datetime import date as _date, datetime as _datetime, timedelta as _timedelta
_SLOTS = ["上午", "下午", "晚上"]


async def _stub_schedule_task(business_id, items=None, days=7, start_date=None, goal=None):
    if not items:
        from sqlalchemy import select
        from backend.db.models import AsyncSessionLocal, ExecutionPlanRecord
        async with AsyncSessionLocal() as session:
            plan_rec = (await session.execute(
                select(ExecutionPlanRecord).filter_by(business_id=business_id)
                .order_by(ExecutionPlanRecord.created_at.desc())
            )).scalars().first()
            if not plan_rec:
                return {"ok": False, "error": "未提供任务列表，且该企业暂无执行计划可加载"}
            loaded = []
            for d in (plan_rec.days or []):
                if isinstance(d, dict):
                    for t in d.get("tasks", []):
                        title = t.get("title") if isinstance(t, dict) else str(t)
                        if title:
                            loaded.append(title)
            items = loaded
            if not goal:
                goal = plan_rec.theme
    if not items:
        return {"ok": False, "error": "没有可排期的任务。"}
    try:
        start = _datetime.fromisoformat(start_date).date() if start_date else _date.today()
    except ValueError:
        start = _date.today()
    total = len(items)
    per_day = max(1, (total + days - 1) // days)
    per_day = min(per_day, 5)
    schedule = []
    reminders = []
    idx = 0
    for day_i in range(days):
        day_tasks = []
        for _ in range(per_day):
            if idx >= total:
                break
            title = items[idx]
            slot = _SLOTS[idx % len(_SLOTS)]
            day_tasks.append({"title": title, "time_slot": slot})
            idx += 1
        if not day_tasks:
            break
        cur = start + _timedelta(days=day_i)
        schedule.append({"day_index": day_i + 1, "date": cur.isoformat(), "tasks": day_tasks})
        task_summary = "；".join(t["title"] for t in day_tasks)
        reminders.append({
            "remind_at": f"{cur.isoformat()}T09:00:00",
            "title": f"第{day_i + 1}天执行提醒",
            "content": f"今日目标：{goal or '推进营销动作'}。任务：{task_summary}",
        })
    return {"ok": True, "business_id": business_id, "goal": goal, "schedule": schedule, "reminders": reminders, "total_tasks": len(items)}


_sys.modules["backend.agent_core.tools"].schedule_task = _stub_schedule_task

# -- persist_todos（复制自 src/agent_core/tools.py，纯 DB，无重依赖）--
#   loops.py 的 confirm_plan 调用它把计划落库为 todos；保持与真实实现一致的契约。
async def _stub_persist_todos(business_id, user_id, plan_id, day_groups):
    import json as _json
    from backend.db.models import AsyncSessionLocal, TodoRecord, select

    rows = []
    for g in day_groups or []:
        day_index = g.get("day_index") or 0
        date_str = g.get("date") or ""
        for t in g.get("tasks", []) or []:
            if isinstance(t, dict):
                title = t.get("title")
                how_to = t.get("how_to")
                checklist = t.get("checklist")
            else:
                title = str(t)
                how_to = None
                checklist = None
            if not title:
                continue
            rows.append(TodoRecord(
                business_id=business_id,
                user_id=user_id,
                plan_id=plan_id,
                day_index=day_index,
                date=date_str,
                title=title,
                time_slot=t.get("time_slot") if isinstance(t, dict) else None,
                status="pending",
                how_to=how_to,
                checklist=_json.dumps(checklist, ensure_ascii=False) if isinstance(checklist, list) else None,
            ))

    async with AsyncSessionLocal() as session:
        # 替换该计划（或该企业未归属计划的）历史待办，保证幂等
        stmt = select(TodoRecord).filter_by(business_id=business_id)
        if plan_id:
            stmt = select(TodoRecord).filter_by(plan_id=plan_id)
        old = (await session.execute(stmt)).scalars().all()
        for o in old:
            await session.delete(o)
        session.add_all(rows)
        await session.commit()

    return {"ok": True, "persisted": len(rows), "plan_id": plan_id}


_sys.modules["backend.agent_core.tools"].persist_todos = _stub_persist_todos


# -- generate_plan / upload_and_parse_data（闭环 regenerate / 上传解析用）--
async def _stub_generate_plan(business_id):
    """返回一个带 id 的草稿计划并落库，供 regenerate 端点返回。"""
    plan_id = f"plan_{_uuid.uuid4().hex[:8]}"
    days = [{
        "day_index": 1, "day_name": "周一", "date": _date.today().isoformat(),
        "focus": "获客", "tasks": [
            {"title": "拍3条短视频", "time_slot": "上午", "how_to": "展示招牌菜", "checklist": ["脚本", "拍摄"]},
            {"title": "优化美团店铺", "time_slot": "下午", "how_to": "完善菜单与团购", "checklist": ["头图", "套餐"]},
        ],
    }]
    from backend.db.models import AsyncSessionLocal, ExecutionPlanRecord
    async with AsyncSessionLocal() as session:
        session.add(ExecutionPlanRecord(
            id=plan_id, business_id=business_id, diagnosis_id="",
            start_date=_date.today(), theme="本周引流", key_metrics={},
            status="draft", days=days,
        ))
        await session.commit()
    return {"ok": True, "plan": {"id": plan_id, "days": days, "theme": "本周引流"}, "diagnosis": {"overall_score": 65}}


_sys.modules["backend.agent_core.tools"].generate_plan = _stub_generate_plan


async def _stub_upload_and_parse_data(files):
    """上传解析桩：不触达真实多模态模型，返回空合并结果。"""
    return {
        "ok": True,
        "merged_numbers": {},
        "file_count": len(files or []),
        "csv_count": 0,
        "image_count": 0,
        "unknown_files": list(files or []),
        "errors": [],
    }


_sys.modules["backend.agent_core.tools"].upload_and_parse_data = _stub_upload_and_parse_data

# -- 持续学习：注入真实 record_feedback / get_strategy_scores / apply_strategy_scores --
#   learning.py 仅依赖 sqlalchemy + db.models（无 chromadb/langgraph 重依赖），可直接加载。
#   loops.py 的 /agent/feedback 调用 record_feedback，需保留真实 DB 落库逻辑。
import importlib.util as _ilu

_learn_spec = _ilu.spec_from_file_location(
    "backend.agent_core._learning_real",
    str(PROJECT_ROOT / "backend" / "agent_core" / "learning.py"),
)
_learn_mod = _ilu.module_from_spec(_learn_spec)
_learn_spec.loader.exec_module(_learn_mod)
_sys.modules["backend.agent_core.learning"].record_feedback = _learn_mod.record_feedback
_sys.modules["backend.agent_core.learning"].get_strategy_scores = _learn_mod.get_strategy_scores
_sys.modules["backend.agent_core.learning"].apply_strategy_scores = _learn_mod.apply_strategy_scores

# -- MemoryStore（简化 stub，无 ChromaDB） --
import time as _time
import uuid as _uuid


class _StubMemoryStore:
    def __init__(self):
        self._history = {}
        self._profiles = {}

    def append_history(self, session_id, user_id, role, content):
        key = session_id
        if key not in self._history:
            self._history[key] = []
        self._history[key].append({
            "session_id": session_id, "user_id": user_id, "role": role,
            "content": content, "timestamp": _time.time(),
        })

    def get_history(self, session_id, limit=20):
        items = self._history.get(session_id, [])
        return items[-limit:] if limit else items

    def save_profile(self, user_id, label, metadata=None):
        self._profiles[user_id] = {"label": label, "metadata": metadata or {}, "updated_at": _time.time()}

    def get_profile(self, user_id):
        return self._profiles.get(user_id)


_sys.modules["backend.agent_core.memory"].MemoryStore = _StubMemoryStore
# Also expose at top-level for get_controller
_MEM_INST = _StubMemoryStore()

# -- get_controller（简化 stub，支持 chat / chat_stream / memory） --
import json as _json


_INTENT_LABELS = {
    "diagnose": "营销诊断", "plan": "生成计划", "schedule": "排程提醒",
    "review": "数据复盘", "chat": "智能问答",
}

_RESPONSE_MAP = {
    "diagnose": "已为你诊断餐饮店（成都川菜），整体健康度65分。主要问题：获客渠道单一、老客复购率低。",
    "plan": "已生成本周7天执行计划，聚焦线下获客与美团运营。",
    "chat": "短视频引流的核心是内容种草+POI定位，建议每周发布3-5条15秒美食特写视频。",
    "schedule": "已排程完成。",
    "review": "复盘报告已生成。",
}


class _StubController:
    """测试用主控桩：意图路由 + 记忆 + 结构化 data。

    与真实 ``MainController`` 保持同一份对外契约（intent / business_id /
    response / data），仅在无 LLM 环境下用确定性输出替代真实子 Agent，
    使闭环 DB 流程（诊断→计划→确认→排期→反馈）可在测试中稳定跑通。
    """

    def __init__(self):
        self.memory = _MEM_INST
        self._session_bids = {}  # 会话级 business_id 复用

    def _resolve_bid(self, session_id: str) -> str:
        if session_id not in self._session_bids:
            self._session_bids[session_id] = f"biz_{_uuid.uuid4().hex[:8]}"
        return self._session_bids[session_id]

    def _diagnosis_data(self, bid: str) -> dict:
        return {
            "diagnosis": {
                "overall_score": 65,
                "score_summary": "离线规则评分",
                "score_breakdown": {},
                "top3_problems": [],
                "strategy_summary": "聚焦定位与获客渠道",
                "this_week_focus": "本周重点获客",
            },
            "business_id": bid,
        }

    def _plan_data(self, bid: str):
        """返回 (plan_id, days, data)。days 同时用于落库与闭环校验。"""
        plan_id = f"plan_{_uuid.uuid4().hex[:8]}"
        days = [{
            "day_index": 1, "day_name": "周一", "date": _date.today().isoformat(),
            "focus": "获客", "tasks": [
                {"title": "拍3条短视频", "time_slot": "上午", "how_to": "展示招牌菜", "checklist": ["脚本", "拍摄"]},
                {"title": "优化美团店铺", "time_slot": "下午", "how_to": "完善菜单与团购", "checklist": ["头图", "套餐"]},
            ],
        }]
        data = {"plan": {"id": plan_id, "days": days, "theme": "本周引流"}, "business_id": bid}
        return plan_id, days, data

    async def _persist_stub_plan(self, business_id: str, plan_id: str, days: list) -> None:
        """把计划落库为 ExecutionPlanRecord，供 confirm 阶段读取（闭环一致性）。"""
        from backend.db.models import AsyncSessionLocal, ExecutionPlanRecord
        async with AsyncSessionLocal() as session:
            session.add(ExecutionPlanRecord(
                id=plan_id, business_id=business_id, diagnosis_id="",
                start_date=_date.today(), theme="本周引流", key_metrics={},
                status="draft", days=days,
            ))
            await session.commit()

    def _classify(self, session_id, message):
        intent = _stub_classify_intent(message)
        bid = self._resolve_bid(session_id)
        response = _RESPONSE_MAP.get(intent, "已收到您的消息。")
        return intent, bid, response

    async def chat(self, session_id, user_id, message, **_kwargs):
        intent, bid, response = self._classify(session_id, message)
        data: dict = {}
        if intent == "diagnose":
            data = self._diagnosis_data(bid)
        elif intent == "plan":
            _plan_id, days, data = self._plan_data(bid)
            await self._persist_stub_plan(bid, _plan_id, days)

        # 写入记忆库
        self.memory.append_history(session_id, user_id, "user", message)
        self.memory.append_history(session_id, user_id, "assistant", response)

        return {"intent": intent, "business_id": bid, "response": response,
                "needs_clarification": False, "data": data}

    async def chat_stream(self, session_id, user_id, message, **_kwargs):
        intent, bid, response = self._classify(session_id, message)
        data: dict = {}
        if intent == "diagnose":
            data = self._diagnosis_data(bid)
        elif intent == "plan":
            _plan_id, days, data = self._plan_data(bid)
            await self._persist_stub_plan(bid, _plan_id, days)

        yield {"type": "intent", "intent": intent, "intent_label": _INTENT_LABELS.get(intent, intent)}
        yield {"type": "thinking", "content": "正在分析..."}
        yield {"type": "done", "response": response, "intent": intent, "business_id": bid, "needs_clarification": False, "data": data}

        # Write to memory
        self.memory.append_history(session_id, user_id, "user", message)
        self.memory.append_history(session_id, user_id, "assistant", response)


_CTRL = _StubController()


def _stub_get_controller():
    return _CTRL


_sys.modules["backend.agent_core"].get_controller = _stub_get_controller

# 在所有 LLM 测试中，模拟 API Key 已配置 → LLM 路径会被走（实际调用被 Mock 替代）
_os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-dummy-for-pytest")

from backend.models.business import BusinessProfile
from backend.models.diagnosis import DiagnosisReport
from backend.models.execution import SevenDayPlan
from backend.models.review import ReviewReport

from tests.fixtures.industries import ALL_INDUSTRIES


# ──────────────────────────────────────────────
# Mock LLM Provider
# ──────────────────────────────────────────────

class MockLLMProvider:
    """
    Mock LLM Provider

    根据调用时的 system_prompt 内容判断是哪个 Agent 在调用，
    返回对应的预设 JSON 响应。
    """

    def __init__(self):
        self.calls = []  # 记录所有调用，用于断言
        self._diagnosis_response = None
        self._executor_response = None
        self._review_response = None
        self._vision_response = None
        self._executor_retry_responses = []  # 用于测试重试逻辑
        self._retry_count = 0

    def set_responses(self, diagnosis=None, executor=None, review=None, vision=None):
        """设置各 Agent 的 Mock 响应"""
        self._diagnosis_response = diagnosis
        self._executor_response = executor
        self._review_response = review
        self._vision_response = vision

    def set_executor_retry_sequence(self, responses):
        """设置执行引擎的重试响应序列（用于测试约束验证重试）"""
        self._executor_retry_responses = list(responses)
        self._retry_count = 0

    async def chat(self, system_prompt, user_message, json_mode=False, model=None, temperature=None):
        """Mock chat 方法"""
        self.calls.append({
            "method": "chat",
            "system_prompt": system_prompt,
            "user_message": user_message,
            "json_mode": json_mode,
        })

        # 按 Agent 特征关键词匹配 — 注意顺序：更具体的关键词优先，
        # 避免"诊断"误匹配 executor/reviewer prompt 中出现的"诊断结论"字样。
        if "执行教练" in system_prompt or "7天执行清单" in system_prompt:
            if self._executor_retry_responses:
                idx = min(self._retry_count, len(self._executor_retry_responses) - 1)
                resp = self._executor_retry_responses[idx]
                self._retry_count += 1
                if isinstance(resp, str):
                    return resp
                return json.dumps(resp, ensure_ascii=False)
            if self._executor_response is not None:
                if isinstance(self._executor_response, str):
                    return self._executor_response
                return json.dumps(self._executor_response, ensure_ascii=False)

        if "数据分析师" in system_prompt or "复盘报告" in system_prompt:
            if self._review_response is not None:
                if isinstance(self._review_response, str):
                    return self._review_response
                return json.dumps(self._review_response, ensure_ascii=False)

        if "营销顾问" in system_prompt or "营销诊断" in system_prompt:
            if self._diagnosis_response is not None:
                if isinstance(self._diagnosis_response, str):
                    return self._diagnosis_response
                return json.dumps(self._diagnosis_response, ensure_ascii=False)

        # 默认返回空 JSON
        return "{}"

    async def chat_with_images(self, system_prompt, image_paths, model=None):
        """Mock 多模态调用"""
        self.calls.append({
            "method": "chat_with_images",
            "system_prompt": system_prompt,
            "image_paths": image_paths,
        })

        if self._vision_response is not None:
            if isinstance(self._vision_response, str):
                return self._vision_response
            return json.dumps(self._vision_response, ensure_ascii=False)

        return '{"numbers": {}}'


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """提供 MockLLMProvider 实例"""
    return MockLLMProvider()


@pytest.fixture
def patched_llm(mock_llm):
    """替换全局 LLMProvider 单例为 Mock。

    同时模拟「API Key 已配置」：``DiagnosisAgent`` 等以 ``llm_config.text_api_key``
    作为是否走 LLM 路径的开关，而 ``settings.llm_config`` 在导入时即读取环境变量，
    测试环境无真实 Key。这里显式置位，使 Agent 真正走到 LLM 调用（实际由 mock 替代），
    避免出现「测试靠本地规则引擎兜底、与生产 LLM 路径漂移」的不一致。
    """
    from backend.config.settings import llm_config

    _orig_key = llm_config.text_api_key
    llm_config.text_api_key = _os.environ.get("DEEPSEEK_API_KEY", "sk-test-dummy-for-pytest")
    try:
        with patch("backend.services.llm._llm_provider", mock_llm):
            with patch("backend.services.llm.get_llm_provider", return_value=mock_llm):
                with patch("backend.agents.diagnosis.get_llm_provider", return_value=mock_llm):
                    with patch("backend.agents.executor.get_llm_provider", return_value=mock_llm):
                        with patch("backend.agents.reviewer.get_llm_provider", return_value=mock_llm):
                            yield mock_llm
    finally:
        llm_config.text_api_key = _orig_key


@pytest.fixture(params=list(ALL_INDUSTRIES.keys()))
def industry_case(request):
    """参数化 fixture：遍历5个行业测试用例"""
    return ALL_INDUSTRIES[request.param]


@pytest.fixture
def industry_name(request):
    """当前行业名称"""
    return request.param


# ──────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────

def make_profile(industry_key: str) -> BusinessProfile:
    """从行业测试数据创建 BusinessProfile"""
    data = ALL_INDUSTRIES[industry_key]["profile_data"]
    return BusinessProfile(
        id=f"test_{industry_key}",
        **data,
    )


def make_diagnosis(industry_key: str) -> DiagnosisReport:
    """从行业测试数据创建 DiagnosisReport"""
    data = ALL_INDUSTRIES[industry_key]["diagnosis_resp"]
    return DiagnosisReport.from_ai_response(
        business_id=f"test_{industry_key}",
        data=data,
    )


def make_plan(industry_key: str) -> SevenDayPlan:
    """从行业测试数据创建 SevenDayPlan"""
    from datetime import date
    data = ALL_INDUSTRIES[industry_key]["executor_resp"]
    return SevenDayPlan.from_ai_response(
        diagnosis_id=f"diag_{industry_key}",
        business_id=f"test_{industry_key}",
        start_date=date(2026, 7, 29),
        data=data,
    )


def make_review(industry_key: str) -> ReviewReport:
    """从行业测试数据创建 ReviewReport"""
    data = ALL_INDUSTRIES[industry_key]["review_resp"]
    return ReviewReport.from_ai_response(
        plan_id=f"plan_{industry_key}",
        business_id=f"test_{industry_key}",
        data=data,
    )


# ──────────────────────────────────────────────
# pytest hook: 注册 --update-snapshot 选项
# ──────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshot",
        action="store_true",
        default=False,
        help="更新 Prompt 快照基线",
    )
