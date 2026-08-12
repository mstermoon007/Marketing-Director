"""
Agent 状态定义
================================

LangGraph 状态图的共享状态（AgentState）。所有节点读取并局部更新该状态，
最终由 compose_response 节点汇总成回复。
"""

from __future__ import annotations

from typing import Optional, TypedDict


# 意图常量
INTENT_DIAGNOSE = "diagnose"
INTENT_PLAN = "plan"
INTENT_SCHEDULE = "schedule"
INTENT_REVIEW = "review"
INTENT_CHAT = "chat"

INTENT_LABELS = {
    INTENT_DIAGNOSE: "诊断",
    INTENT_PLAN: "计划",
    INTENT_SCHEDULE: "日程",
    INTENT_REVIEW: "复盘",
    INTENT_CHAT: "闲聊/问答",
}


class AgentState(TypedDict, total=False):
    """多 Agent 协作层的共享状态。"""

    # 身份与上下文
    user_id: str
    business_id: str
    session_id: str
    pending_intent: str

    # 对话
    user_message: str
    intent: str
    files: list

    # 记忆与知识（由节点填充，供 compose 汇总）
    memory_context: str          # 用户画像 + 历史摘要
    knowledge_context: str       # RAG 检索到的营销方法卡片文本
    tool_results: dict           # 各工具返回结果

    # 输出
    response: str
    needs_clarification: bool
    clarify_question: str
    error: str
