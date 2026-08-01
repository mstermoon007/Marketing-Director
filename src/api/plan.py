"""周计划模块接口（获取指定周的7天执行计划）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.agents.executor import ExecutorAgent
from src.db.models import (
    BusinessRecord,
    DiagnosisRecord,
    ExecutionPlanRecord,
    SyncSession,
)
from src.models.business import BusinessProfile
from src.models.diagnosis import DiagnosisReport, Problem


logger = logging.getLogger(__name__)

router = APIRouter()


class PlanResponse(BaseModel):
    """周计划统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        周计划数据载荷（SevenDayPlan 结构）。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class _ExecutorPersistentError(Exception):
    """内部标记：执行引擎需要 fallback。"""

    pass


def _record_to_profile(record: BusinessRecord) -> BusinessProfile:
    """DB BusinessRecord 转换为业务模型 BusinessProfile。

    Parameters
    ----------
    record : BusinessRecord
        数据库企业记录。

    Returns
    -------
    BusinessProfile
        转换后的业务模型实例。
    """
    return BusinessProfile(
        id=record.id,
        business_name=record.business_name,
        industry=record.industry,
        city=record.city,
        product_desc=record.product_desc or "",
        price_range=record.price_range or "",
        target_customers=record.target_customers or "",
        competitors=record.competitors or "",
        current_channels=record.current_channels or "",
        monthly_revenue=record.monthly_revenue or "",
        team_size=record.team_size or "",
        biggest_pain=record.biggest_pain or "",
    )


def _record_to_diagnosis(record: DiagnosisRecord) -> DiagnosisReport:
    """DB DiagnosisRecord 转换为业务模型 DiagnosisReport。

    Parameters
    ----------
    record : DiagnosisRecord
        数据库诊断记录。

    Returns
    -------
    DiagnosisReport
        转换后的诊断报告业务模型实例。
    """
    problems: List[Problem] = []
    for p in record.top3_problems or []:
        if isinstance(p, dict):
            problems.append(Problem.from_dict(p))
    return DiagnosisReport(
        id=record.id,
        business_id=record.business_id,
        overall_score=record.overall_score or 0,
        score_summary=record.score_summary or "",
        score_breakdown=record.score_breakdown or {},
        top3_problems=problems,
        strategy_summary=record.strategy_summary or "",
        this_week_focus=record.this_week_focus or "",
    )


