"""
Agent 对话接口（后端大脑入口）
================================

暴露多 Agent 协作层的 HTTP 接口：

- ``POST /api/agent/chat`` ：一轮自然语言对话，主控 Agent 自动分类意图并调度子 Agent。
  支持多轮（session_id）、可选 business_id、可选上传文件路径（复盘用）。
- ``GET  /api/agent/history`` ：读取某会话的对话历史（上下文保持）。

所有接口均需 JWT 鉴权（与既有 API 一致）。
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agent_core import get_controller
from backend.agent_core.config import agent_core_config
from backend.agent_core.state import INTENT_LABELS
from backend.api.auth import get_current_user


router = APIRouter()


class AgentChatRequest(BaseModel):
    """Agent 对话请求。"""

    message: str = Field(..., description="用户自然语言输入")
    session_id: str = Field("", description="会话ID；留空则用 用户ID:default")
    business_id: str = Field("", description="可选企业ID；留空时复用会话已绑定企业")
    files: list[str] = Field(default_factory=list, description="上传文件路径列表（复盘用）")


class AgentHistoryResponse(BaseModel):
    """通用响应。"""

    code: int = 0
    message: str = "ok"
    data: dict = Field(default_factory=dict)


@router.post("/agent/chat", response_model=AgentHistoryResponse)
async def agent_chat(req: AgentChatRequest, user: dict = Depends(get_current_user)) -> AgentHistoryResponse:
    """与营销 Agent 对话一轮。"""
    user_id = user["user_id"]
    session_id = req.session_id or f"{user_id}:default"

    controller = get_controller()
    result = await controller.chat(
        session_id=session_id,
        user_id=user_id,
        message=req.message,
        business_id=req.business_id or None,
        files=req.files or None,
    )
    return AgentHistoryResponse(data={
        "response": result["response"],
        "intent": result["intent"],
        "intent_label": INTENT_LABELS.get(result["intent"], ""),
        "business_id": result["business_id"],
        "needs_clarification": result["needs_clarification"],
        "session_id": session_id,
    })


@router.get("/agent/history", response_model=AgentHistoryResponse)
async def agent_history(
    session_id: str = "", user: dict = Depends(get_current_user)
) -> AgentHistoryResponse:
    """读取某会话的对话历史。"""
    sid = session_id or f"{user['user_id']}:default"
    controller = get_controller()
    history = controller.memory.get_history(sid, limit=agent_core_config.history_window)
    return AgentHistoryResponse(data={"session_id": sid, "history": history})


@router.post("/agent/chat/stream")
async def agent_chat_stream(
    req: AgentChatRequest, user: dict = Depends(get_current_user)
) -> StreamingResponse:
    """流式对话（SSE）。

    逐段返回 ``data: {json}\\n\\n`` 事件：intent / thinking / tool / done / error。
    前端用 ``wx.request({enableChunked:true})`` 解析分块，实时渲染 Agent 思考过程。
    """
    user_id = user["user_id"]
    session_id = req.session_id or f"{user_id}:default"
    controller = get_controller()

    async def event_generator():
        try:
            async for evt in controller.chat_stream(
                session_id=session_id,
                user_id=user_id,
                message=req.message,
                business_id=req.business_id or None,
                files=req.files or None,
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
