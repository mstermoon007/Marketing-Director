"""个人中心 / 资源列表接口。

为前端「个人中心」页提供按当前用户聚合的列表与历史数据：

- ``GET /api/business/list``        ：当前用户名下所有企业。
- ``GET /api/diagnosis/history``    ：当前用户所有企业的诊断报告历史。
- ``GET /api/plan/history``         ：当前用户所有企业的执行计划历史。
- ``GET /api/review/history``       ：当前用户所有企业的复盘报告历史。

由于诊断 / 计划 / 复盘记录本身不带 user_id，统一通过 ``businesses.user_id``
关联过滤，确保只返回当前用户的资源（数据隔离）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.auth import get_current_user
from backend.db.models import (
    AsyncSessionLocal,
    BusinessRecord,
    DiagnosisRecord,
    ExecutionPlanRecord,
    ReviewRecord,
)


logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


class ProfileResponse(BaseModel):
    """通用响应格式（与既有模块一致）。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


def _business_to_dict(rec: BusinessRecord) -> dict:
    return {
        "id": rec.id,
        "business_name": rec.business_name,
        "industry": rec.industry,
        "city": rec.city,
        "product_desc": rec.product_desc or "",
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@router.get("/profile/businesses", response_model=ProfileResponse)
async def list_my_businesses(user: dict = Depends(get_current_user)) -> ProfileResponse:
    """当前用户名下所有企业。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BusinessRecord)
            .filter_by(user_id=user["user_id"])
            .order_by(BusinessRecord.created_at.desc())
        )
        items = [_business_to_dict(r) for r in result.scalars().all()]
    return ProfileResponse(data={"list": items, "total": len(items)})


@router.get("/profile/diagnosis-history", response_model=ProfileResponse)
async def list_my_diagnoses(user: dict = Depends(get_current_user)) -> ProfileResponse:
    """当前用户所有诊断报告（经 businesses.user_id 关联过滤）。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DiagnosisRecord)
            .join(BusinessRecord, DiagnosisRecord.business_id == BusinessRecord.id)
            .filter(BusinessRecord.user_id == user["user_id"])
            .order_by(DiagnosisRecord.created_at.desc())
        )
        items = [
            {
                "id": r.id,
                "business_id": r.business_id,
                "overall_score": r.overall_score,
                "score_summary": r.score_summary,
                "this_week_focus": r.this_week_focus,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
    return ProfileResponse(data={"list": items, "total": len(items)})


@router.get("/profile/plan-history", response_model=ProfileResponse)
async def list_my_plans(user: dict = Depends(get_current_user)) -> ProfileResponse:
    """当前用户所有执行计划（经 businesses.user_id 关联过滤）。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ExecutionPlanRecord)
            .join(BusinessRecord, ExecutionPlanRecord.business_id == BusinessRecord.id)
            .filter(BusinessRecord.user_id == user["user_id"])
            .order_by(ExecutionPlanRecord.created_at.desc())
        )
        items = [
            {
                "id": r.id,
                "business_id": r.business_id,
                "theme": r.theme,
                "week_number": r.week_number,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
    return ProfileResponse(data={"list": items, "total": len(items)})


@router.get("/profile/review-history", response_model=ProfileResponse)
async def list_my_reviews(user: dict = Depends(get_current_user)) -> ProfileResponse:
    """当前用户所有复盘报告（经 businesses.user_id 关联过滤）。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ReviewRecord)
            .join(BusinessRecord, ReviewRecord.business_id == BusinessRecord.id)
            .filter(BusinessRecord.user_id == user["user_id"])
            .order_by(ReviewRecord.created_at.desc())
        )
        items = [
            {
                "id": r.id,
                "business_id": r.business_id,
                "plan_id": r.plan_id,
                "week_number": r.week_number,
                "summary": r.summary,
                "numbers": r.numbers,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
    return ProfileResponse(data={"list": items, "total": len(items)})
