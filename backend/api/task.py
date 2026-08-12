"""任务模块接口（任务详情/打卡/上传执行记录）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.auth import get_current_user
from backend.config.settings import PROJECT_ROOT, app_config
from backend.db.models import AsyncSessionLocal, TodoRecord


logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

# 绝对路径上传目录，防止目录穿透
UPLOAD_DIR = (PROJECT_ROOT / "data" / "task_uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _todo_to_dict(t: TodoRecord) -> dict:
    """将 TodoRecord ORM 对象转为 API 响应字典。"""
    return {
        "task_id": t.id,
        "business_id": t.business_id,
        "plan_id": t.plan_id,
        "day_index": t.day_index,
        "date": t.date,
        "title": t.title,
        "time_slot": t.time_slot,
        "status": t.status,
        "how_to": t.how_to,
        "checklist": json.loads(t.checklist) if isinstance(t.checklist, str) else (t.checklist or []),
        "notes": t.notes,
        "images": t.images or [],
        "done_criteria": "",
        "estimated_minutes": 0,
        "created_at": t.created_at.isoformat() if t.created_at else "",
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "checked_in_at": t.completed_at.isoformat() if t.completed_at else None,
    }


# ── 上传安全工具 ──

# Magic byte 签名表
_MAGIC_BYTES: dict = {
    ".png":  (b"\x89PNG\r\n\x1a\n", 8),
    ".jpg":  (b"\xff\xd8\xff", 3),
    ".jpeg": (b"\xff\xd8\xff", 3),
    ".webp": (b"RIFF", 4),
    ".bmp":  (b"BM", 2),
    ".gif":  (b"\x47\x49\x46\x38", 6),
    ".csv":  (None, 0),
    ".tsv":  (None, 0),
    ".txt":  (None, 0),
    ".md":   (None, 0),
}


def _validate_magic_bytes(content: bytes, ext: str) -> bool:
    """校验文件内容头部 magic byte 是否与扩展名匹配。"""
    sig_info = _MAGIC_BYTES.get(ext)
    if sig_info is None:
        return True
    expected, sig_len = sig_info
    if expected is None:
        return True
    if len(content) < sig_len:
        return False
    actual = content[:sig_len]
    if ext == ".webp":
        return actual == b"RIFF" and content[8:12] == b"WEBP"
    return actual == expected


def _generate_safe_filename(original_name: str, content: bytes) -> str:
    """生成安全的文件名：uuid + 校验过的扩展名。"""
    ext = Path(original_name).suffix.lower() if original_name else ""

    allowed_exts = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp",
        ".txt", ".md", ".csv",
    }
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型: {original_name}，支持: {', '.join(sorted(allowed_exts))}",
        )

    if not _validate_magic_bytes(content, ext):
        raise HTTPException(
            status_code=422,
            detail=f"文件内容与扩展名 {ext} 不匹配（magic byte 校验失败），疑似扩展名伪装",
        )

    return f"{uuid.uuid4().hex}{ext}"


def _safe_write_file(content: bytes, filename: str) -> Path:
    """安全写入文件到 UPLOAD_DIR，确保路径不逃逸。"""
    target = (UPLOAD_DIR / filename).resolve()
    if not str(target).startswith(str(UPLOAD_DIR)):
        raise HTTPException(
            status_code=422,
            detail="文件路径异常，疑似路径遍历攻击",
        )
    target.write_bytes(content)
    return target


class TaskResponse(BaseModel):
    """任务统一响应格式。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class TaskCheckinRequest(BaseModel):
    """打卡请求体。"""

    task_id: str = Field(..., description="任务ID")
    notes: Optional[str] = Field(None, description="打卡文字备注")
    images: Optional[list[str]] = Field(
        None, description="图片URL列表（可选，可先用/upload上传拿到URL）"
    )