def _build_rule_based_plan(
    profile: BusinessProfile,
    diagnosis: DiagnosisReport,
    start_date: date,
) -> dict:
    """规则引擎 fallback：生成通用7天计划模板。

    当 LLM Agent 连续失败时使用。

    Parameters
    ----------
    profile : BusinessProfile
        企业档案业务模型。
    diagnosis : DiagnosisReport
        诊断报告业务模型。
    start_date : date
        计划起始日期（周一）。

    Returns
    -------
    dict
        SevenDayPlan 结构的字典，包含 id、theme、goals、
        key_metrics、days 等字段。
    """
    week_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    days: List[dict] = []
    focuses = [
        "客户画像与需求梳理",
        "核心文案/话术打磨",
        "获客渠道内容发布",
        "线索跟进与转化",
        "老客户维护/转介绍",
        "数据复盘与下周规划",
        "休息调整或自学充电",
    ]
    common_tasks_pool: List[dict] = [
        {
            "time_slot": "09:00-09:30",
            "title": "梳理目标客户画像",
            "how_to": "列出至少3类核心客户的特征、痛点、常用平台",
            "checklist": ["写出客户年龄段", "写出客户核心需求", "列出常用APP/平台"],
            "done_criteria": "形成1页纸客户画像文档",
            "estimated_minutes": 30,
        },
        {
            "time_slot": "10:00-10:30",
            "title": "撰写3条朋友圈/短文案",
            "how_to": "围绕产品卖点、客户案例、干货分享三个方向",
            "checklist": ["卖点型1条", "案例型1条", "干货型1条"],
            "done_criteria": "文案存入素材库待发布",
            "estimated_minutes": 30,
        },
        {
            "time_slot": "14:00-14:30",
            "title": "渠道发布内容",
            "how_to": "在选定的主渠道发布1条内容，带上引导话术",
            "checklist": ["选好平台", "内容排版", "加引导话术/私信诱饵"],
            "done_criteria": "成功发布并记录数据",
            "estimated_minutes": 30,
        },
        {
            "time_slot": "16:00-16:30",
            "title": "跟进5条线索/客户",
            "how_to": "用标准化话术跟进，记录沟通要点",
            "checklist": ["列出跟进清单", "逐一沟通", "更新跟进记录表"],
            "done_criteria": "完成至少5条有效跟进",
            "estimated_minutes": 30,
        },
    ]

    for i in range(7):
        d = start_date + timedelta(days=i)
        day_tasks: List[dict] = []
        if i < 5:
            day_tasks = [common_tasks_pool[i % len(common_tasks_pool)]]
        elif i == 5:
            day_tasks = [
                {
                    "time_slot": "09:00-10:00",
                    "title": "本周数据复盘",
                    "how_to": "统计本周发布内容数据、线索量、成交数",
                    "checklist": ["整理数据", "对比目标", "写出3条改进点"],
                    "done_criteria": "形成本周复盘记录",
                    "estimated_minutes": 60,
                }
            ]

        days.append(
            {
                "day_label": week_labels[i],
                "date": d.isoformat(),
                "focus": focuses[i],
                "tasks": day_tasks,
            }
        )

    focus_stripped = (diagnosis.this_week_focus or "").strip()
    strategy_stripped = (diagnosis.strategy_summary or "精准获客").strip()
    theme = focus_stripped or f"围绕「{strategy_stripped}」开启执行"
    goals = [
        "完成本周核心渠道内容发布计划",
        "建立标准化线索跟进流程",
        "沉淀3条以上可复用内容模板",
    ]
    key_metrics = {"新增客户": 0, "咨询量": 0, "成交量": 0}

    return {
        "id": uuid.uuid4().hex,
        "diagnosis_id": diagnosis.id,
        "business_id": profile.id,
        "start_date": start_date.isoformat(),
        "theme": theme,
        "goals": goals,
        "key_metrics": key_metrics,
        "days": days,
        "plan_source": "rule_based",
    }


async def _generate_plan_with_fallback(
    profile: BusinessProfile,
    diagnosis: DiagnosisReport,
    start_date: date,
):
    """执行引擎 3次重试 + 规则引擎兜底。

    Parameters
    ----------
    profile : BusinessProfile
        企业档案业务模型。
    diagnosis : DiagnosisReport
        诊断报告业务模型。
    start_date : date
        计划起始日期。

    Returns
    -------
    dict
        SevenDayPlan 结构字典，附带 plan_source 标识（"llm"/"rule_based"）。
    """
    last_error = None
    for attempt in range(1, 4):
        try:
            agent = ExecutorAgent()
            plan = await agent.run(
                profile=profile,
                diagnosis=diagnosis,
                start_date=start_date,
            )
            logger.info("执行引擎第%d次调用成功", attempt)
            result = plan.to_dict()
            result["plan_source"] = "llm"
            return result
        except Exception as e:
            last_error = e
            logger.warning("执行引擎第%d次调用失败: %s", attempt, e)
            continue

    logger.warning("执行引擎连续3次失败，回退到规则引擎: %s", last_error)
    return _build_rule_based_plan(profile, diagnosis, start_date)


