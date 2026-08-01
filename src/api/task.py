"""任务模块接口（任务详情/打卡/上传执行记录）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from src.config.settings import PROJECT_ROOT, app_config


logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = PROJECT_ROOT / "data" / "task_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TaskResponse(BaseModel):
    """任务统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        任务相关数据载荷。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


class TaskCheckinRequest(BaseModel):
    """打卡请求体。

    Parameters
    ----------
    task_id : str
        任务ID（必填）。
    notes : Optional[str]
        打卡文字备注（可选）。
    images : Optional[List[str]]
        图片URL列表（可选，可先用/upload上传拿到URL）。
    """

    task_id: str = Field(..., description="任务ID")
    notes: Optional[str] = Field(None, description="打卡文字备注")
    images: Optional[List[str]] = Field(
        None, description="图片URL列表（可选，可先用/upload上传拿到URL）"
    )


def _get_mock_task_detail(task_id: str) -> dict:
    """Mock 生成任务详情。

    真实场景下应从 ExecutionPlanRecord.days[*].tasks[*] 中按索引查找。
    这里先返回通用模板 + task_id 标识。

    Parameters
    ----------
    task_id : str
        任务唯一标识ID。

    Returns
    -------
    dict
        任务详情字典，包含 task 与 execution_logs 两部分。
    """
    task = {
        "task_id": task_id,
        "title": "梳理目标客户画像",
        "time_slot": "09:00-09:30",
        "how_to": "列出至少3类核心客户的特征、痛点、常用平台",
        "checklist": [
            "写出客户年龄段",
            "写出客户核心需求",
            "列出常用APP/平台",
        ],
        "done_criteria": "形成1页纸客户画像文档",
        "estimated_minutes": 30,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    execution_logs = [
        {
            "log_id": uuid.uuid4().hex,
            "task_id": task_id,
            "action": "created",
            "notes": "系统生成任务",
            "images": [],
            "created_at": datetime.utcnow().isoformat(),
        },
    ]

    return {
        "task": task,
        "execution_logs": execution_logs,
    }


@router.get("/task/detail", response_model=TaskResponse)
async def get_task_detail(
    task_id: str = Query(..., description="任务ID"),
) -> TaskResponse:
    """[V3.0] 获取任务详情 + 执行日志。

    返回结构：
      {
        task: {task_id, title, time_slot, how_to, checklist,
               done_criteria, estimated_minutes, status},
        execution_logs: [ {log_id, action, notes, images[], created_at}, ... ]
      }

    Parameters
    ----------
    task_id : str
        任务ID（必填查询参数）。

    Returns
    -------
    TaskResponse
        任务详情与执行日志响应。

    Raises
    ------
    HTTPException
        - 422: 缺少 task_id 参数。
        - 500: 内部处理异常。
    """
    if not task_id:
        raise HTTPException(status_code=422, detail="缺少 task_id 参数")

    try:
        detail = _get_mock_task_detail(task_id)

        logger.info("任务详情获取成功: task_id=%s", task_id)
        return TaskResponse(data=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("任务详情获取失败: %s", e)
        raise HTTPException(status_code=500, detail=f"任务详情获取失败: {e}") from e


@router.post("/task/checkin", response_model=TaskResponse)
async def task_checkin(req: TaskCheckinRequest) -> TaskResponse:
    """[V3.0] 任务打卡。

    接收：task_id, notes?, images?[]
    行为：更新任务状态为 done，追加一条 execution_log
    返回：更新后的 task + execution_logs

    Parameters
    ----------
    req : TaskCheckinRequest
        打卡请求体，包含 task_id、notes、images。

    Returns
    -------
    TaskResponse
        data 包含更新后的 task、execution_logs、checkin_id。

    Raises
    ------
    HTTPException
        - 422: 缺少 task_id 参数。
        - 500: 内部处理异常。
    """
    if not req.task_id:
        raise HTTPException(status_code=422, detail="缺少 task_id 参数")

    try:
        log_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()

        new_log = {
            "log_id": log_id,
            "task_id": req.task_id,
            "action": "checkin",
            "notes": req.notes or "完成打卡",
            "images": req.images or [],
            "created_at": now,
        }

        task = {
            "task_id": req.task_id,
            "title": "梳理目标客户画像",
            "time_slot": "09:00-09:30",
            "how_to": "列出至少3类核心客户的特征、痛点、常用平台",
            "checklist": [
                "写出客户年龄段",
                "写出客户核心需求",
                "列出常用APP/平台",
            ],
            "done_criteria": "形成1页纸客户画像文档",
            "estimated_minutes": 30,
            "status": "done",
            "checked_in_at": now,
            "checkin_notes": req.notes or "",
            "checkin_images": req.images or [],
            "created_at": now,
        }

        logger.info(
            "任务打卡成功: task_id=%s notes_len=%d images=%d",
            req.task_id,
            len(req.notes or ""),
            len(req.images or []),
        )

        return TaskResponse(
            data={
                "task": task,
                "execution_logs": [new_log],
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
    """[V3.0] 上传任务执行记录（multipart）。

    支持：
      - 图片文件（PNG/JPG/GIF/WEBP）
      - 文本文件（TXT/MD/CSV）
      - 纯文字备注（不传文件也可以）

    返回：
      {
        upload_id,
        file_path?,
        file_url?,
        saved_notes,
        task_id?,
        created_at,
      }

    Parameters
    ----------
    task_id : Optional[str]
        关联任务ID（可选表单字段）。
    notes : Optional[str]
        文字备注（可选表单字段）。
    file : Optional[UploadFile]
        上传文件（可选，支持图片与文本）。

    Returns
    -------
    TaskResponse
        data 包含 upload_id、file_path、file_url、saved_notes 等。

    Raises
    ------
    HTTPException
        - 422: 缺少文件名或不支持的文件类型。
        - 413: 文件超过大小限制。
        - 500: 内部处理异常。
    """
    try:
        upload_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        result: dict = {
            "upload_id": upload_id,
            "task_id": task_id,
            "saved_notes": notes or "",
            "created_at": now,
        }

        if file:
            if not file.filename:
                raise HTTPException(status_code=422, detail="缺少文件名")

            allowed_ext = {
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".txt",
                ".md",
                ".csv",
            }
            lower_name = file.filename.lower()
            is_allowed = any(lower_name.endswith(ext) for ext in allowed_ext)
            if not is_allowed:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"不支持的文件类型: {file.filename}，" f"支持: {', '.join(allowed_ext)}"
                    ),
                )

            content = await file.read()
            size_mb = len(content) / (1024 * 1024)
            if size_mb > app_config.max_upload_size_mb:
                raise HTTPException(
                    status_code=413,
                    detail=(f"文件超过 {app_config.max_upload_size_mb}MB 限制"),
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{file.filename}"
            target = UPLOAD_DIR / safe_filename
            target.write_bytes(content)

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
