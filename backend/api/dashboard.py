"""工作台模块接口（获取工作台概览数据）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api._authz import require_business
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


class DashboardResponse(BaseModel):
    """工作台统一响应格式。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


def _calc_week_number(start_date: Optional[date]) -> int:
    """根据计划起始日期计算当前周数（12周总周期）。"""
    if not start_date:
        return 1
    today = date.today()
    if today < start_date:
        return 1
    delta_days = (today - start_date).days
    week = (delta_days // 7) + 1
    return max(1, min(12, week))


def _get_weekday_label(weekday_idx: int) -> str:
    """获取星期标签（中文）。"""
    labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return labels[weekday_idx] if 0 <= weekday_idx < 7 else ""


def _extract_tasks_from_days(days: list[dict], today_idx: Optional[int]) -> list[dict]:
    """从计划 days 中抽取当天（或第一个非空）的任务。"""
    if not days:
        return []

    if today_idx is not None and 0 <= today_idx < len(days):
        target_day = days[today_idx]
    else:
        target_day = days[0]

    tasks = (
        target_day.get("tasks", []) or []
        if isinstance(target_day, dict)
        else []
    )

    result: list[dict] = []
    for idx, t in enumerate(tasks):
        if isinstance(t, dict):
            task_id = t.get("task_id") or f"task_{idx + 1}"
            result.append(
                {
                    "task_id": task_id,
                    "title": t.get("title", ""),
                    "time_slot": t.get("time_slot", t.get("time", "")),
                    "how_to": t.get("how_to", ""),
                    "checklist": t.get("checklist", []),
                    "done_criteria": t.get("done_criteria", ""),
                    "estimated_minutes": t.get("estimated_minutes", t.get("minutes", 0)),
                    "status": t.get("status", "pending"),
                }
            )
    return result


def _build_week_completion(days: list[dict]) -> list[dict]:
    """构造7天完成度数组（无真实打卡数据时用占位）。"""
    result: list[dict] = []
    today = date.today().weekday()
    for i in range(7):
        total = 0
        completed = 0
        if i < len(days) and isinstance(days[i], dict):
            tasks = days[i].get("tasks", []) or []
            total = len(tasks)
            for t in tasks:
                if isinstance(t, dict) and t.get("status") == "done":
                    completed += 1
        percentage = round((completed / total) * 100, 1) if total > 0 else 0.0
        is_today = i == today
        result.append(
            {
                "day": i + 1,
                "label": _get_weekday_label(i),
                "date": (date.today() - timedelta(days=today - i)).isoformat(),
                "total": total,
                "completed": completed,
                "percentage": percentage,
                "is_today": is_today,
            }
        )
    return result


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    business_id: Optional[str] = Query(None, description="企业ID（可选）"),
    user: dict = Depends(get_current_user),
) -> DashboardResponse:
    """[V1.0] 获取工作台概览（文档6.3.7节）。"""
    async with AsyncSessionLocal() as session:
        try:
            # 对象级授权：确定归属当前用户的企业范围，杜绝跨用户查看（防 IDOR）
            if business_id:
                await require_business(session, business_id, user["user_id"])
                scoped_business_id = business_id
            else:
                biz_row = (
                    await session.execute(
                        select(BusinessRecord)
                        .filter_by(user_id=user["user_id"])
                        .order_by(BusinessRecord.created_at.desc())
                    )
                ).scalars().first()
                scoped_business_id = biz_row.id if biz_row else None

            diag_stmt = select(DiagnosisRecord)
            if scoped_business_id:
                diag_stmt = diag_stmt.filter_by(business_id=scoped_business_id)
            diag_stmt = diag_stmt.order_by(DiagnosisRecord.created_at.desc())
            result = await session.execute(diag_stmt)
            diag_record = result.scalars().first()

            actual_business_id = scoped_business_id
            strategy_summary = ""
            this_week_focus = ""
            if diag_record:
                actual_business_id = diag_record.business_id
                strategy_summary = diag_record.strategy_summary or ""
                this_week_focus = diag_record.this_week_focus or ""

            plan_stmt = select(ExecutionPlanRecord)
            if actual_business_id:
                plan_stmt = plan_stmt.filter_by(business_id=actual_business_id)
            plan_stmt = plan_stmt.order_by(ExecutionPlanRecord.created_at.desc())
            result = await session.execute(plan_stmt)
            plan_record = result.scalars().first()

            plan_days: list[dict] = []
            start_date = None
            theme = ""
            plan_id = ""
            if plan_record:
                plan_days = plan_record.days or []
                start_date = plan_record.start_date
                theme = plan_record.theme or ""
                plan_id = plan_record.id

            review_stmt = select(ReviewRecord)
            if actual_business_id:
                review_stmt = review_stmt.filter_by(business_id=actual_business_id)
            review_stmt = review_stmt.order_by(ReviewRecord.created_at.desc())
            result = await session.execute(review_stmt)
            review_record = result.scalars().first()

            current_week = _calc_week_number(start_date)
            total_weeks = 12

            if current_week <= 4:
                phase_num = 1
                phase_title = "第1阶段：定位筑基期"
                phase_goal = (
                    "完成精准定位与基础准备：" f"{this_week_focus or '客户画像梳理与核心卖点提炼'}"
                )
            elif current_week <= 8:
                phase_num = 2
                phase_title = "第2阶段：渠道放量期"
                phase_goal = "跑通核心渠道获客SOP，实现稳定引流"
            else:
                phase_num = 3
                phase_title = "第3阶段：转化裂变期"
                phase_goal = "优化转化漏斗，建立转介绍机制，形成闭环"

            phase_info = {
                "phase": phase_num,
                "title": phase_title,
                "goal": phase_goal,
            }

            today_idx = date.today().weekday()
            today_tasks = _extract_tasks_from_days(plan_days, today_idx)

            total_week_tasks = 0
            completed_week_tasks = 0
            for d in plan_days:
                if isinstance(d, dict):
                    tasks = d.get("tasks", []) or []
                    total_week_tasks += len(tasks)
                    for t in tasks:
                        if isinstance(t, dict) and t.get("status") == "done":
                            completed_week_tasks += 1

            weekly_percentage = (
                round((completed_week_tasks / total_week_tasks) * 100, 1)
                if total_week_tasks > 0
                else 0.0
            )
            weekly_progress = {
                "completed": completed_week_tasks,
                "total": total_week_tasks,
                "percentage": weekly_percentage,
            }

            week_completion = _build_week_completion(plan_days)

            result_data: dict = {
                "current_week": current_week,
                "total_weeks": total_weeks,
                "phase_info": phase_info,
                "weekly_progress": weekly_progress,
                "today_tasks": today_tasks,
                "week_completion": week_completion,
            }

            if actual_business_id:
                result_data["business_id"] = actual_business_id
            if plan_id:
                result_data["plan_id"] = plan_id
            if theme:
                result_data["week_theme"] = theme
            if strategy_summary:
                result_data["strategy_summary"] = strategy_summary
            if review_record:
                result_data["latest_review_id"] = review_record.id
                result_data["latest_review_summary"] = (review_record.summary or "")[:60]

            logger.info(
                "工作台获取成功: week=%d/%d tasks_today=%d total_tasks=%d",
                current_week,
                total_weeks,
                len(today_tasks),
                total_week_tasks,
            )

            return DashboardResponse(data=result_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("工作台获取失败: %s", e)
            raise HTTPException(status_code=500, detail=f"工作台获取失败: {e}") from e
