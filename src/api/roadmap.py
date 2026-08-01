"""路线图模块接口（获取当前季度营销路线图）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db.models import DiagnosisRecord, SyncSession


logger = logging.getLogger(__name__)

router = APIRouter()


class RoadmapResponse(BaseModel):
    """路线图统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        季度路线图数据载荷（overall_goal + phases[]）。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class PhaseItem(BaseModel):
    """单个阶段（文档6.3.3节 PhaseItem）。

    Parameters
    ----------
    phase : int
        阶段序号 1-3。
    title : str
        阶段名称。
    duration : str
        持续时间，例如"第1-2周"。
    goal : str
        阶段目标。
    key_results : List[str]
        关键结果KR列表。
    focus_tasks : List[str]
        重点任务列表。
    """

    phase: int = Field(..., description="阶段序号 1-3")
    title: str = Field("", description="阶段名称")
    duration: str = Field("", description="持续时间，例如'第1-2周'")
    goal: str = Field("", description="阶段目标")
    key_results: List[str] = Field(default_factory=list, description="关键结果KR")
    focus_tasks: List[str] = Field(default_factory=list, description="重点任务")


def _build_default_roadmap(strategy_summary: str, this_week_focus: str) -> dict:
    """根据诊断报告策略方向，构建 3 个阶段的季度路线图。

    若无诊断信息，则返回通用路线图模板。

    Parameters
    ----------
    strategy_summary : str
        诊断报告中的策略摘要。
    this_week_focus : str
        诊断报告中的本周重点。

    Returns
    -------
    dict
        quarterly_roadmap 结构字典，包含 overall_goal 与 phases（3个PhaseItem）。
    """
    strategy = (strategy_summary or "").strip() or "以精准定位+低成本获客为核心，建立可持续营销闭环"
    focus = (this_week_focus or "").strip() or "梳理核心卖点与目标客户画像"

    overall_goal = (
        f"季度营销目标：通过「{strategy}」，" "在12周内实现获客体系从0到1搭建，达成稳定获客"
    )

    phases = [
        PhaseItem(
            phase=1,
            title="第1阶段：定位筑基期",
            duration="第1-4周",
            goal=f"完成精准定位与基础准备：{focus}",
            key_results=[
                "完成企业核心卖点梳理与差异化定位",
                "建立3个以上精准目标客户画像",
                "完成1-2个核心获客渠道的初期测试",
            ],
            focus_tasks=[
                "客户访谈与需求调研（至少10个真实客户）",
                "核心文案/话术打磨（产品介绍、朋友圈、引流话术）",
                "选定1-2个主渠道，完成账号/物料准备",
            ],
        ).model_dump(),
        PhaseItem(
            phase=2,
            title="第2阶段：渠道放量期",
            duration="第5-8周",
            goal="跑通核心渠道获客SOP，实现稳定引流",
            key_results=[
                "核心渠道日引流达到目标量级",
                "建立线索跟进SOP，转化率提升至行业均值以上",
                "沉淀3套以上可复用的内容模板",
            ],
            focus_tasks=[
                "内容产出频率固定（每周3-5条）",
                "建立线索记录表，每日跟进复盘",
                "渠道数据监控：曝光-点击-咨询-成交全链路",
            ],
        ).model_dump(),
        PhaseItem(
            phase=3,
            title="第3阶段：转化裂变期",
            duration="第9-12周",
            goal="优化转化漏斗，建立转介绍机制，形成闭环",
            key_results=[
                "成交转化率提升20%以上",
                "老客户转介绍占比达到30%以上",
                "建立标准化复盘机制，每周迭代优化",
            ],
            focus_tasks=[
                "成交客户跟进与售后SOP完善",
                "转介绍激励方案设计与落地",
                "月度数据复盘，下季度策略规划",
            ],
        ).model_dump(),
    ]

    return {
        "overall_goal": overall_goal,
        "phases": phases,
    }


@router.get("/roadmap/current", response_model=RoadmapResponse)
async def get_current_roadmap(
    business_id: Optional[str] = None,
) -> RoadmapResponse:
    """[V3.0] 获取当前季度路线图（文档6.3.3节）。

    返回结构：
      {
        overall_goal: str,
        phases: [
          {phase, title, duration, goal, key_results[], focus_tasks[]},
          {phase, title, duration, goal, key_results[], focus_tasks[]},
          {phase, title, duration, goal, key_results[], focus_tasks[]},
        ]
      }

    内部聚合：优先取最新诊断报告的 strategy_summary/this_week_focus 生成，
    若无诊断数据则返回通用模板。

    Parameters
    ----------
    business_id : Optional[str]
        企业ID（可选查询参数），未提供时使用最新诊断记录。

    Returns
    -------
    RoadmapResponse
        季度路线图响应数据，包含 overall_goal 与 3 个 phases。

    Raises
    ------
    HTTPException
        - 500: 内部处理异常。
    """
    session = SyncSession()
    try:
        diag_query = session.query(DiagnosisRecord)
        if business_id:
            diag_query = diag_query.filter_by(business_id=business_id)
        diag_record = diag_query.order_by(DiagnosisRecord.created_at.desc()).first()

        strategy_summary = ""
        this_week_focus = ""
        if diag_record:
            strategy_summary = diag_record.strategy_summary or ""
            this_week_focus = diag_record.this_week_focus or ""

        roadmap = _build_default_roadmap(strategy_summary, this_week_focus)

        if diag_record:
            roadmap["diagnosis_id"] = diag_record.id
            roadmap["business_id"] = diag_record.business_id

        logger.info("路线图获取成功: phases=%d", len(roadmap.get("phases", [])))

        return RoadmapResponse(data=roadmap)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("路线图获取失败: %s", e)
        raise HTTPException(status_code=500, detail=f"路线图获取失败: {e}") from e
    finally:
        session.close()
