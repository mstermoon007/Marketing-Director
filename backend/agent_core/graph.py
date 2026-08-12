"""
LangGraph 状态图装配
================================

定义多 Agent 协作层的核心状态图：

    START → classify（意图分类）
          → 路由 → diagnose / plan / schedule / review / chat（子 Agent 节点）
          → compose（汇总回复）
          → END

- ``classify``：基于规则（可选 LLM）分类意图，复用会话级 pending_intent 处理追问回流。
- 各子 Agent 节点：调用标准化工具 + RAG 检索 + 记忆读写，产出结构化结果。
- ``compose``：按优先级收口（追问 > 错误 > 正常回复），保证最终一定有 response。

节点函数通过闭包捕获共享的 memory / kb 实例。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.agent_core.intent import classify_intent
from backend.agent_core.state import (
    INTENT_CHAT,
    INTENT_DIAGNOSE,
    INTENT_PLAN,
    INTENT_REVIEW,
    INTENT_SCHEDULE,
    AgentState,
)
from backend.agent_core.sub_agents.chat_agent import run_chat
from backend.agent_core.sub_agents.diagnosis_agent import run_diagnose
from backend.agent_core.sub_agents.planner_agent import run_plan
from backend.agent_core.sub_agents.reviewer_agent import run_review
from backend.agent_core.sub_agents.scheduler_agent import run_schedule


def _compose(state: dict) -> dict:
    """汇总节点：保证最终一定有可读回复。"""
    if state.get("needs_clarification"):
        state["response"] = state.get("clarify_question") or "需要更多信息才能继续。"
        return state
    if state.get("error"):
        state["response"] = f"⚠️ {state['error']}"
        return state
    if not state.get("response"):
        state["response"] = "（暂无结果）"
    return state


def build_agent_graph(memory, kb):
    """构建并编译 Agent 状态图。"""
    g = StateGraph(AgentState)

    async def _classify(s):
        return {**s, "intent": classify_intent(s.get("user_message", ""), s.get("pending_intent"))}

    async def _diagnose(s):
        return await run_diagnose(s, memory, kb)

    async def _plan(s):
        return await run_plan(s, memory, kb)

    async def _schedule(s):
        return await run_schedule(s, memory, kb)

    async def _review(s):
        return await run_review(s, memory, kb)

    async def _chat(s):
        return await run_chat(s, memory, kb)

    g.add_node("classify", _classify)
    g.add_node("diagnose", _diagnose)
    g.add_node("plan", _plan)
    g.add_node("schedule", _schedule)
    g.add_node("review", _review)
    g.add_node("chat", _chat)
    g.add_node("compose", _compose)

    g.add_edge(START, "classify")
    g.add_conditional_edges(
        "classify",
        lambda s: s["intent"],
        {
            INTENT_DIAGNOSE: "diagnose",
            INTENT_PLAN: "plan",
            INTENT_SCHEDULE: "schedule",
            INTENT_REVIEW: "review",
            INTENT_CHAT: "chat",
        },
    )
    for node in ("diagnose", "plan", "schedule", "review", "chat"):
        g.add_edge(node, "compose")
    g.add_edge("compose", END)

    return g.compile()
