"""
主流程 Pipeline — 唯一的核心编排层
参考开发思路文档：第 5.3 节 — run_full_pipeline() / run_weekly_review()

唯一核心链路：
输入企业信息 → AI 诊断报告 → 7 天执行清单 → 老板执行 → 上传截图复盘
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select

from backend.agents.diagnosis import DiagnosisAgent
from backend.agents.executor import ExecutorAgent
from backend.agents.reviewer import ReviewAgent
from backend.db.models import (
    AsyncSessionLocal,
    BusinessRecord,
    DiagnosisRecord,
    ExecutionPlanRecord,
    ReviewRecord,
)
from backend.models.business import BusinessProfile
from backend.models.diagnosis import DiagnosisReport
from backend.models.execution import SevenDayPlan
from backend.models.review import ReviewReport


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 内部辅助：DB 记录 → 业务模型
# ──────────────────────────────────────────────

def _record_to_profile(record: BusinessRecord) -> BusinessProfile:
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
        created_at=record.created_at,
    )


def _record_to_diagnosis(record: DiagnosisRecord) -> DiagnosisReport:
    from backend.models.diagnosis import Problem
    problems = [
        Problem.from_dict(p) if isinstance(p, dict) else p
        for p in (record.top3_problems or [])
    ]
    return DiagnosisReport(
        id=record.id,
        business_id=record.business_id,
        overall_score=record.overall_score or 0,
        score_summary=record.score_summary or "",
        score_breakdown=record.score_breakdown or {},
        top3_problems=problems,
        strategy_summary=record.strategy_summary or "",
        this_week_focus=record.this_week_focus or "",
        created_at=record.created_at,
    )


def _record_to_plan(record: ExecutionPlanRecord) -> SevenDayPlan:
    from backend.models.execution import DayPlan, Task
    days = []
    for d in (record.days or []):
        if isinstance(d, dict):
            tasks = [
                Task.from_dict(t) if isinstance(t, dict) else t
                for t in d.get("tasks", [])
            ]
            days.append(DayPlan(
                day_label=d.get("day_label", ""),
                focus=d.get("focus", ""),
                tasks=tasks,
            ))
    return SevenDayPlan(
        id=record.id,
        diagnosis_id=record.diagnosis_id,
        business_id=record.business_id,
        start_date=record.start_date,
        theme=record.theme or "",
        goals=record.goals or [],
        key_metrics=record.key_metrics or {},
        days=days,
        created_at=record.created_at,
    )


# ──────────────────────────────────────────────
# 公共 API：加载数据（异步）
# ──────────────────────────────────────────────

async def load_business_profile(business_id: str) -> BusinessProfile:
    """加载企业信息（文档 5.3 pipeline 定义）"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BusinessRecord).filter_by(id=business_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError(f"企业信息不存在: {business_id}")
        return _record_to_profile(record)


async def load_diagnosis_report(business_id: str) -> Optional[DiagnosisReport]:
    """加载某企业最新诊断报告"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DiagnosisRecord)
            .filter_by(business_id=business_id)
            .order_by(DiagnosisRecord.created_at.desc())
        )
        record = result.scalars().first()
        if not record:
            return None
        return _record_to_diagnosis(record)


async def load_execution_plan(plan_id: str) -> SevenDayPlan:
    """加载 7 天执行计划（文档 5.3 pipeline 定义）"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ExecutionPlanRecord).filter_by(id=plan_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError(f"执行计划不存在: {plan_id}")
        return _record_to_plan(record)


# ──────────────────────────────────────────────
# 公共 API：Pipeline 主流程
# ──────────────────────────────────────────────

async def run_full_pipeline(business_id: str) -> dict:
    """
    唯一的核心方法：跑完整条链路（文档 5.3 定义）

    步骤：
    1. 加载企业信息
    2. 生成诊断报告
    3. 生成 7 天执行清单
    4. 返回全部结果（dict 格式便于序列化）
    """
    logger.info("Pipeline.run_full_pipeline.start | business=%s", business_id)

    # Step 1: 加载企业信息
    profile = await load_business_profile(business_id)

    # Step 2: 诊断 Agent
    diagnosis_agent = DiagnosisAgent()
    diagnosis: DiagnosisReport = await diagnosis_agent.run(profile)

    # 持久化诊断结果（供后续查询）
    async with AsyncSessionLocal() as session:
        try:
            diag_record = DiagnosisRecord(
                business_id=business_id,
                overall_score=diagnosis.overall_score,
                score_summary=diagnosis.score_summary,
                score_breakdown=diagnosis.score_breakdown,
                top3_problems=diagnosis.to_dict()["top_issues"],
                strategy_summary=diagnosis.strategy_summary,
                this_week_focus=diagnosis.this_week_focus,
            )
            session.add(diag_record)
            await session.commit()
            await session.refresh(diag_record)
            diagnosis.id = diag_record.id
            diagnosis.created_at = diag_record.created_at
        except Exception:
            await session.rollback()
            raise

    # Step 3: 执行引擎（核心）
    executor_agent = ExecutorAgent()
    from datetime import date
    plan: SevenDayPlan = await executor_agent.run(
        profile=profile,
        diagnosis=diagnosis,
        start_date=date.today(),
    )

    # 持久化执行计划
    async with AsyncSessionLocal() as session:
        try:
            plan_record = ExecutionPlanRecord(
                diagnosis_id=diagnosis.id,
                business_id=business_id,
                start_date=plan.start_date or date.today(),
                theme=plan.theme,
                goals=plan.goals,
                key_metrics=plan.key_metrics,
                days=plan.to_dict()["days"],
            )
            session.add(plan_record)
            await session.commit()
            await session.refresh(plan_record)
            plan.id = plan_record.id
            plan.created_at = plan_record.created_at
        except Exception:
            await session.rollback()
            raise

    result = {
        "business": {
            "id": profile.id,
            "business_name": profile.business_name,
            "industry": profile.industry,
            "city": profile.city,
        },
        "diagnosis": diagnosis.to_dict(),
        "plan": plan.to_dict(),
    }

    logger.info(
        "Pipeline.run_full_pipeline.done | business=%s score=%d theme=%s",
        profile.business_name, diagnosis.overall_score, plan.theme,
    )
    return result


async def run_weekly_review(plan_id: str, uploaded_files: list) -> dict:
    """
    周末复盘：上传截图 → 解析 → 生成复盘报告（文档 5.3 定义）
    """
    logger.info(
        "Pipeline.run_weekly_review.start | plan=%s files=%d",
        plan_id, len(uploaded_files),
    )

    # Step 1: 加载执行计划
    plan = await load_execution_plan(plan_id)

    # Step 2: 调用复盘 Agent（包含截图解析 + 数据合并 + 报告生成）
    reviewer = ReviewAgent()
    review: ReviewReport = await reviewer.run(plan=plan, uploaded_files=uploaded_files)

    # Step 3: 持久化复盘结果
    async with AsyncSessionLocal() as session:
        try:
            record = ReviewRecord(
                plan_id=plan_id,
                business_id=plan.business_id,
                summary=review.summary,
                numbers=review.numbers,
                vs_target=review.to_dict()["vs_target"],
                what_worked=review.what_worked,
                what_didnt=review.what_didnt,
                suggestions=review.suggestions,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            review.id = record.id
            review.created_at = record.created_at
        except Exception:
            await session.rollback()
            raise

    logger.info(
        "Pipeline.run_weekly_review.done | plan=%s summary=%s suggestions=%d",
        plan_id, (review.summary or "")[:30], len(review.suggestions),
    )

    return {"review": review.to_dict()}
