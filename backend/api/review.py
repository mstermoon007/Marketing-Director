"""复盘模块接口（上传文件/提交结构化数据/生成复盘报告）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.agents.reviewer import ReviewAgent
from backend.api.auth import get_current_user
from backend.config.settings import PROJECT_ROOT, app_config
from backend.db.models import (
    AsyncSessionLocal,
    ExecutionPlanRecord,
    ReviewRecord,
)
from backend.models.execution import DayPlan, SevenDayPlan, Task
from backend.utils.document_parser import is_csv_file, is_image_file


logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

# 绝对路径上传目录，防止目录穿透
UPLOAD_DIR = (PROJECT_ROOT / "data" / "uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_staged_uploads: dict[str, list[str]] = {}


# ── 上传安全工具 ──

# Magic byte 签名表：扩展名 → (前N字节签名, 签名长度)
_MAGIC_BYTES: dict[str, tuple] = {
    ".png":  (b"\x89PNG\r\n\x1a\n", 8),
    ".jpg":  (b"\xff\xd8\xff", 3),
    ".jpeg": (b"\xff\xd8\xff", 3),
    ".webp": (b"RIFF", 4),  # 完整校验还需第 8-11 字节为 WEBP
    ".bmp":  (b"BM", 2),
    ".gif":  (b"\x47\x49\x46\x38", 6),  # GIF87a / GIF89a
    ".csv":  (None, 0),  # 文本格式，无 magic byte
    ".tsv":  (None, 0),
}


def _validate_magic_bytes(content: bytes, ext: str) -> bool:
    """校验文件内容头部 magic byte 是否与扩展名匹配。

    Parameters
    ----------
    content : bytes
        文件内容前若干字节。
    ext : str
        文件扩展名（含点号，小写）。

    Returns
    -------
    bool
        magic byte 匹配返回 True，不匹配或无法校验返回 False。
    """
    sig_info = _MAGIC_BYTES.get(ext)
    if sig_info is None:
        # 未知扩展名，不校验 magic byte（由上层扩展名白名单拦截）
        return True
    expected, sig_len = sig_info
    if expected is None:
        # 文本格式（csv/tsv），无 magic byte，跳过
        return True
    if len(content) < sig_len:
        return False
    actual = content[:sig_len]
    if ext == ".webp":
        # WebP: RIFF....WEBP
        return actual == b"RIFF" and content[8:12] == b"WEBP"
    return actual == expected


def _generate_safe_filename(original_name: str, content: bytes) -> str:
    """生成安全的文件名：uuid + 校验过的扩展名。

    拒绝原始文件名中的路径分隔符，仅保留白名单扩展名。

    Parameters
    ----------
    original_name : str
        原始上传文件名。
    content : bytes
        文件内容（用于 magic byte 校验）。

    Returns
    -------
    str
        安全的文件名（uuid + 扩展名）。

    Raises
    ------
    HTTPException
        扩展名不在白名单中或 magic byte 不匹配。
    """
    # 提取扩展名（仅最后一个 . 之后部分，转小写）
    ext = Path(original_name).suffix.lower() if original_name else ""

    allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".csv", ".tsv"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型: {original_name}。支持: {', '.join(sorted(allowed_exts))}",
        )

    # magic byte 校验
    if not _validate_magic_bytes(content, ext):
        raise HTTPException(
            status_code=422,
            detail=f"文件内容与扩展名 {ext} 不匹配（magic byte 校验失败），疑似扩展名伪装",
        )

    # 用 uuid 替代原始文件名，彻底杜绝路径遍历
    return f"{uuid.uuid4().hex}{ext}"


def _safe_write_file(content: bytes, filename: str) -> Path:
    """安全写入文件到 UPLOAD_DIR，确保路径不逃逸。

    Parameters
    ----------
    content : bytes
        文件内容。
    filename : str
        已处理的安全文件名（uuid + 扩展名）。

    Returns
    -------
    Path
        写入后的绝对路径。

    Raises
    ------
    HTTPException
        如果解析后的路径不在 UPLOAD_DIR 内（路径遍历攻击）。
    """
    target = (UPLOAD_DIR / filename).resolve()
    # 安全校验：确保最终路径仍在 UPLOAD_DIR 内
    if not str(target).startswith(str(UPLOAD_DIR)):
        raise HTTPException(
            status_code=422,
            detail="文件路径异常，疑似路径遍历攻击",
        )
    target.write_bytes(content)
    return target


class ReviewResponse(BaseModel):
    """复盘统一响应格式。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class GenerateRequest(BaseModel):
    """生成复盘报告请求体。"""

    files: Optional[list[str]] = Field(None, description="可选文件路径列表，默认使用暂存文件")


