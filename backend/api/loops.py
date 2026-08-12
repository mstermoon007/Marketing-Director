"""
闭环业务接口（阶段四 · 功能闭环）
================================

把诊断 / 计划 / 排期 / 数据上传 / 复盘 / 持续学习 六大能力从「单次对话输出」
升级为「可保存、可编辑、可确认、可反馈」的完整业务闭环。

所有接口均需 JWT 鉴权；涉及企业的操作按当前用户归属处理。
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from backend.agent_core.learning import record_feedback
from backend.agent_core.tools import calculate_kpi, persist_todos, upload_and_parse_data
from backend.api.auth import get_current_user
from backend.api.review import _generate_safe_filename, _safe_write_file
from backend.config.settings import app_config
from backend.db.models import (
    AsyncSessionLocal,
    BusinessRecord,
    ExecutionPlanRecord,
    MetricRecord,
    ReviewRecord,
    TodoRecord,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# 请求体
# ──────────────────────────────────────────────
class PlanConfirmResponse(BaseModel):
    ok: bool = True
    plan_id: str = ""
    schedule: list = []


class PlanEditItem(BaseModel):
    day_index: int
    task_index: int
    title: Optional[str] = None
    time_slot: Optional[str] = None
    how_to: Optional[str] = None
    checklist: Optional[list[str]] = None


class PlanEditRequest(BaseModel):
    edits: list[PlanEditItem] = []


class CheckinRequest(BaseModel):
    todo_id: str
    status: Optional[str] = None  # pending | doing | done
    notes: Optional[str] = None
    images: Optional[list[str]] = None


class ScheduleSyncRequest(BaseModel):
    business_id: str = ""
    plan_id: Optional[str] = None
    days: list = []


class ReviewTriggerRequest(BaseModel):
    business_id: str = ""
    week_number: Optional[int] = None


class ReviewApplyRequest(BaseModel):
    business_id: str = ""


class FeedbackRequest(BaseModel):
    target_type: str  # diagnosis | plan | schedule | review | card | suggestion
    target_id: Optional[str] = None
    rating: int = 0  # +1 / -1 / 0
    comment: Optional[str] = None
    business_id: Optional[str] = None
    card_ids: list[str] = []


# ──────────────────────────────────────────────
# 辅助
# ──────────────────────────────────────────────
async def _resolve_business(user_id: str, business_id: str | None) -> Optional[str]:
    """解析当前用户归属的企业 ID。"""
    if business_id:
        return business_id
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(
                select(BusinessRecord)
                .filter_by(user_id=user_id)
                .order_by(BusinessRecord.created_at.desc())
            )
        ).scalars().first()
        if rec:
            return rec.id
        rec = (
            await session.execute(select(BusinessRecord).order_by(BusinessRecord.created_at.desc()))
        ).scalars().first()
        return rec.id if rec else None


def _flatten_schedule(days: list[dict]) -> list[dict]:
    out = []
    for g in days or []:
        for t in g.get("tasks", []) or []:
            if isinstance(t, dict) and t.get("title"):
                out.append({
                    "day_index": g.get("day_index"),
                    "date": g.get("date"),
                    "title": t.get("title"),
                    "time_slot": t.get("time_slot"),
                    "how_to": t.get("how_to"),
                })
    return out


# ──────────────────────────────────────────────
# 计划：确认 / 微调 / 重新生成
# ──────────────────────────────────────────────
@router.post("/plan/{plan_id}/confirm", response_model=PlanConfirmResponse)
async def confirm_plan(plan_id: str, user: dict = Depends(get_current_user)) -> PlanConfirmResponse:
    """确认计划 → 标记 confirmed 并自动排期落库 todos。"""
    user_id = user["user_id"]
    async with AsyncSessionLocal() as session:
        plan = (
            await session.execute(select(ExecutionPlanRecord).filter_by(id=plan_id))
        ).scalar_one_or_none()
        if not plan:
            return PlanConfirmResponse(ok=False, plan_id=plan_id)
        plan.status = "confirmed"
        plan.confirmed_at = _utcnow()
        days = plan.days or []
        await session.commit()
        await session.refresh(plan)

        result = await persist_todos(plan.business_id, user_id, plan.id, days)
        logger.info("计划 %s 已确认并排期，落库 %d 条待办", plan_id, result.get("persisted", 0))

    return PlanConfirmResponse(ok=True, plan_id=plan_id, schedule=_flatten_schedule(days))


@router.post("/plan/{plan_id}/edit")
async def edit_plan(
    plan_id: str, req: PlanEditRequest, user: dict = Depends(get_current_user)
) -> dict:
    """微调计划中的任务（标题/时段/做法/清单），写回计划的 days JSON。"""
    async with AsyncSessionLocal() as session:
        plan = (
            await session.execute(select(ExecutionPlanRecord).filter_by(id=plan_id))
        ).scalar_one_or_none()
        if not plan:
            return {"ok": False, "error": "计划不存在"}
        days = plan.days or []
        for e in req.edits:
            day = next((d for d in days if d.get("day_index") == e.day_index), None)
            if not day:
                continue
            tasks = day.get("tasks", []) or []
            if 0 <= e.task_index < len(tasks):
                t = tasks[e.task_index]
                if e.title is not None:
                    t["title"] = e.title
                if e.time_slot is not None:
                    t["time_slot"] = e.time_slot
                if e.how_to is not None:
                    t["how_to"] = e.how_to
                if e.checklist is not None:
                    t["checklist"] = e.checklist
        plan.days = days
        await session.commit()
        await session.refresh(plan)
    return {"ok": True, "plan": plan.to_dict() if hasattr(plan, "to_dict") else _plan_to_dict(plan)}


@router.post("/plan/{plan_id}/regenerate")
async def regenerate_plan(plan_id: str, user: dict = Depends(get_current_user)) -> dict:
    """基于同一企业重新生成计划（结合已有记忆/反馈）。"""
    async with AsyncSessionLocal() as session:
        plan = (
            await session.execute(select(ExecutionPlanRecord).filter_by(id=plan_id))
        ).scalar_one_or_none()
        if not plan:
            return {"ok": False, "error": "计划不存在"}
        business_id = plan.business_id
    from backend.agent_core.tools import generate_plan

    res = await generate_plan(business_id)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error", "生成失败")}
    return {"ok": True, "plan": res.get("plan"), "diagnosis": res.get("diagnosis")}


# ──────────────────────────────────────────────
# 排期：打卡 / 同步 / 读取
# ──────────────────────────────────────────────
@router.put("/schedule/checkin")
async def checkin_todo(req: CheckinRequest, user: dict = Depends(get_current_user)) -> dict:
    """任务完成打卡 / 修改状态，落库 todos（闭环：完成标记反馈至复盘 Agent）。"""
    async with AsyncSessionLocal() as session:
        todo = (
            await session.execute(select(TodoRecord).filter_by(id=req.todo_id))
        ).scalar_one_or_none()
        if not todo:
            return {"ok": False, "error": "任务不存在"}
        if req.status is not None:
            todo.status = req.status
            todo.completed_at = _utcnow() if req.status == "done" else None
        if req.notes is not None:
            todo.notes = req.notes
        if req.images is not None:
            todo.images = req.images
        await session.commit()
        await session.refresh(todo)
    return {"ok": True, "todo": _todo_to_dict(todo)}


@router.post("/schedule/sync")
async def sync_schedule(req: ScheduleSyncRequest, user: dict = Depends(get_current_user)) -> dict:
    """把排期结果同步落库（用于「安排本周日程」快捷指令或确认后补录）。"""
    user_id = user["user_id"]
    business_id = await _resolve_business(user_id, req.business_id)
    if not business_id:
        return {"ok": False, "error": "尚未建立企业档案，请先诊断。"}
    result = await persist_todos(business_id, user_id, req.plan_id, req.days)
    return {
        "ok": result.get("ok", False),
        "persisted": result.get("persisted", 0),
        "business_id": business_id,
    }


@router.get("/schedule")
async def get_schedule(business_id: str = "", user: dict = Depends(get_current_user)) -> dict:
    """读取当前企业已落库的排期待办（跨会话持久，反映打卡状态）。"""
    user_id = user["user_id"]
    bid = await _resolve_business(user_id, business_id)
    if not bid:
        return {"ok": True, "todos": []}
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(TodoRecord)
                .filter_by(business_id=bid)
                .order_by(TodoRecord.day_index, TodoRecord.created_at)
            )
        ).scalars().all()
        todos = [_todo_to_dict(t) for t in rows]
    return {"ok": True, "business_id": bid, "todos": todos}


# ──────────────────────────────────────────────
# 数据上传：文件 → 解析指标 → 落库
# ──────────────────────────────────────────────
async def _stage_upload(file: UploadFile) -> str:
    """安全落盘上传文件，返回服务端可读的绝对路径。

    复用复盘接口已加固的三道校验：扩展名白名单 → magic byte 防伪装 →
    uuid 重命名 + 路径逃逸检查，另加大小限制。
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="缺少文件名")
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > app_config.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"文件 {file.filename} 超过 {app_config.max_upload_size_mb}MB 限制",
        )
    safe_name = _generate_safe_filename(file.filename, content)
    return str(_safe_write_file(content, safe_name))


