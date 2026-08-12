"""
诊断子 Agent
================================

内部流程：框架追问 + 数据 + RAG → 归因

1. 解析/确认企业（无 business_id 时从自然语言抽取行业并建档案；信息不足则框架追问）
2. 调用 ``diagnose_business`` 工具产出诊断报告（评分/问题/策略）
3. RAG 检索该行业相关营销方法卡片，支撑「归因 + 建议动作」
4. 渲染具体、有案例支撑的诊断回复，并写入记忆库（用户画像）
"""

from __future__ import annotations

from backend.agent_core.common import (
    business_exists,
    create_business_from_text,
    detect_industry,
    format_cards,
    render_diagnosis,
)
from backend.agent_core.tools import diagnose_business, search_marketing_knowledge


async def run_diagnose(state: dict, memory, kb) -> dict:
    user_msg = state.get("user_message", "")
    business_id = state.get("business_id")

    if business_id and not await business_exists(business_id):
        business_id = None

    if not business_id:
        industry = detect_industry(user_msg)
        if not industry:
            state["needs_clarification"] = True
            state["clarify_question"] = (
                "为了给你做精准诊断，请告诉我：\n"
                "① 你做的是哪个行业/生意？\n"
                "② 开在哪座城市？\n"
                "③ 主要卖什么、服务谁？\n"
                "④ 目前最大的痛点是什么？"
            )
            return state
        business_id = await create_business_from_text(
            user_msg, industry, user_id=state["user_id"]
        )
        state["business_id"] = business_id

    res = await diagnose_business(business_id)
    if not res.get("ok"):
        state["error"] = res.get("error", "诊断失败")
        return state

    report = res["report"]
    industry = detect_industry(user_msg) or report.get("industry", "")

    # RAG：围绕策略方向与行业检索具体打法
    rag = await search_marketing_knowledge(
        f"{report.get('strategy_summary', '')} {industry} 获客 转化 内容 方法",
        top_k=3,
    )
    cards = rag.get("cards", [])
    cards_text = format_cards(cards)

    # 写入记忆：用户画像（行业 + 最近诊断评分）
    memory.save_profile(
        state["user_id"],
        f"行业：{industry}；需求：诊断营销健康度。最近诊断评分 {report.get('overall_score')}。"
        f"策略方向：{report.get('strategy_summary', '')}",
        {"industry": industry or "", "business_id": business_id},
    )

    state["tool_results"] = {"diagnose": res}
    state["knowledge_context"] = cards_text
    state["response"] = render_diagnosis(report, cards_text)
    state["business_id"] = business_id
    return state
