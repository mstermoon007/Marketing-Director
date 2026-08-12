"""执行计划模块接口（生成7天执行清单/查看执行计划）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.auth import get_current_user
from sqlalchemy import select

from backend.agents.executor import ExecutorAgent
from backend.db.models import (
    AsyncSessionLocal,
    BusinessRecord,
    DiagnosisRecord,
    ExecutionPlanRecord,
)
from backend.models.business import BusinessProfile
from backend.models.diagnosis import DiagnosisReport, Problem


logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


class ExecutionResponse(BaseModel):
    """执行计划统一响应格式。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class GeneratePlanRequest(BaseModel):
    """生成执行计划请求体。"""

    start_date: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="计划起始日期（ISO格式）",
    )


def _record_to_profile(record: BusinessRecord) -> BusinessProfile:
    """DB BusinessRecord 转换为业务模型 BusinessProfile。"""
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
    """DB DiagnosisRecord 转换为业务模型 DiagnosisReport。"""
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


@router.post("/execution/{diagnosis_id}", response_model=ExecutionResponse)
async def generate_plan(
    diagnosis_id: str,
    req: GeneratePlanRequest = GeneratePlanRequest(),
) -> ExecutionResponse:
    """生成7天执行清单（核心接口）。"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(DiagnosisRecord).filter_by(id=diagnosis_id)
            )
            diagnosis_record = result.scalar_one_or_none()
            if not diagnosis_record:
                raise HTTPException(status_code=404, detail="诊断报告不存在")

            result = await session.execute(
                select(BusinessRecord).filter_by(id=diagnosis_record.business_id)
            )
            business_record = result.scalar_one_or_none()
            if not business_record:
                raise HTTPException(status_code=404, detail="企业信息不存在")

            profile = _record_to_profile(business_record)
            diagnosis = _record_to_diagnosis(diagnosis_record)
            start_date = date.fromisoformat(req.start_date)

            agent = ExecutorAgent()
            plan = await agent.run(
                profile=profile,
                diagnosis=diagnosis,
                start_date=start_date,
            )

            db_record = ExecutionPlanRecord(
                diagnosis_id=diagnosis_id,
                business_id=business_record.id,
                start_date=start_date,
                theme=plan.theme,
                goals=plan.goals,
                key_metrics=plan.key_metrics,
                days=plan.to_dict()["days"],
            )
            session.add(db_record)
            await session.commit()
            await session.refresh(db_record)

            plan.id = db_record.id
            plan.created_at = db_record.created_at

            logger.info(
                "执行计划生成完成: plan=%s theme=%s days=%d",
                plan.id,
                plan.theme,
                len(plan.days),
            )

            return ExecutionResponse(data=plan.to_dict())

        except ValueError as e:
            logger.error("执行引擎 Agent 异常: %s", e)
            raise HTTPException(status_code=502, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.exception("计划生成失败: %s", e)
            raise HTTPException(status_code=500, detail=f"计划生成失败: {e}") from e


@router.get("/execution/{plan_id}", response_model=ExecutionResponse)
async def get_plan(plan_id: str) -> ExecutionResponse:
    """查看7天执行计划。"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(ExecutionPlanRecord).filter_by(id=plan_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                raise HTTPException(status_code=404, detail="计划不存在")

            return ExecutionResponse(
                data={
                    "id": record.id,
                    "diagnosis_id": record.diagnosis_id,
                    "business_id": record.business_id,
                    "start_date": record.start_date.isoformat() if record.start_date else None,
                    "theme": record.theme,
                    "goals": record.goals,
                    "key_metrics": record.key_metrics,
                    "days": record.days,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("获取执行计划失败: %s", e)
            raise HTTPException(status_code=500, detail=f"获取失败: {e}") from e
