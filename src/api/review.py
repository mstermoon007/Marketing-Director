"""复盘模块接口（上传文件/提交结构化数据/生成复盘报告）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.agents.reviewer import ReviewAgent
from src.config.settings import PROJECT_ROOT, app_config
from src.db.models import (
    ExecutionPlanRecord,
    ReviewRecord,
    SyncSession,
)
from src.models.execution import DayPlan, SevenDayPlan, Task
from src.utils.document_parser import is_csv_file, is_image_file


logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_staged_uploads: Dict[str, List[str]] = {}


class ReviewResponse(BaseModel):
    """复盘统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        复盘报告数据载荷。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class GenerateRequest(BaseModel):
    """生成复盘报告请求体。

    Parameters
    ----------
    files : Optional[List[str]]
        可选的文件路径列表，未提供则使用暂存文件。
    """

    files: Optional[List[str]] = Field(None, description="可选文件路径列表，默认使用暂存文件")


class ReviewSubmitRequest(BaseModel):
    """[V3.0] 复盘提交请求体。

    Parameters
    ----------
    review_type : str
        复盘类型：weekly/daily/monthly。
    week_number : Optional[int]
        周数。
    plan_id : Optional[str]
        关联执行计划ID（可选）。
    business_id : Optional[str]
        企业ID（可选）。
    completed_tasks : List[str]
        已完成任务列表。
    incomplete_tasks : List[str]
        未完成任务列表。
    key_takeaway : str
        核心收获。
    difficulties : str
        遇到的困难。
    images : List[str]
        图片URL列表。
    numbers : Optional[dict]
        业务数据，如 {"新增客户": 5, "咨询量": 20}。
    """

    review_type: str = Field("weekly", description="复盘类型：weekly/daily/monthly")
    week_number: Optional[int] = Field(1, description="周数")
    plan_id: Optional[str] = Field(None, description="关联执行计划ID（可选）")
    business_id: Optional[str] = Field(None, description="企业ID（可选）")
    completed_tasks: List[str] = Field(default_factory=list, description="已完成任务列表")
    incomplete_tasks: List[str] = Field(default_factory=list, description="未完成任务列表")
    key_takeaway: str = Field("", description="核心收获")
    difficulties: str = Field("", description="遇到的困难")
    images: List[str] = Field(default_factory=list, description="图片URL列表")
    numbers: Optional[dict] = Field(None, description="业务数据，如{'新增客户':5, '咨询量':20}")


class _ReviewerPersistentError(Exception):
    """内部标记：复盘需要 fallback 到规则引擎。"""

    pass


