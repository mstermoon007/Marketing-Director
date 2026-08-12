"""
Agent 核心框架配置
================================

从环境变量读取 Agent 层相关配置，带合理默认值，便于本地与容器部署。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from backend.config.settings import PROJECT_ROOT


@dataclass
class AgentCoreConfig:
    """Agent 核心框架配置。"""

    # ChromaDB 持久化目录
    chroma_persist_dir: str = os.getenv(
        "CHROMA_PERSIST_DIR",
        str(PROJECT_ROOT / "data" / "chroma_db"),
    )

    # 营销知识库卡片文件路径（JSONL）
    knowledge_file: str = os.getenv(
        "MARKETING_KNOWLEDGE_FILE",
        str(PROJECT_ROOT / "data" / "marketing_knowledge_cards.jsonl"),
    )

    # 向量化提供方：local（离线） / openai（需 Key）
    embedding_provider: str = os.getenv("AGENT_EMBEDDING_PROVIDER", "local")

    # RAG 检索条数
    knowledge_top_k: int = int(os.getenv("AGENT_KNOWLEDGE_TOP_K", "5"))

    # 会话历史保留条数（多轮上下文窗口）
    history_window: int = int(os.getenv("AGENT_HISTORY_WINDOW", "12"))

    # 是否强制重建知识库（首次启动或卡片更新后建议 True 一次）
    rebuild_knowledge: bool = os.getenv("AGENT_REBUILD_KNOWLEDGE", "false").lower() == "true"

    # 意图分类是否启用 LLM（无 Key 时走规则）
    use_llm_intent: bool = os.getenv("AGENT_USE_LLM_INTENT", "true").lower() == "true"


agent_core_config = AgentCoreConfig()
