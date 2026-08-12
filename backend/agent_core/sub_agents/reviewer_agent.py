"""
复盘子 Agent
================================

内部流程：计划 vs 实际 + 归因 → 调整建议

1. 解析/确认企业（无则尝试从文本建档案）
2. 若有上传文件 → ``upload_and_parse_data`` 解析为结构化数字；否则框架追问（请上传）
3. 调用 ``calculate_kpi`` 对比计划目标，计算达成率/转化率/环比
4. 归因总结（哪些达标/未达标 + 原因方向）
5. RAG 检索调整打法，给出下周建议
6. 把指标快照写入记忆库（指标变化）
"""

from __future__ import annotations

from backend.agent_core.common import (
    business_exists,
    create_business_from_text,
    detect_industry,
    format_cards,
    load_latest_plan_targets,
    render_review,
)
from backend.agent_core.tools import (
    calculate_kpi,
    search_marketing_knowledge,
    upload_and_parse_data,
)


def _build_review_summary(kpi: dict, numbers: dict, targets: dict) -> str:
    """基于 KPI 结果生成归因与建议文本（模板化，不空洞）。"""
    rows = kpi.get("rows", [])
    achieved = [r for r in rows if r.get("achievement_rate") is not None and r["achievement_rate"] >= 100]
    missed = [r for r in rows if r.get("achievement_rate") is not None and r["achievement_rate"] < 100]

    parts = []
    if achieved:
        names = "、".join(r["metric"] for r in achieved)
        parts.append(f"达标项：{names} —— 说明当前打法有效，下周保持节奏并适度加量。")
    if missed:
        names = "、".join(f"{r['metric']}({r['achievement_rate']}%)" for r in missed)
        parts.append(
            f"未达标项：{names} —— 多半是获客动作频次不够或触达人群不准，"
            "建议把对应动作前置到每天上午，并用更具体的客户痛点做内容钩子。"
        )
    if not parts:
        parts.append("本次未设目标，建议下周明确 2-3 个量化目标（如新增客户、咨询量）便于对比。")
    return "\n".join(parts)


async def run_review(state: dict, memory, kb) -> dict:
    user_msg = state.get("user_message", "")
    business_id = state.get("business_id")
    files = state.get("files") or []

    if business_id and not await business_exists(business_id):
        business_id = None

    if not business_id:
        industry = detect_industry(user_msg)
        if industry:
            business_id = await create_business_from_text(
                user_msg, industry, user_id=state["user_id"]
            )
            state["business_id"] = business_id

    if not files:
        state["needs_clarification"] = True
        state["clarify_question"] = (
            "复盘需要你上传本周数据（截图 PNG/JPG 或 CSV）。上传后我可以解析数字、"
            "对比计划目标做归因，并给出下周调整建议。"
        )
        return state

    parsed = await upload_and_parse_data(files)
    numbers = parsed.get("merged_numbers", {}) or {}
    if not numbers:
        state["needs_clarification"] = True
        state["clarify_question"] = (
            "我没从上传文件里解析出数字。请确认是带数据的 CSV 或清晰的截图，"
            "也可以直接在对话里告诉我本周各项数据（如：新增客户12、咨询量45）。"
        )
        return state

    targets = await load_latest_plan_targets(business_id) if business_id else {}
    kpi = calculate_kpi(numbers, targets)

    summary_text = _build_review_summary(kpi, numbers, targets)

    # RAG：调整方法
    industry = detect_industry(user_msg) or ""
    rag = await search_marketing_knowledge(
        f"{industry} 复盘 调整 提升 获客 转化 方法", top_k=3
    )
    cards_text = format_cards(rag.get("cards", []))

    # 写入记忆：指标变化快照
    if business_id:
        for m, v in numbers.items():
            memory.save_metric_snapshot(
                business_id, m, float(targets.get(m, 0) or 0), float(v)
            )

    state["tool_results"] = {"review_parse": parsed, "kpi": kpi}
    state["knowledge_context"] = cards_text
    state["response"] = render_review(kpi, cards_text, summary_text)
    state["business_id"] = business_id
    return state