@router.post("/files/upload")
async def files_upload(
    file: UploadFile = File(...), user: dict = Depends(get_current_user)
) -> dict:
    """通用文件暂存：小程序本地临时路径 → 服务端可读路径。

    返回的 ``file_path`` 可直接放进 ``/agent/chat`` 或 ``/agent/chat/stream``
    的 ``files`` 字段——这是「对话里发数据 → Agent 真能读到」的关键一步，
    否则小程序传过来的只是设备本地临时路径，服务端根本打不开。
    """
    path = await _stage_upload(file)
    return {"ok": True, "file_path": path}


@router.post("/metrics/upload")
async def metrics_upload(
    file: UploadFile = File(...),
    business_id: str = "",
    user: dict = Depends(get_current_user),
) -> dict:
    """上传截图/CSV → 解析为结构化指标 → 落库 metrics → 返回 KPI。"""
    user_id = user["user_id"]
    bid = await _resolve_business(user_id, business_id)
    if not bid:
        return {"ok": False, "error": "尚未建立企业档案，请先诊断。"}

    path = await _stage_upload(file)
    parsed = await upload_and_parse_data([path])
    merged = parsed.get("merged_numbers") or {}
    if not merged:
        return {"ok": False, "error": "未解析到有效指标数字", "parsed": parsed}

    async with AsyncSessionLocal() as session:
        rec = MetricRecord(business_id=bid, user_id=user_id, source="upload", numbers=merged)
        session.add(rec)
        await session.commit()

    targets = await _latest_plan_targets(bid)
    kpi = calculate_kpi(merged, targets=targets)

    with contextlib.suppress(OSError):
        os.remove(path)

    return {"ok": True, "merged_numbers": merged, "kpi": kpi, "business_id": bid}


