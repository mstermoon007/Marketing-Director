"""对象级授权辅助（防 IDOR）。

所有按 ID 访问企业 / 诊断 / 计划 / 复盘 / 待办 的接口，都必须先确认
资源归属当前 JWT 用户，否则返回 404（不暴露资源是否存在）。
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import (
    BusinessRecord,
    DiagnosisRecord,
    ExecutionPlanRecord,
    ReviewRecord,
)


async def require_business(session, business_id: str, user_id: str) -> BusinessRecord:
    """确认企业存在且归属当前用户。"""
    rec = (
        await session.execute(
            select(BusinessRecord).filter_by(id=business_id, user_id=user_id)
        )
    ).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="企业不存在")
    return rec


async def require_owned_plan(
    session, plan_id: str, user_id: str
) -> ExecutionPlanRecord:
    """确认执行计划存在且其所属企业归属当前用户。"""
    plan = (
        await session.execute(
            select(ExecutionPlanRecord).filter_by(id=plan_id)
        )
    ).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    await require_business(session, plan.business_id, user_id)
    return plan


async def require_owned_diagnosis(
    session, diagnosis_id: str, user_id: str
) -> DiagnosisRecord:
    """确认诊断存在且其所属企业归属当前用户。"""
    diag = (
        await session.execute(
            select(DiagnosisRecord).filter_by(id=diagnosis_id)
        )
    ).scalar_one_or_none()
    if not diag:
        raise HTTPException(status_code=404, detail="诊断不存在")
    await require_business(session, diag.business_id, user_id)
    return diag


async def require_owned_review(
    session, review_id: str, user_id: str
) -> ReviewRecord:
    """确认复盘存在且其所属企业归属当前用户。"""
    rev = (
        await session.execute(select(ReviewRecord).filter_by(id=review_id))
    ).scalar_one_or_none()
    if not rev:
        raise HTTPException(status_code=404, detail="复盘不存在")
    await require_business(session, rev.business_id, user_id)
    return rev
