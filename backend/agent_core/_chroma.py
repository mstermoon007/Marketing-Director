"""
ChromaDB 客户端单例
================================

所有 Agent 组件共用同一个 PersistentClient 与 EmbeddingFunction 实例，
避免多客户端对同一目录的冲突，并关闭匿名遥测。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import chromadb

from backend.agent_core.config import agent_core_config
from backend.agent_core.embeddings import get_embedding_function


logger = logging.getLogger(__name__)

# 关闭 ChromaDB 匿名遥测，避免外网请求
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

_client = None
_embedding_fn = None


def get_chroma_client() -> "chromadb.api.client.Client":
    """返回（惰性创建）共享的 ChromaDB 持久化客户端。"""
    global _client
    if _client is None:
        path = agent_core_config.chroma_persist_dir
        Path(path).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=path)
        logger.info("ChromaDB 客户端已连接：%s", path)
    return _client


def get_embedding_fn():
    """返回（惰性创建）共享的 EmbeddingFunction。"""
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = get_embedding_function(agent_core_config.embedding_provider)
        logger.info(
            "Embedding 函数已加载：provider=%s", agent_core_config.embedding_provider
        )
    return _embedding_fn