class ReviewSubmitRequest(BaseModel):
    """[V3.0] 复盘提交请求体。"""

    review_type: str = Field("weekly", description="复盘类型：weekly/daily/monthly")
    week_number: Optional[int] = Field(1, description="周数")
    plan_id: Optional[str] = Field(None, description="关联执行计划ID（可选）")
    business_id: Optional[str] = Field(None, description="企业ID（可选）")
    completed_tasks: list[str] = Field(default_factory=list, description="已完成任务列表")
    incomplete_tasks: list[str] = Field(default_factory=list, description="未完成任务列表")
    key_takeaway: str = Field("", description="核心收获")
    difficulties: str = Field("", description="遇到的困难")
    images: list[str] = Field(default_factory=list, description="图片URL列表")
    numbers: Optional[dict] = Field(None, description="业务数据，如{'新增客户':5, '咨询量':20}")


class _ReviewerPersistentError(Exception):
    """内部标记：复盘需要 fallback 到规则引擎。"""

    pass


def _build_rule_based_review(
    req: ReviewSubmitRequest,
    plan: Optional[SevenDayPlan] = None,
) -> dict:
    """规则引擎 fallback：基于提交数据生成结构化复盘。"""
    completed_count = len(req.completed_tasks)
    incomplete_count = len(req.incomplete_tasks)
    total = completed_count + incomplete_count
    completion_rate = round((completed_count / total) * 100, 1) if total > 0 else 100.0

    numbers = req.numbers or {"新增客户": 0, "咨询量": 0, "成交量": 0}

    what_worked: list[str] = []
    if req.key_takeaway:
        what_worked.append(req.key_takeaway)
    if completed_count > 0:
        what_worked.append(f"本周完成{completed_count}项任务，完成率{completion_rate}%")
    if not what_worked:
        what_worked.append("本周基础工作推进顺利")

    what_didnt: list[str] = []
    if req.difficulties:
        what_didnt.append(req.difficulties)
    if incomplete_count > 0:
        what_didnt.append(f"有{incomplete_count}项任务未完成，需分析原因")
    if not what_didnt:
        what_didnt.append("暂无明显短板，继续保持")

    suggestions = [
        "下周优先完成本周遗留的未完成任务",
        "针对最大困难制定具体解决步骤",
        "每天固定时间段复盘当日进度",
    ]

    vs_target: list[dict] = []
    for metric_name, actual in numbers.items():
        try:
            actual_val = int(actual) if isinstance(actual, (int, float)) else 0
        except Exception:
            actual_val = 0
        target_val = max(actual_val, 1)
        vs_target.append(
            {
                "metric_name": metric_name,
                "target": target_val,
                "actual": actual_val,
                "achieved": actual_val >= target_val,
            }
        )

    summary_parts = [f"第{req.week_number}周复盘：完成率{completion_rate}%。"]
    if req.key_takeaway:
        summary_parts.append(req.key_takeaway)
    if req.difficulties:
        summary_parts.append(f" 困难点：{req.difficulties}")
    summary = "".join(summary_parts).strip()

    return {
        "id": uuid.uuid4().hex,
        "plan_id": req.plan_id or "",
        "business_id": req.business_id or "",
        "week_number": req.week_number,
        "review_type": req.review_type,
        "summary": summary,
        "numbers": numbers,
        "vs_target": vs_target,
        "what_worked": what_worked,
        "what_didnt": what_didnt,
        "suggestions": suggestions,
        "completed_tasks": req.completed_tasks,
        "incomplete_tasks": req.incomplete_tasks,
        "key_takeaway": req.key_takeaway,
        "difficulties": req.difficulties,
        "images": req.images,
        "review_source": "rule_based",
    }


