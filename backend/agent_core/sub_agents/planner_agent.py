"""
计划子 Agent
================================

内部流程：拆解 + 模板填充 → 日程生成

1. 解析/确认企业（信息不足则框架追问）
2. 调用 ``generate_plan`` 产出诊断 + 7 天执行计划
3. 调用 ``schedule_task`` 在计划基础上生成按天排期与主动提醒
4. RAG 检索与业务薄弱维度/行业相关的方法卡片，丰富计划建议
5. 渲染计划回复，并写入记忆库
"""

from __future__ import annotations

from backend.agent_core.common import (
    business_exists,
    create_business_from_text,
    detect_industry,
    format_cards,
    render_plan,
)
from backend.agent_core.tools import generate_plan, schedule_task, search_marketing_knowledge


async def run_plan(state: dict, memory, kb) -> dict:
    user_msg = state.get("user_message", "")
    business_id = state.get("business_id")

    if business_id and not await business_exists(business_id):
        business_id = None

    if not business_id:
        industry = detect_industry(user_msg)
        if not industry:
            state["needs_clarification"] = True
            state["clarify_question"] = (
                "做计划前我需要先了解你的生意：行业、城市、卖什么、最大痛点？"
                "告诉我后我会先诊断再生成 7 天执行计划。"
            )
            return state
        business_id = await create_business_from_text(user_msg, industry)
        state["business_id"] = business_id

    res = await generate_plan(business_id)
    if not res.get("ok"):
        state["error"] = res.get("error", "生成计划失败")
        return state

    plan = res["plan"]
    industry = detect_industry(user_msg) or plan.get("industry", "")

    # 基于计划生成排期 + 提醒
    sched = await schedule_task(business_id, goal=plan.get("theme"))

    # RAG：围绕行业与执行方法检索
    rag = await search_marketing_knowledge(
        f"{industry} 执行计划 获客 内容 私域 方法", top_k=3
    )
    cards_text = format_cards(rag.get("cards", []))

    memory.save_profile(
        state["user_id"],
        f"行业：{industry}；已生成计划，主题：{plan.get('theme','')}。",
        {"industry": industry or "", "business_id": business_id},
    )

    state["tool_results"] = {"plan": res, "schedule": sched}
    state["knowledge_context"] = cards_text
    state["response"] = render_plan(plan, sched, cards_text)
    state["business_id"] = business_id
    return state
