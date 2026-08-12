"""认证模块接口（微信小程序登录 + JWT 签发/校验）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging
import time

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.config.settings import app_config


logger = logging.getLogger(__name__)

router = APIRouter()


# ── JWT 工具 ──

def _get_jwt_secret() -> str:
    """获取 JWT 签名密钥（必须来自环境变量 JWT_SECRET_KEY）。

    生产环境与开发环境均强制要求设置 JWT_SECRET_KEY，禁止任何硬编码/常量回退，
    避免 token 可被任意伪造（原 dev-only 常量密钥属于安全反模式）。
    """
    secret = app_config.jwt_secret_key
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY 未设置。必须通过环境变量 JWT_SECRET_KEY 设置签名密钥！"
        )
    return secret


def create_access_token(user_id: str, openid: str = "") -> str:
    """签发标准 JWT。

    Parameters
    ----------
    user_id : str
        用户唯一标识。
    openid : str
        微信 openid（可选，嵌入 payload 供后续使用）。

    Returns
    -------
    str
        标准 JWT 字符串（header.payload.signature）。
    """
    secret = _get_jwt_secret()
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "openid": openid,
        "iat": now,
        "exp": now + app_config.jwt_expire_days * 86400,
    }
    return jwt.encode(payload, secret, algorithm=app_config.jwt_algorithm)


def verify_token(token: str) -> dict:
    """验证 JWT 并返回 payload。

    Parameters
    ----------
    token : str
        JWT 字符串。

    Returns
    -------
    dict
        解码后的 payload，包含 user_id、openid、iat、exp。

    Raises
    ------
    HTTPException
        token 无效或过期时返回 401。
    """
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[app_config.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token") from None


def get_current_user(request: Request) -> dict:
    """FastAPI 依赖注入：从 Authorization header 提取并验证 JWT。

    使用方式::

        @router.get("/protected")
        async def protected(user: dict = Depends(get_current_user)):
            user_id = user["user_id"]
            ...

    Raises
    ------
    HTTPException
        未提供 token 或 token 无效时返回 401。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证信息，请先登录")
    token = auth_header[7:]  # 去掉 "Bearer " 前缀
    return verify_token(token)


# ── 请求/响应模型 ──

class LoginRequest(BaseModel):
    """登录请求（微信小程序code）。

    Parameters
    ----------
    code : str
        微信小程序登录code，由 wx.login() 返回。
    """

    code: str = Field(..., description="微信小程序登录code")


class AuthResponse(BaseModel):
    """认证统一响应格式。"""

    code: int = Field(0, description="响应状态码，0表示成功")
    message: str = Field("ok", description="响应消息")
    data: dict = Field(default_factory=dict, description="响应数据载荷")


# ── 微信 code2session ──

async def _wechat_code2session(code: str) -> dict:
    """调用微信 jscode2session 接口，用 code 换取 openid + session_key。

    Parameters
    ----------
    code : str
        微信小程序登录 code。

    Returns
    -------
    dict
        包含 openid, session_key, unionid? 的字典。

    Raises
    ------
    HTTPException
        微信接口调用失败或返回错误码。
    """
    appid = app_config.wechat_appid
    secret = app_config.wechat_secret

    if not appid or not secret:
        raise HTTPException(
            status_code=500,
            detail="微信小程序配置缺失（WECHAT_APPID/WECHAT_SECRET），无法验证登录",
        )

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": appid,
        "secret": secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("微信 code2session 请求失败: %s", e)
            raise HTTPException(
                status_code=502,
                detail=f"微信登录服务暂时不可用: {e}",
            ) from e

    if "errcode" in data and data["errcode"] != 0:
        logger.error("微信 code2session 返回错误: %s", data)
        raise HTTPException(
            status_code=401,
            detail=f"微信登录失败: {data.get('errmsg', '未知错误')}",
        )

    return data


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest) -> AuthResponse:
    """微信小程序登录。

    流程：
      1. 接收 wx.login() 返回的 code
      2. 调用微信 jscode2session 获取 openid
      3. 用 openid 生成 user_id
      4. 签发标准 JWT（HS256 + 环境变量密钥）

    Parameters
    ----------
    req : LoginRequest
        登录请求体，包含微信小程序code。

    Returns
    -------
    AuthResponse
        认证响应，data 包含 token（标准JWT）、user_id、openid。

    Raises
    ------
    HTTPException
        - 422: code 为空。
        - 401: 微信 code 校验失败。
        - 502: 微信服务不可用。
    """
    if not req.code:
        raise HTTPException(status_code=422, detail="缺少 code 参数")

    # 调用微信 code2session 获取 openid
    wx_data = await _wechat_code2session(req.code)

    if wx_data is None:
        raise HTTPException(status_code=401, detail="微信登录失败：code 无效")

    openid = wx_data.get("openid", "")

    if not openid:
        raise HTTPException(status_code=401, detail="微信登录失败：未获取到 openid")

    # 用 openid 的 hash 作为 user_id（稳定且不泄露 openid 原文）
    import hashlib
    user_id = hashlib.sha256(openid.encode()).hexdigest()[:32]

    # 签发标准 JWT
    token = create_access_token(user_id, openid)

    logger.info("登录成功: user_id=%s openid_prefix=%s", user_id, openid[:8])

    return AuthResponse(
        data={
            "token": token,
            "user_id": user_id,
            "openid": openid,
            "is_new_user": False,  # 实际项目应查询用户表判断
            # 生产环境配置下发：前端登录成功后持久化，取代原先的本地加密/硬编码方案
            "api_base_url": app_config.public_api_base_url,
        }
    )


@router.get("/auth/verify", response_model=AuthResponse)
async def verify_auth(user: dict = Depends(get_current_user)) -> AuthResponse:
    """验证当前 token 是否有效。

    需要 Authorization: Bearer <token> header。
    有效则返回 user_id，无效则返回 401。
    """
    return AuthResponse(
        data={
            "user_id": user.get("user_id", ""),
            "valid": True,
            # 登录态续期时也一并下发生产地址，保证前端缓存失效后可立即恢复
            "api_base_url": app_config.public_api_base_url,
        }
    )
