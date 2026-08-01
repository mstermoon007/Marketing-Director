"""认证模块接口（微信小程序登录Mock实现）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import base64
import json
import logging
import random
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求（微信小程序code）。

    Parameters
    ----------
    code : str
        微信小程序登录code，由 wx.login() 返回。
    """

    code: str = Field(..., description="微信小程序登录code")


class AuthResponse(BaseModel):
    """认证统一响应格式。

    Parameters
    ----------
    code : int
        响应状态码，0表示成功。
    message : str
        响应消息。
    data : dict
        响应数据载荷。
    """

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


def _generate_mock_jwt(user_id: str) -> str:
    """生成 Mock JWT 格式 token。

    生产环境应使用真实 jwt.encode。
    格式：header.payload.signature（Base64 模拟）。

    Parameters
    ----------
    user_id : str
        用户唯一标识（UUID hex格式）。

    Returns
    -------
    str
        Mock JWT 格式字符串，30天有效。
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "iat": 1700000000,
        "exp": 1700000000 + 86400 * 30,
    }
    h = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    s = base64.urlsafe_b64encode(b"mock_signature").rstrip(b"=").decode()
    return f"{h}.{p}.{s}"


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest) -> AuthResponse:
    """微信小程序登录（Mock实现）。

    接收 wx.login() 返回的 code，生成：
      - token: Mock JWT 格式（30天有效）
      - user_id: UUID 格式（hex）
      - is_new_user: 标记是否新用户（Mock随机）

    Parameters
    ----------
    req : LoginRequest
        登录请求体，包含微信小程序code。

    Returns
    -------
    AuthResponse
        认证响应，data 包含 token、user_id、is_new_user。

    Raises
    ------
    HTTPException
        当 code 为空时返回 422 错误。

    Examples
    --------
    >>> request = LoginRequest(code="wx_login_code_123")
    >>> response = await login(request)
    >>> "token" in response.data
    True
    """
    if not req.code:
        raise HTTPException(status_code=422, detail="缺少 code 参数")

    user_id = uuid.uuid4().hex
    token = _generate_mock_jwt(user_id)
    is_new_user = random.random() < 0.3

    logger.info("登录成功: user_id=%s is_new_user=%s", user_id, is_new_user)

    return AuthResponse(
        data={
            "token": token,
            "user_id": user_id,
            "is_new_user": is_new_user,
        }
    )