# ──────────────────────────────────────────────
# 复盘：触发 / 应用建议
# ──────────────────────────────────────────────
@router.post("/review/trigger")
async def review_trigger(req: ReviewTriggerRequest, user: dict = Depends(get_current_user)) -> dict:
    """生成本周复盘报告 + 下周建议，并写入 ReviewRecord。

    优先使用用户上传的指标作为实际值；若无上传数据则提示先上传。
    """
    user_id = user["user_id"]
    bid = await _resolve_business(user_id, req.business_id)
    if not bid:
        return {"ok": False, "error": "尚未建立企业档案，请先诊断。"}

    numbers = await _latest_metrics(bid)
    if not numbers:
        return {
            "ok": False,
            "needs_upload": True,
            "error": "本周还没有上传业务数据，请先上传 CSV/截图再复盘。",
        }
    targets = await _latest_plan_targets(bid)
    kpi = calculate_kpi(numbers, targets=targets)

    suggestions = _build_suggestions(kpi)
    summary = kpi.get("summary", "")
    what_worked, what_didnt = _split_findings(kpi)

    async with AsyncSessionLocal() as session:
        rec = ReviewRecord(
            plan_id=(await _latest_plan_id(bid) or ""),
            business_id=bid,
            week_number=req.week_number,
            summary=summary,
            numbers=numbers,
            vs_target=kpi.get("rows", []),
            what_worked=what_worked,
            what_didnt=what_didnt,
            suggestions=suggestions,
        )
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        review = rec.to_dict() if hasattr(rec, "to_dict") else _review_to_dict(rec)

    return {"ok": True, "review": review, "needs_upload": False}


@router.post("/review/{review_id}/apply")
async def review_apply(review_id: str, req: ReviewApplyRequest, user: dict = Depends(get_current_user)) -> dict:
    """把复盘建议直接应用到下周：重新生成计划并自动排期。"""
    user_id = user["user_id"]
    bid = await _resolve_business(user_id, req.business_id)
    if not bid:
        return {"ok": False, "error": "尚未建立企业档案，请先诊断。"}

    from backend.agent_core.tools import generate_plan

    res = await generate_plan(bid)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error", "生成失败")}
    plan = res["plan"]
    plan_id = plan.get("id") if isinstance(plan, dict) else getattr(plan, "id", None)
    days = plan.get("days", []) if isinstance(plan, dict) else getattr(plan, "days", [])
    await persist_todos(bid, user_id, plan_id, days)
    return {"ok": True, "plan": plan, "schedule": _flatten_schedule(days)}


