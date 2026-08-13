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

import asyncio
import contextlib
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agent_core import get_controller
from backend.agent_core.config import agent_core_config
from backend.agent_core.state import INTENT_LABELS
from backend.api.auth import get_current_user, verify_token
from backend.utils.security import assert_safe_file_list


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
    # 会话按所有者命名空间化，防止用户 A 用客户端 session_id 读取用户 B 的对话历史
    session_id = f"{user_id}:{req.session_id or 'default'}"

    controller = get_controller()
    result = await controller.chat(
        session_id=session_id,
        user_id=user_id,
        message=req.message,
        business_id=req.business_id or None,
        files=assert_safe_file_list(req.files) or None,
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
    sid = f"{user['user_id']}:{session_id or 'default'}"
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
    # 会话按所有者命名空间化，防止用户 A 用客户端 session_id 读取用户 B 的对话历史
    session_id = f"{user_id}:{req.session_id or 'default'}"
    controller = get_controller()

    # SSE 心跳间隔：微信小程序对分块请求的 timeout 按「相邻分块空闲间隔」计时，
    # Agent 在 runner 执行（LLM/RAG/工具编排）期间不会产出任何 SSE 事件，连接会长时间静默，
    # 极易触发 WAServiceMainContext 的 Error: timeout（dev 10s / prod 30s）。
    # 每隔几秒下发一条 SSE 注释行（以 ":" 开头，前端解析器会忽略），保活连接。
    SSE_HEARTBEAT_INTERVAL = 8  # 秒，必须小于任一环境的 timeout 下限

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        async def _producer() -> None:
            # 在独立 task 中跑 controller.chat_stream，事件经队列转发，
            # 既保留顺序，又允许主生成器在无事件时插入心跳。
            try:
                async for evt in controller.chat_stream(
                    session_id=session_id,
                    user_id=user_id,
                    message=req.message,
                    business_id=req.business_id or None,
                    files=assert_safe_file_list(req.files) or None,
                ):
                    await queue.put(("event", evt))
            except Exception as e:  # 统一为 error 事件下推
                await queue.put(("error", str(e)))
            finally:
                await queue.put(("stop", None))

        prod_task = asyncio.ensure_future(_producer())
        try:
            while True:
                try:
                    kind, payload = await asyncio.wait_for(
                        queue.get(), timeout=SSE_HEARTBEAT_INTERVAL
                    )
                except asyncio.TimeoutError:
                    # 空闲超时：下发心跳注释行，避免微信侧连接被掐断
                    yield ": heartbeat\n\n"
                    continue

                if kind == "stop":
                    break
                if kind == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': payload}, ensure_ascii=False)}\n\n"
                    break
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            prod_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await prod_task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _extract_ws_token(websocket: WebSocket) -> str | None:
    """从 WebSocket 连接中提取 JWT。

    优先取 ``Authorization: Bearer <token>`` 请求头（与 HTTP 接口一致）；
    小程序 ``wx.connectSocket`` 对自定义请求头支持有限，故同时兼容 ``?token=`` 查询参数。
    """
    auth = websocket.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    token = websocket.query_params.get("token")
    return token if token else None


@router.websocket("/agent/chat/ws")
async def agent_chat_ws(websocket: WebSocket) -> None:
    """WebSocket 流式对话。

    与 ``POST /api/agent/chat/stream`` (SSE) 等价，但使用 WebSocket 双向通道：

    - 连接后服务端先校验 JWT（Authorization 头或 ``?token=`` 查询参数），失败则关闭连接。
    - 客户端首帧发送 JSON：``{"message", "session_id", "business_id", "files"}``。
    - 服务端逐条回推 Agent 事件 JSON（与 SSE 的 ``data`` 载荷结构一致），
      事件类型含 intent / thinking / tool / done / error。
    - 空闲时下发 ``{"type": "ping"}`` 心跳保活，避免连接被中间代理掐断。

    鉴权失败、首帧格式错误、客户端断开均会优雅关闭连接，不抛未处理异常。
    """
    await websocket.accept()

    # ── 鉴权 ──
    try:
        token = _extract_ws_token(websocket)
        jwt_payload = verify_token(token) if token else None
    except Exception:
        jwt_payload = None
    if not jwt_payload or "user_id" not in jwt_payload:
        await websocket.send_json({"type": "error", "message": "未登录或 token 失效"})
        await websocket.close(code=1008)
        return

    user_id = jwt_payload["user_id"]

    # ── 读取首帧请求 ──
    try:
        raw = await websocket.receive_text()
    except WebSocketDisconnect:
        return
    try:
        req = json.loads(raw)
        if not isinstance(req, dict):
            raise ValueError("首帧必须为 JSON 对象")
    except (json.JSONDecodeError, ValueError):
        await websocket.send_json({"type": "error", "message": "首帧格式错误（需为 JSON 对象）"})
        await websocket.close(code=1008)
        return

    message = str(req.get("message", ""))
    session_id = f"{user_id}:{req.get('session_id', '') or 'default'}"
    business_id = req.get("business_id") or None
    files = assert_safe_file_list(req.get("files") or []) or None

    controller = get_controller()

    # 心跳间隔：与 SSE 一致，必须小于连接保活阈值
    WS_HEARTBEAT_INTERVAL = 8  # 秒

    queue: asyncio.Queue = asyncio.Queue()

    async def _producer() -> None:
        """在独立 task 中跑 controller.chat_stream，事件经队列转发，
        既保留顺序，又允许主循环在无事件时插入心跳。"""
        try:
            async for evt in controller.chat_stream(
                session_id=session_id,
                user_id=user_id,
                message=message,
                business_id=business_id,
                files=files,
            ):
                await queue.put(("event", evt))
        except Exception as e:  # 统一为 error 事件下推
            await queue.put(("error", str(e)))
        finally:
            await queue.put(("stop", None))

    prod_task = asyncio.ensure_future(_producer())
    try:
        while True:
            try:
                kind, item = await asyncio.wait_for(queue.get(), timeout=WS_HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                # 空闲超时：下发心跳，避免连接被掐断
                await websocket.send_json({"type": "ping"})
                continue

            if kind == "stop":
                break
            if kind == "error":
                await websocket.send_json({"type": "error", "message": item})
                break
            await websocket.send_json(item)
    except WebSocketDisconnect:
        # 客户端主动断开：由 finally 取消 producer 并收尾
        pass
    finally:
        prod_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await prod_task
        with contextlib.suppress(RuntimeError):
            # 连接已关闭时忽略
            await websocket.close()