@router.get("/task/detail", response_model=TaskResponse)
async def get_task_detail(
    task_id: str = Query(..., description="任务ID（对应 TodoRecord.id）"),
    user: dict = Depends(get_current_user),
) -> TaskResponse:
    """[V1.0] 获取任务详情 + 执行日志（从数据库 TodoRecord 读取）。"""
    if not task_id:
        raise HTTPException(status_code=422, detail="缺少 task_id 参数")

    try:
        async with AsyncSessionLocal() as session:
            todo = (
                await session.execute(
                    select(TodoRecord).filter_by(id=task_id, user_id=user["user_id"])
                )
            ).scalar_one_or_none()

            if not todo:
                raise HTTPException(status_code=404, detail="任务不存在")

            task_dict = _todo_to_dict(todo)
            execution_logs = [
                {
                    "log_id": uuid.uuid4().hex,
                    "task_id": task_id,
                    "action": "created",
                    "notes": "系统生成任务",
                    "images": todo.images or [],
                    "created_at": todo.created_at.isoformat() if todo.created_at else "",
                }
            ]

            logger.info("任务详情获取成功: task_id=%s", task_id)
            return TaskResponse(data={"task": task_dict, "execution_logs": execution_logs})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("任务详情获取失败: %s", e)
        raise HTTPException(status_code=500, detail=f"任务详情获取失败: {e}") from e


@router.post("/task/checkin", response_model=TaskResponse)
async def task_checkin(
    req: TaskCheckinRequest,
    user: dict = Depends(get_current_user),
) -> TaskResponse:
    """[V1.0] 任务打卡（更新 TodoRecord 状态为 done）。"""
    if not req.task_id:
        raise HTTPException(status_code=422, detail="缺少 task_id 参数")

    try:
        async with AsyncSessionLocal() as session:
            todo = (
                await session.execute(
                    select(TodoRecord).filter_by(id=req.task_id, user_id=user["user_id"])
                )
            ).scalar_one_or_none()

            if not todo:
                raise HTTPException(status_code=404, detail="任务不存在")

            now = datetime.now(timezone.utc)
            todo.status = "done"
            todo.completed_at = now
            if req.notes:
                todo.notes = req.notes
            if req.images:
                todo.images = req.images

            await session.commit()
            await session.refresh(todo)

            task_dict = _todo_to_dict(todo)
            log_id = uuid.uuid4().hex

            logger.info(
                "任务打卡成功: task_id=%s notes_len=%d images=%d",
                req.task_id,
                len(req.notes or ""),
                len(req.images or []),
            )

            return TaskResponse(
                data={
                    "task": task_dict,
                    "execution_logs": [
                        {
                            "log_id": log_id,
                            "task_id": req.task_id,
                            "action": "checkin",
                            "notes": req.notes or "完成打卡",
                            "images": req.images or [],
                            "created_at": now.isoformat(),
                        }
                    ],
                    "checkin_id": log_id,
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("任务打卡失败: %s", e)
        raise HTTPException(status_code=500, detail=f"任务打卡失败: {e}") from e


@router.post("/task/upload", response_model=TaskResponse)
async def task_upload(
    task_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
) -> TaskResponse:
    """[V1.0] 上传任务执行记录（multipart）。

    支持：
      - 图片文件（PNG/JPG/GIF/WEBP）
      - 文本文件（TXT/MD/CSV）
      - 纯文字备注（不传文件也可以）

    安全加固：
      - uuid 文件名，拒绝原始文件名
      - magic byte 校验，防止扩展名伪装
      - UPLOAD_DIR 绝对路径，防止目录穿透
    """
    try:
        upload_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        result: dict = {
            "upload_id": upload_id,
            "task_id": task_id,
            "saved_notes": notes or "",
            "created_at": now,
        }

        if file:
            if not file.filename:
                raise HTTPException(status_code=422, detail="缺少文件名")

            content = await file.read()
            size_mb = len(content) / (1024 * 1024)
            if size_mb > app_config.max_upload_size_mb:
                raise HTTPException(
                    status_code=413,
                    detail=(f"文件超过 {app_config.max_upload_size_mb}MB 限制"),
                )

            # 安全文件名生成 + magic byte 校验 + 路径遍历防护
            safe_filename = _generate_safe_filename(file.filename, content)
            target = _safe_write_file(content, safe_filename)

            result["file_path"] = str(target)
            result["file_url"] = f"/uploads/task_uploads/{safe_filename}"
            result["file_name"] = file.filename
            result["file_size_bytes"] = len(content)

        logger.info(
            "任务上传成功: upload_id=%s task_id=%s has_file=%s",
            upload_id,
            task_id,
            "file_path" in result,
        )

        return TaskResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("任务上传失败: %s", e)
        raise HTTPException(status_code=500, detail=f"上传失败: {e}") from e