# ──────────────────────────────────────────────
# 持续学习：反馈
# ──────────────────────────────────────────────
@router.post("/agent/feedback")
async def agent_feedback(req: FeedbackRequest, user: dict = Depends(get_current_user)) -> dict:
    """采集用户对 Agent 产出的反馈（赞/踩/计划修改），更新策略有效性评分。"""
    user_id = user["user_id"]
    result = await record_feedback(
        user_id=user_id,
        target_type=req.target_type,
        target_id=req.target_id,
        rating=req.rating,
        comment=req.comment,
        business_id=req.business_id,
        card_ids=req.card_ids,
    )
    return result


# ──────────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────────
def _plan_to_dict(p: ExecutionPlanRecord) -> dict:
    return {
        "id": p.id,
        "diagnosis_id": p.diagnosis_id,
        "business_id": p.business_id,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "theme": p.theme,
        "goals": p.goals,
        "key_metrics": p.key_metrics,
        "days": p.days,
        "status": p.status,
        "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
        "week_number": p.week_number,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _todo_to_dict(t: TodoRecord) -> dict:
    return {
        "id": t.id,
        "business_id": t.business_id,
        "plan_id": t.plan_id,
        "day_index": t.day_index,
        "date": t.date,
        "title": t.title,
        "time_slot": t.time_slot,
        "status": t.status,
        "how_to": t.how_to,
        "checklist": json.loads(t.checklist) if t.checklist else None,
        "notes": t.notes,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "images": t.images or [],
    }


def _review_to_dict(r: ReviewRecord) -> dict:
    return {
        "id": r.id,
        "plan_id": r.plan_id,
        "business_id": r.business_id,
        "week_number": r.week_number,
        "summary": r.summary,
        "numbers": r.numbers,
        "vs_target": r.vs_target,
        "what_worked": r.what_worked,
        "what_didnt": r.what_didnt,
        "suggestions": r.suggestions,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _latest_metrics(business_id: str) -> dict:
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(
                select(MetricRecord)
                .filter_by(business_id=business_id)
                .order_by(MetricRecord.created_at.desc())
            )
        ).scalars().first()
        return rec.numbers if rec else {}


async def _latest_plan_targets(business_id: str) -> dict:
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(
                select(ExecutionPlanRecord)
                .filter_by(business_id=business_id)
                .order_by(ExecutionPlanRecord.created_at.desc())
            )
        ).scalars().first()
        return rec.key_metrics if rec and rec.key_metrics else {}


async def _latest_plan_id(business_id: str) -> Optional[str]:
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(
                select(ExecutionPlanRecord)
                .filter_by(business_id=business_id)
                .order_by(ExecutionPlanRecord.created_at.desc())
            )
        ).scalars().first()
        return rec.id if rec else None


def _build_suggestions(kpi: dict) -> list[str]:
    """根据 KPI 结果生成下周执行建议。"""
    suggestions: list[str] = []
    for row in kpi.get("rows", []):
        target = row.get("target")
        actual = row.get("actual")
        rate = row.get("achievement_rate")
        if target and rate is not None and rate < 100:
            suggestions.append(
                f"【{row['metric']}】本周达成 {actual}/{target}（{rate}%），下周重点补齐缺口，加大对应渠道投入。"
            )
    if kpi.get("derived"):
        tips = "、".join(f"{k}={v}" for k, v in kpi["derived"].items())
        suggestions.append(f"派生指标提示：{tips}，可作为下周优化抓手。")
    if not suggestions:
        suggestions.append("本周目标整体达成良好，下周可在稳定基本盘的同时尝试 1 个新渠道小步测试。")
    return suggestions


def _split_findings(kpi: dict) -> tuple[list[str], list[str]]:
    worked, didnt = [], []
    for row in kpi.get("rows", []):
        rate = row.get("achievement_rate")
        if rate is not None and rate >= 100:
            worked.append(f"{row['metric']} 达标（{row['actual']}/{row['target']}）")
        elif rate is not None:
            didnt.append(f"{row['metric']} 未达标（{row['actual']}/{row['target']}）")
    return worked, didnt
