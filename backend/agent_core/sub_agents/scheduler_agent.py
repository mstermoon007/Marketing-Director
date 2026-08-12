"""
日程子 Agent
================================

内部流程：按天分配 + 主动提醒

1. 解析/确认企业（无则尝试从文本建档案）
2. 调用 ``schedule_task`` 把任务按天分配（≤5 任务/天），并生成每日 09:00 主动提醒
3. 若既无企业计划也无用户提供任务，则框架追问（让用户直接列出任务）
4. 渲染排期 + 提醒清单
"""

from __future__ import annotations

from backend.agent_core.common import (
    business_exists,
    create_business_from_text,
    detect_industry,
    render_schedule,
)
from backend.agent_core.tools import schedule_task


async def run_schedule(state: dict, memory, kb) -> dict:
    user_msg = state.get("user_message", "")
    business_id = state.get("business_id")

    if business_id and not await business_exists(business_id):
        business_id = None

    if not business_id:
        industry = detect_industry(user_msg)
        if industry:
            business_id = await create_business_from_text(
                user_msg, industry, user_id=state["user_id"]
            )
            state["business_id"] = business_id

    if not business_id:
        state["needs_clarification"] = True
        state["clarify_question"] = (
            "排日程需要你的企业信息。请先告诉我你的生意（行业/城市/卖什么），"
            "或直接把想排期的任务用逗号告诉我，例如：发朋友圈、给老客打电话、拍一条短视频。"
        )
        return state

    sched = await schedule_task(business_id)
    if not sched.get("ok"):
        state["needs_clarification"] = True
        state["clarify_question"] = (
            sched.get("error", "无法排期")
            + " 你也可以直接把想排期的任务用逗号告诉我，例如：发朋友圈、给老客打电话、做短视频。"
        )
        return state

    state["tool_results"] = {"schedule": sched}
    state["response"] = render_schedule(sched)
    state["business_id"] = business_id
    return state
