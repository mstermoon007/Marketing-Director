"""
记忆库（Memory Store）
================================

基于 ChromaDB 的持久化记忆，覆盖三类业务上下文：

1. 用户画像（user_profile）：每个用户一份最新画像摘要，随对话累积更新。
2. 对话历史（conversation_history）：按 session 存储多轮消息，支持上下文保持与追问。
3. 指标变化（metric_snapshots）：按 business 记录关键指标的目标/实际快照，支持趋势回溯。

所有写入走共享的 EmbeddingFunction（离线哈希或 OpenAI），保证可检索。
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from backend.agent_core._chroma import get_chroma_client, get_embedding_fn


logger = logging.getLogger(__name__)


class MemoryStore:
    """记忆库封装。"""

    def __init__(self):
        self._client = get_chroma_client()
        self._ef = get_embedding_fn()
        self._profile = self._client.get_or_create_collection(
            name="user_profile", embedding_function=self._ef
        )
        self._history = self._client.get_or_create_collection(
            name="conversation_history", embedding_function=self._ef
        )
        self._metrics = self._client.get_or_create_collection(
            name="metric_snapshots", embedding_function=self._ef
        )

    # ── 用户画像 ──
    def save_profile(self, user_id: str, profile_text: str, metadata: Optional[dict] = None) -> None:
        """保存/覆盖用户画像（按 user_id 幂等 upsert）。"""
        meta = {"user_id": user_id}
        if metadata:
            meta.update({k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))})
        self._profile.upsert(
            ids=[user_id],
            documents=[profile_text],
            metadatas=[meta],
        )
        logger.debug("记忆库：保存用户画像 user=%s", user_id)

    def get_profile(self, user_id: str) -> Optional[dict]:
        """读取用户画像，返回 {text, metadata} 或 None。"""
        res = self._profile.get(ids=[user_id], include=["documents", "metadatas"])
        if res and res["ids"]:
            return {
                "text": (res["documents"] or [""])[0],
                "metadata": (res["metadatas"] or [{}])[0],
            }
        return None

    # ── 对话历史 ──
    def append_history(self, session_id: str, user_id: str, role: str, text: str) -> None:
        """追加一条对话消息。role ∈ {user, assistant, system}。"""
        doc_id = f"{session_id}:{uuid.uuid4().hex[:12]}"
        self._history.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[{
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "ts": float(time.time()),
            }],
        )

    def get_history(self, session_id: str, limit: int = 12) -> list[dict]:
        """读取某会话最近 limit 条消息，按时间升序返回 {role, text, ts}。"""
        res = self._history.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"],
        )
        items = []
        if res and res["ids"]:
            for doc, meta in zip(res["documents"], res["metadatas"]):
                items.append({
                    "role": meta.get("role", "user"),
                    "text": doc,
                    "ts": meta.get("ts", 0.0),
                })
            items.sort(key=lambda x: x["ts"])
        return items[-limit:]

    def get_user_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """读取某用户跨会话最近 limit 条消息（用于画像与上下文）。"""
        res = self._history.get(
            where={"user_id": user_id},
            include=["documents", "metadatas"],
        )
        items = []
        if res and res["ids"]:
            for doc, meta in zip(res["documents"], res["metadatas"]):
                items.append({
                    "role": meta.get("role", "user"),
                    "text": doc,
                    "ts": meta.get("ts", 0.0),
                })
            items.sort(key=lambda x: x["ts"])
        return items[-limit:]

    # ── 指标变化 ──
    def save_metric_snapshot(
        self,
        business_id: str,
        metric_name: str,
        target: float,
        actual: float,
        ts: Optional[float] = None,
    ) -> None:
        """保存一条指标快照（目标 vs 实际）。"""
        ts = ts or time.time()
        doc_id = f"{business_id}:{metric_name}:{uuid.uuid4().hex[:8]}"
        self._metrics.add(
            ids=[doc_id],
            documents=[f"{metric_name} 目标 {target} 实际 {actual}"],
            metadatas=[{
                "business_id": business_id,
                "metric": metric_name,
                "target": float(target),
                "actual": float(actual),
                "ts": float(ts),
            }],
        )

    def get_metric_trend(
        self, business_id: str, metric_name: Optional[str] = None, limit: int = 10
    ) -> list[dict]:
        """读取某业务指标变化趋势，按时间降序返回。"""
        where = {"business_id": business_id}
        if metric_name:
            where = {"$and": [
                {"business_id": business_id},
                {"metric": metric_name},
            ]}
        res = self._metrics.get(where=where, include=["metadatas"])
        items = []
        if res and res["ids"]:
            for meta in res["metadatas"]:
                items.append({
                    "metric": meta.get("metric"),
                    "target": meta.get("target"),
                    "actual": meta.get("actual"),
                    "ts": meta.get("ts", 0.0),
                })
            items.sort(key=lambda x: x["ts"], reverse=True)
        return items[:limit]