async def _generate_review_with_fallback(
    plan: Optional[SevenDayPlan],
    uploaded_files: Optional[list[str]],
    submit_req: Optional[ReviewSubmitRequest] = None,
) -> dict:
    """复盘 Agent 3次重试 + 规则引擎兜底。"""
    last_error = None
    for attempt in range(1, 4):
        try:
            agent = ReviewAgent()
            files_list = uploaded_files or []
            if plan:
                review = await agent.run(plan=plan, uploaded_files=files_list)
                result = review.to_dict()
                result["review_source"] = "llm"
                if submit_req:
                    result["week_number"] = submit_req.week_number
                    result["review_type"] = submit_req.review_type
                    result["completed_tasks"] = submit_req.completed_tasks
                    result["incomplete_tasks"] = submit_req.incomplete_tasks
                    result["key_takeaway"] = submit_req.key_takeaway
                    result["difficulties"] = submit_req.difficulties
                    result["images"] = submit_req.images
                logger.info("复盘Agent第%d次调用成功", attempt)
                return result
        except Exception as e:
            last_error = e
            logger.warning("复盘Agent第%d次调用失败: %s", attempt, e)
            continue

    logger.warning("复盘Agent连续3次失败，回退到规则引擎: %s", last_error)
    return _build_rule_based_review(submit_req or ReviewSubmitRequest(), plan)


def _record_to_plan(record: ExecutionPlanRecord) -> SevenDayPlan:
    """DB ExecutionPlanRecord 转换为业务模型 SevenDayPlan。"""
    days: list[DayPlan] = []
    for d in record.days or []:
        if isinstance(d, dict):
            tasks: list[Task] = [
                Task.from_dict(t) if isinstance(t, dict) else t for t in d.get("tasks", [])
            ]
            days.append(
                DayPlan(
                    day_label=d.get("day_label", ""),
                    focus=d.get("focus", ""),
                    tasks=tasks,
                )
            )

    return SevenDayPlan(
        id=record.id,
        diagnosis_id=record.diagnosis_id,
        business_id=record.business_id,
        start_date=record.start_date,
        theme=record.theme or "",
        goals=record.goals or [],
        key_metrics=record.key_metrics or {},
        days=days,
    )


@router.post("/review/{plan_id}/upload", response_model=ReviewResponse)
async def upload_single_file(plan_id: str, file: UploadFile = File(...)) -> ReviewResponse:
    """逐文件上传到暂存区（适配微信小程序 wx.uploadFile）。"""
    if not file.filename:
        raise HTTPException(status_code=422, detail="缺少文件名")
    if not is_image_file(file.filename) and not is_csv_file(file.filename):
        raise HTTPException(
            status_code=422,
            detail=(f"不支持的文件类型: {file.filename}。" "请上传 PNG/JPG 截图或 CSV 文件。"),
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > app_config.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=(f"文件 {file.filename} 超过 " f"{app_config.max_upload_size_mb}MB 限制"),
        )

    # 安全文件名生成 + magic byte 校验 + 路径遍历防护
    safe_filename = _generate_safe_filename(file.filename, content)
    target = _safe_write_file(content, safe_filename)

    saved_path = str(target)

    if plan_id not in _staged_uploads:
        _staged_uploads[plan_id] = []
    _staged_uploads[plan_id].append(saved_path)

    return ReviewResponse(
        data={
            "file_path": saved_path,
            "staged_count": len(_staged_uploads[plan_id]),
            "plan_id": plan_id,
        }
    )