def _build_rule_based_review(
    req: ReviewSubmitRequest,
    plan: Optional[SevenDayPlan] = None,
) -> dict:
    """规则引擎 fallback：基于提交数据生成结构化复盘。

    Parameters
    ----------
    req : ReviewSubmitRequest
        复盘提交请求体。
    plan : Optional[SevenDayPlan]
        关联的7天计划（可选）。

    Returns
    -------
    dict
        结构化复盘数据，包含 summary、numbers、vs_target、
        what_worked、what_didnt、suggestions 等。
    """
    completed_count = len(req.completed_tasks)
    incomplete_count = len(req.incomplete_tasks)
    total = completed_count + incomplete_count
    completion_rate = round((completed_count / total) * 100, 1) if total > 0 else 100.0

    numbers = req.numbers or {"新增客户": 0, "咨询量": 0, "成交量": 0}

    what_worked: List[str] = []
    if req.key_takeaway:
        what_worked.append(req.key_takeaway)
    if completed_count > 0:
        what_worked.append(f"本周完成{completed_count}项任务，完成率{completion_rate}%")
    if not what_worked:
        what_worked.append("本周基础工作推进顺利")

    what_didnt: List[str] = []
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

    vs_target: List[dict] = []
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
    uploaded_files: Optional[List[str]],
    submit_req: Optional[ReviewSubmitRequest] = None,
) -> dict:
    """复盘 Agent 3次重试 + 规则引擎兜底。

    Parameters
    ----------
    plan : Optional[SevenDayPlan]
        7天计划业务模型。
    uploaded_files : Optional[List[str]]
        已上传文件路径列表。
    submit_req : Optional[ReviewSubmitRequest]
        结构化复盘提交请求（可选）。

    Returns
    -------
    dict
        结构化复盘报告数据，附带 review_source 标识。
    """
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
    """DB ExecutionPlanRecord 转换为业务模型 SevenDayPlan。

    Parameters
    ----------
    record : ExecutionPlanRecord
        数据库执行计划记录。

    Returns
    -------
    SevenDayPlan
        转换后的7天计划业务模型实例。
    """
    days: List[DayPlan] = []
    for d in record.days or []:
        if isinstance(d, dict):
            tasks: List[Task] = [
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


def _save_single_upload(file: UploadFile) -> str:
    """保存单个上传文件到磁盘，返回绝对路径字符串。

    Parameters
    ----------
    file : UploadFile
        FastAPI 上传文件对象。

    Returns
    -------
    str
        保存后的绝对文件路径。

    Raises
    ------
    HTTPException
        当缺少文件名时返回 422 错误。
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="缺少文件名")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
    target = UPLOAD_DIR / safe_filename

    return str(target)


@router.post("/review/{plan_id}/upload", response_model=ReviewResponse)
async def upload_single_file(plan_id: str, file: UploadFile = File(...)) -> ReviewResponse:
    """逐文件上传到暂存区（适配微信小程序 wx.uploadFile）。

    每次上传 1 个文件。成功后将文件加入该 plan 的暂存区，
    之后可通过 /review/{plan_id}/generate 生成复盘报告。

    Parameters
    ----------
    plan_id : str
        执行计划ID（路径参数）。
    file : UploadFile
        上传文件（PNG/JPG 截图或 CSV 文件）。

    Returns
    -------
    ReviewResponse
        data 包含 file_path、staged_count、plan_id。

    Raises
    ------
    HTTPException
        - 422: 缺少文件名或不支持的文件类型。
        - 413: 文件超过大小限制。
    """
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
    target = UPLOAD_DIR / safe_filename
    target.write_bytes(content)

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
    """使用已暂存的文件（或请求体传入的文件路径）生成复盘报告。

    调用后会清空该 plan 的暂存区。

    Parameters
    ----------
    plan_id : str
        执行计划ID（路径参数）。
    req : Optional[GenerateRequest]
        可选请求体，可传入 files 列表覆盖暂存区。

    Returns
    -------
    ReviewResponse
        生成的复盘报告数据。

    Raises
    ------
    HTTPException
        - 422: 未找到文件。
        - 404: 执行计划不存在。
        - 502: 复盘 Agent 异常。
        - 500: 内部处理异常。
    """
    saved_paths = (
        list(req.files)
        if req and req.files
        else list(_staged_uploads.get(plan_id, []))
    )

    if not saved_paths:
        raise HTTPException(
            status_code=422,
            detail="请先上传文件（使用 /review/{plan_id}/upload 接口）",
        )

    session = SyncSession()
    try:
        plan_record = session.query(ExecutionPlanRecord).filter_by(id=plan_id).first()
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
        session.commit()
        session.refresh(db_record)

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
        session.rollback()
        logger.exception("复盘失败: %s", e)
        raise HTTPException(status_code=500, detail=f"复盘失败: {e}") from e
    finally:
        session.close()


@router.post("/review/{plan_id}", response_model=ReviewResponse)
async def create_review_legacy(
    plan_id: str,
    files: List[UploadFile] = File(...),
) -> ReviewResponse:
    """[兼容旧版] 一次性上传多文件并生成复盘报告。

    小程序端建议改用：
      1) POST /review/{plan_id}/upload   （逐个上传）
      2) POST /review/{plan_id}/generate （生成报告）

    Parameters
    ----------
    plan_id : str
        执行计划ID（路径参数）。
    files : List[UploadFile]
        批量上传文件列表。

    Returns
    -------
    ReviewResponse
        生成的复盘报告数据。

    Raises
    ------
    HTTPException
        - 422: 未上传文件或不支持的文件类型。
        - 413: 文件超过大小限制。
        - 404: 执行计划不存在。
        - 502: 复盘 Agent 异常。
        - 500: 内部处理异常。
    """
    if not files:
        raise HTTPException(status_code=422, detail="请上传至少一个文件")

    saved_paths: List[str] = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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
        file_path = UPLOAD_DIR / f"{timestamp}_{uuid.uuid4().hex[:8]}_{f.filename}"
        file_path.write_bytes(content)
        saved_paths.append(str(file_path))

    session = SyncSession()
    try:
        plan_record = session.query(ExecutionPlanRecord).filter_by(id=plan_id).first()
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
        session.commit()
        session.refresh(db_record)

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
        session.rollback()
        logger.exception("复盘失败: %s", e)
        raise HTTPException(status_code=500, detail=f"复盘失败: {e}") from e
    finally:
        session.close()


@router.post("/review/submit", response_model=ReviewResponse)
async def submit_review_v3(req: ReviewSubmitRequest) -> ReviewResponse:
    """[V3.0] 提交复盘报告（文档6.2节规范）。

    接收结构化数据：review_type, week_number, plan_id?, business_id?,
    completed_tasks[], incomplete_tasks[], key_takeaway, difficulties,
    images[], numbers?。

    内部：3次Agent重试 + 规则引擎兜底。

    Parameters
    ----------
    req : ReviewSubmitRequest
        结构化复盘提交请求体。

    Returns
    -------
    ReviewResponse
        保存后的复盘报告数据。

    Raises
    ------
    HTTPException
        - 500: 内部处理异常。
    """
    session = SyncSession()
    try:
        plan = None
        business_id = req.business_id
        plan_id = req.plan_id

        if plan_id:
            plan_record = session.query(ExecutionPlanRecord).filter_by(id=plan_id).first()
            if plan_record:
                plan = _record_to_plan(plan_record)
                business_id = business_id or plan_record.business_id
        elif business_id:
            plan_record = (
                session.query(ExecutionPlanRecord)
                .filter_by(business_id=business_id)
                .order_by(ExecutionPlanRecord.created_at.desc())
                .first()
            )
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
        session.commit()
        session.refresh(db_record)

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
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.exception("[V3.0]复盘提交失败: %s", e)
        raise HTTPException(status_code=500, detail=f"复盘提交失败: {e}") from e
    finally:
        session.close()


@router.get("/review/latest", response_model=ReviewResponse)
async def get_latest_review_v3(
    business_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> ReviewResponse:
    """[V3.0] 获取最新复盘报告。

    优先级：plan_id > business_id > 全表最新一条。

    Parameters
    ----------
    business_id : Optional[str]
        企业ID（可选查询参数）。
    plan_id : Optional[str]
        计划ID（可选查询参数）。

    Returns
    -------
    ReviewResponse
        最新复盘报告数据。

    Raises
    ------
    HTTPException
        - 404: 暂无复盘数据。
    """
    session = SyncSession()
    try:
        query = session.query(ReviewRecord)
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
        elif business_id:
            query = query.filter_by(business_id=business_id)
        record = query.order_by(ReviewRecord.created_at.desc()).first()

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
    finally:
        session.close()


@router.get("/review/{plan_id}", response_model=ReviewResponse)
async def get_review(plan_id: str) -> ReviewResponse:
    """查看最新复盘报告。

    Parameters
    ----------
    plan_id : str
        执行计划ID（路径参数）。

    Returns
    -------
    ReviewResponse
        该计划最新复盘报告数据。

    Raises
    ------
    HTTPException
        - 404: 尚未生成复盘报告。
    """
    session = SyncSession()
    try:
        record = (
            session.query(ReviewRecord)
            .filter_by(plan_id=plan_id)
            .order_by(ReviewRecord.created_at.desc())
            .first()
        )
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
    finally:
        session.close()
