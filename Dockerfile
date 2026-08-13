FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # 首启从知识库卡片重建 Chroma 向量库（容器磁盘为临时，chroma_db 不会随镜像携带）
    AGENT_REBUILD_KNOWLEDGE=true \
    # 运行环境：本镜像专用于 CloudRun 生产部署，显式 production，
    # 使后端按 APP_ENV 落到生产库 data/app_prod.db（与开发库 app_dev.db 隔离）。
    # 若云托管控制台注入了同名变量，以其为准；运行时护栏(_guard_prod_env_isolation)
    # 会在 PORT 已设却写回 app_dev.db 时拒绝启动。
    APP_ENV=production \
    # 小程序生产地址：登录成功后由后端下发（api_base_url）。此处为容器默认，
    # 若云托管控制台配置了同名环境变量将被其覆盖。
    PUBLIC_API_BASE_URL=https://marketing-agent-295298-11-1466398119.sh.run.tcloudbase.com/api

WORKDIR /app

# 编译依赖：chromadb / 部分包可能需本地构建
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./backend
COPY data ./data
RUN mkdir -p /app/data/chroma_db

EXPOSE 8000

# CloudRun 容器模式会注入 PORT；本地/默认回退 8000
CMD ["sh", "-c", "uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