@router.post("/review/{plan_id}/generate", response_model=ReviewResponse)
async def generate_review_report(
    plan_id: str, req: Optional[GenerateRequest] = None
) -> ReviewResponse:
    """使用已暂存的文件（或请求体传入的文件路径）生成复盘报告。"""
    saved_paths = (
        list(req.files)
        if req and req.files
        else list(_staged_uploads.get(plan_id, []))
    )

    if not saved_paths:
        raise HTTPException(
            status_code=422,
            detail=f"请先上传文件（使用 /review/{plan_id}/upload 接口）",
        )

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(ExecutionPlanRecord).filter_by(id=plan_id)
            )
            plan_record = result.scalar_one_or_none()
            if not plan_record:
                raise HTTPException(status_code=404, detail="执行计划不存在")

            plan = _record_to_plan(plan_record)
            agent = ReviewAgent()
            review = await agent.run(plan=plan, uploaded_files=saved_paths)

            db_record = ReviewRecord(
                plan_id=plan_id,
                business_id=plan_record.business_id,
                summary=review.summary,
                numbers=review.numbers,
                vs_target=review.to_dict()["vs_target"],
                what_worked=review.what_worked,
                what_didnt=review.what_didnt,
                suggestions=review.suggestions,
            )
            session.add(db_record)
            await session.commit()
            await session.refresh(db_record)

            review.id = db_record.id
            review.created_at = db_record.created_at

            _staged_uploads.pop(plan_id, None)

            logger.info(
                "复盘完成: review=%s summary=%s suggestions=%d",
                review.id,
                (review.summary or "")[:30],
                len(review.suggestions),
            )

            return ReviewResponse(data=review.to_dict())

        except ValueError as e:
            logger.error("复盘 Agent 异常: %s", e)
            raise HTTPException(status_code=502, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.exception("复盘失败: %s", e)
            raise HTTPException(status_code=500, detail=f"复盘失败: {e}") from e


@router.post("/review/{plan_id}", response_model=ReviewResponse)
async def create_review_legacy(
    plan_id: str,
    files: list[UploadFile] = File(...),
) -> ReviewResponse:
    """[兼容旧版] 一次性上传多文件并生成复盘报告。"""
    if not files:
        raise HTTPException(status_code=422, detail="请上传至少一个文件")

    saved_paths: list[str] = []

    for f in files:
        content = await f.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > app_config.max_upload_size_mb:
            raise HTTPException(
                status_code=413,
                detail=(f"文件 {f.filename} 超过 " f"{app_config.max_upload_size_mb}MB 限制"),
            )
        if not is_image_file(f.filename or "") and not is_csv_file(f.filename or ""):
            raise HTTPException(
                status_code=422,
                detail=(f"不支持的文件类型: {f.filename}。" "请上传 PNG/JPG 截图或 CSV 文件。"),
            )

        # 安全文件名 + magic byte + 路径遍历防护
        safe_filename = _generate_safe_filename(f.filename or "", content)
        target = _safe_write_file(content, safe_filename)
        saved_paths.append(str(target))

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(ExecutionPlanRecord).filter_by(id=plan_id)
            )
            plan_record = result.scalar_one_or_none()
            if not plan_record:
                raise HTTPException(status_code=404, detail="执行计划不存在")

            plan = _record_to_plan(plan_record)
            agent = ReviewAgent()
            review = await agent.run(plan=plan, uploaded_files=saved_paths)

            db_record = ReviewRecord(
                plan_id=plan_id,
                business_id=plan_record.business_id,
                summary=review.summary,
                numbers=review.numbers,
                vs_target=review.to_dict()["vs_target"],
                what_worked=review.what_worked,
                what_didnt=review.what_didnt,
                suggestions=review.suggestions,
            )
            session.add(db_record)
            await session.commit()
            await session.refresh(db_record)

            review.id = db_record.id
            review.created_at = db_record.created_at

            logger.info(
                "复盘完成[legacy]: review=%s summary=%s suggestions=%d",
                review.id,
                (review.summary or "")[:30],
                len(review.suggestions),
            )

            return ReviewResponse(data=review.to_dict())

        except ValueError as e:
            logger.error("复盘 Agent 异常: %s", e)
            raise HTTPException(status_code=502, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.exception("复盘失败: %s", e)
            raise HTTPException(status_code=500, detail=f"复盘失败: {e}") from e


@router.post("/review/submit", response_model=ReviewResponse)
async def submit_review_v3(req: ReviewSubmitRequest) -> ReviewResponse:
    """[V3.0] 提交复盘报告（文档6.2节规范）。"""
    async with AsyncSessionLocal() as session:
        try:
            plan = None
            business_id = req.business_id
            plan_id = req.plan_id

            if plan_id:
                result = await session.execute(
                    select(ExecutionPlanRecord).filter_by(id=plan_id)
                )
                plan_record = result.scalar_one_or_none()
                if plan_record:
                    plan = _record_to_plan(plan_record)
                    business_id = business_id or plan_record.business_id
            elif business_id:
                result = await session.execute(
                    select(ExecutionPlanRecord)
                    .filter_by(business_id=business_id)
                    .order_by(ExecutionPlanRecord.created_at.desc())
                )
                plan_record = result.scalars().first()
                if plan_record:
                    plan = _record_to_plan(plan_record)
                    plan_id = plan_record.id

            review_data = await _generate_review_with_fallback(
                plan=plan,
                uploaded_files=[],
                submit_req=req,
            )

            final_business_id = business_id or (plan.business_id if plan else "")
            final_plan_id = plan_id or (plan.id if plan else "")

            db_record = ReviewRecord(
                id=uuid.uuid4().hex,
                plan_id=final_plan_id,
                business_id=final_business_id,
                summary=review_data.get("summary", ""),
                numbers=review_data.get("numbers", {}),
                vs_target=review_data.get("vs_target", []),
                what_worked=review_data.get("what_worked", []),
                what_didnt=review_data.get("what_didnt", []),
                suggestions=review_data.get("suggestions", []),
            )
            session.add(db_record)
            await session.commit()
            await session.refresh(db_record)

            review_data["id"] = db_record.id
            review_data["created_at"] = (
                db_record.created_at.isoformat() if db_record.created_at else None
            )
            review_data["business_id"] = final_business_id
            review_data["plan_id"] = final_plan_id

            logger.info(
                "[V3.0]复盘提交成功: review=%s week=%s source=%s",
                db_record.id,
                req.week_number,
                review_data.get("review_source", "unknown"),
            )

            return ReviewResponse(data=review_data)

        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            logger.exception("[V3.0]复盘提交失败: %s", e)
            raise HTTPException(status_code=500, detail=f"复盘提交失败: {e}") from e


@router.get("/review/latest", response_model=ReviewResponse)
async def get_latest_review_v3(
    business_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> ReviewResponse:
    """[V3.0] 获取最新复盘报告。"""
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(ReviewRecord)
            if plan_id:
                stmt = stmt.filter_by(plan_id=plan_id)
            elif business_id:
                stmt = stmt.filter_by(business_id=business_id)
            stmt = stmt.order_by(ReviewRecord.created_at.desc())
            result = await session.execute(stmt)
            record = result.scalars().first()

            if not record:
                raise HTTPException(status_code=404, detail="暂无复盘数据")

            data = {
                "id": record.id,
                "plan_id": record.plan_id,
                "business_id": record.business_id,
                "summary": record.summary,
                "numbers": record.numbers,
                "vs_target": record.vs_target,
                "what_worked": record.what_worked,
                "what_didnt": record.what_didnt,
                "suggestions": record.suggestions,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }

            return ReviewResponse(data=data)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("获取复盘报告失败: %s", e)
            raise HTTPException(status_code=500, detail=f"获取失败: {e}") from e


@router.get("/review/{plan_id}", response_model=ReviewResponse)
async def get_review(plan_id: str) -> ReviewResponse:
    """查看最新复盘报告。"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(ReviewRecord)
                .filter_by(plan_id=plan_id)
                .order_by(ReviewRecord.created_at.desc())
            )
            record = result.scalars().first()
            if not record:
                raise HTTPException(status_code=404, detail="尚未生成复盘报告")

            return ReviewResponse(
                data={
                    "id": record.id,
                    "plan_id": record.plan_id,
                    "business_id": record.business_id,
                    "summary": record.summary,
                    "numbers": record.numbers,
                    "vs_target": record.vs_target,
                    "what_worked": record.what_worked,
                    "what_didnt": record.what_didnt,
                    "suggestions": record.suggestions,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("获取复盘报告失败: %s", e)
            raise HTTPException(status_code=500, detail=f"获取失败: {e}") from e
