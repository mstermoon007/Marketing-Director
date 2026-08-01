"""FastAPI 应用入口（初始化数据库/注册路由/CORS配置）。

本模块属于 AI营销战略执行智能体（V3.0.0）后端服务。

Copyright 2026 AI Marketing Team
MIT License
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.business import router as business_router
from src.api.dashboard import router as dashboard_router
from src.api.diagnosis import router as diagnosis_router
from src.api.execution import router as execution_router
from src.api.plan import router as plan_router
from src.api.review import router as review_router
from src.api.roadmap import router as roadmap_router
from src.api.task import router as task_router
from src.config.settings import app_config
from src.db.models import init_db


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(diagnosis_router, prefix="/api", tags=["诊断"])
app.include_router(execution_router, prefix="/api", tags=["执行计划"])
app.include_router(review_router, prefix="/api", tags=["复盘"])
app.include_router(auth_router, prefix="/api", tags=["认证"])
app.include_router(roadmap_router, prefix="/api", tags=["路线图"])
app.include_router(plan_router, prefix="/api", tags=["周计划"])
app.include_router(task_router, prefix="/api", tags=["任务"])
app.include_router(dashboard_router, prefix="/api", tags=["工作台"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_config.debug,
    )
