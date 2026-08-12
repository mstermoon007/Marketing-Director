"""FastAPI 应用入口（初始化数据库/注册路由/CORS配置）。

本模块属于 AI营销战略执行智能体（V1.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.agent import router as agent_router
from backend.api.auth import router as auth_router
from backend.api.business import router as business_router
from backend.api.dashboard import router as dashboard_router
from backend.api.diagnosis import router as diagnosis_router
from backend.api.execution import router as execution_router
from backend.api.loops import router as loops_router
from backend.api.plan import router as plan_router
from backend.api.review import router as review_router
from backend.api.roadmap import router as roadmap_router
from backend.api.task import router as task_router
from backend.config.settings import PROJECT_ROOT, app_config
from backend.db.models import init_db


logging.basicConfig(
    level=logging.DEBUG if app_config.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

logger.info("初始化数据库...")
init_db()

app = FastAPI(
    title=app_config.app_name,
    version=app_config.app_version,
    description="用AI帮小企业把营销战略翻译成每天的执行动作",
)

# CORS 白名单：微信小程序请求不经过浏览器 CORS，此处仅保护 Web 端调试访问。
# 生产环境通过 CORS_ALLOWED_ORIGINS 环境变量配置精确域名。
_cors_origins = (
    [o.strip() for o in app_config.cors_allowed_origins.split(",") if o.strip()]
    if app_config.cors_allowed_origins
    else [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.get("/")
async def root() -> dict:
    """根路径：返回应用名称与版本。

    Returns
    -------
    dict
        包含 name 与 version 的字典。

    Examples
    --------
    >>> resp = await root()
    >>> "name" in resp and "version" in resp
    True
    """
    return {
        "name": app_config.app_name,
        "version": app_config.app_version,
    }


@app.get("/health")
async def health_check() -> dict:
    """健康检查接口。

    Returns
    -------
    dict
        固定返回 ``{"status": "ok"}``。
    """
    return {"status": "ok"}


app.include_router(business_router, prefix="/api", tags=["企业信息"])
app.include_router(agent_router, prefix="/api", tags=["Agent 对话"])
app.include_router(diagnosis_router, prefix="/api", tags=["诊断"])
app.include_router(execution_router, prefix="/api", tags=["执行计划"])
app.include_router(loops_router, prefix="/api", tags=["闭环业务"])
app.include_router(review_router, prefix="/api", tags=["复盘"])
app.include_router(auth_router, prefix="/api", tags=["认证"])
app.include_router(roadmap_router, prefix="/api", tags=["路线图"])
app.include_router(plan_router, prefix="/api", tags=["周计划"])
app.include_router(task_router, prefix="/api", tags=["任务"])
app.include_router(dashboard_router, prefix="/api", tags=["工作台"])

# 静态文件挂载：仅暴露上传目录（data/uploads），绝不挂载 data/ 根目录，
# 否则会连带暴露 SQLite 数据库（app.db）等敏感文件。
_UPLOAD_DIR = (PROJECT_ROOT / "data" / "uploads").resolve()
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOAD_DIR)), name="uploads")


if __name__ == "__main__":
    import os

    import uvicorn

    # CloudRun 容器模式会注入 PORT 环境变量；本地/默认回退 8000
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
    )