@router.get("/plan/weekly", response_model=PlanResponse)
async def get_weekly_plan_v3(
    week_number: Optional[int] = Query(1, ge=1, le=12, description="周数 1-12（对应季度12周）"),
    business_id: Optional[str] = None,
    diagnosis_id: Optional[str] = None,
) -> PlanResponse:
    """[V3.0] 获取周执行计划（文档6.3.4节 SevenDayPlan 结构）。

    参数优先级：diagnosis_id > business_id > 最新诊断记录/企业。

    返回 SevenDayPlan 结构：
      {
        id, diagnosis_id, business_id, start_date,
        theme, goals[], key_metrics{},
        days: [ {day_label, date, focus, tasks:[Task]} x 7 ]
      }

    Parameters
    ----------
    week_number : Optional[int]
        第N周，1-12（对应季度12周），默认1。
    business_id : Optional[str]
        企业ID（可选，无则取最新企业）。
    diagnosis_id : Optional[str]
        诊断ID（可选，无则取最新诊断）。

    Returns
    -------
    PlanResponse
        SevenDayPlan 周计划响应数据。

    Raises
    ------
    HTTPException
        - 404: 暂无企业信息，请先创建企业档案。
        - 500: 内部处理异常。
    """
    session = SyncSession()
    try:
        if diagnosis_id:
            diag_record = session.query(DiagnosisRecord).filter_by(id=diagnosis_id).first()
        elif business_id:
            diag_record = (
                session.query(DiagnosisRecord)
                .filter_by(business_id=business_id)
                .order_by(DiagnosisRecord.created_at.desc())
                .first()
            )
        else:
            diag_record = (
                session.query(DiagnosisRecord).order_by(DiagnosisRecord.created_at.desc()).first()
            )

        if not diag_record:
            logger.warning("无诊断记录，尝试使用最新企业+规则模板")
            business_record = (
                session.query(BusinessRecord).order_by(BusinessRecord.created_at.desc()).first()
            )
            if not business_record:
                raise HTTPException(status_code=404, detail="暂无企业信息，请先创建企业档案")
            profile = _record_to_profile(business_record)
            diagnosis = DiagnosisReport(
                business_id=profile.id,
                strategy_summary="精准获客与转化体系搭建",
                this_week_focus="客户画像梳理与基础内容准备",
            )
        else:
            business_record = (
                session.query(BusinessRecord).filter_by(id=diag_record.business_id).first()
            )
            profile = _record_to_profile(business_record)
            diagnosis = _record_to_diagnosis(diag_record)

        week_offset = (week_number or 1) - 1
        start_date = date.today() + timedelta(weeks=week_offset)
        while start_date.weekday() != 0:
            start_date -= timedelta(days=1)

        existing_plan = (
            session.query(ExecutionPlanRecord)
            .filter_by(business_id=profile.id)
            .order_by(ExecutionPlanRecord.created_at.desc())
            .first()
        )

        if existing_plan and week_number == 1:
            plan_data: dict = {
                "id": existing_plan.id,
                "diagnosis_id": existing_plan.diagnosis_id,
                "business_id": existing_plan.business_id,
                "start_date": (
                    existing_plan.start_date.isoformat()
                    if existing_plan.start_date
                    else start_date.isoformat()
                ),
                "theme": existing_plan.theme or "",
                "goals": existing_plan.goals or [],
                "key_metrics": existing_plan.key_metrics or {},
                "days": existing_plan.days or [],
                "plan_source": "database",
                "week_number": week_number,
            }
        else:
            plan_data = await _generate_plan_with_fallback(profile, diagnosis, start_date)

            db_record = ExecutionPlanRecord(
                id=uuid.uuid4().hex,
                diagnosis_id=diagnosis.id or (diag_record.id if diag_record else ""),
                business_id=profile.id,
                start_date=start_date,
                theme=plan_data.get("theme", ""),
                goals=plan_data.get("goals", []),
                key_metrics=plan_data.get("key_metrics", {}),
                days=plan_data.get("days", []),
            )
            try:
                session.add(db_record)
                session.commit()
                plan_data["id"] = db_record.id
            except Exception:
                session.rollback()

        plan_data["week_number"] = week_number

        logger.info(
            "[V3.0]周计划获取成功: week=%d days=%d source=%s",
            week_number,
            len(plan_data.get("days", [])),
            plan_data.get("plan_source", "unknown"),
        )

        return PlanResponse(data=plan_data)
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.exception("[V3.0]周计划获取失败: %s", e)
        raise HTTPException(status_code=500, detail=f"周计划获取失败: {e}") from e
    finally:
        session.close()
