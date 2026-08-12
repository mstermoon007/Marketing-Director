"""
营销知识库（Knowledge Base）— RAG 检索
================================

将 ``data/marketing_knowledge_cards.jsonl`` 中的 500+ 营销方法卡片向量化进 ChromaDB，
提供语义/词面混合检索（RAG），为各子 Agent 提供「有案例支撑」的方法论，避免空洞建议。

集合：``marketing_knowledge``
- document：方法名 + 原理 + 步骤 + 正文（用于检索匹配）
- metadata：category / industry / channel / kpi / name（category、industry 可作为过滤条件）
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.agent_core._chroma import get_chroma_client, get_embedding_fn
from backend.agent_core.config import agent_core_config


logger = logging.getLogger(__name__)


class KnowledgeBase:
    """营销方法卡片知识库（RAG）。"""

    def __init__(self):
        self._client = get_chroma_client()
        self._ef = get_embedding_fn()
        self._col = self._client.get_or_create_collection(
            name="marketing_knowledge", embedding_function=self._ef
        )
        self._file = Path(agent_core_config.knowledge_file)

    # ── 入库 ──
    def ingest(self, force: bool = False) -> int:
        """读取 JSONL 并写入向量库。force=True 时清空重建；否则仅补充缺失。"""
        if not self._file.exists():
            logger.warning("知识库语料文件不存在：%s", self._file)
            return 0

        if force:
            try:
                self._client.delete_collection("marketing_knowledge")
            except Exception:
                pass
            self._col = self._client.get_or_create_collection(
                name="marketing_knowledge", embedding_function=self._ef
            )

        existing = set(self._col.get(include=[])["ids"]) if not force else set()

        cards = []
        with self._file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                cards.append(json.loads(line))

        ids, docs, metas = [], [], []
        for c in cards:
            cid = c.get("id")
            if cid in existing:
                continue
            name = c.get("name", "")
            principle = c.get("principle", "")
            steps = c.get("steps", [])
            content = c.get("content", "")
            steps_text = "\n".join(f"- {s}" for s in steps) if isinstance(steps, list) else str(steps)
            document = f"{name}\n原理：{principle}\n步骤：\n{steps_text}\n内容：{content}"
            channels = c.get("channels", [])
            channel = channels[0] if isinstance(channels, list) and channels else str(channels)
            steps_text = "\n".join(f"- {s}" for s in steps) if isinstance(steps, list) else str(steps)
            metas.append({
                "name": name,
                "category": c.get("category", "通用"),
                "industry": c.get("industry", "通用"),
                "channel": channel,
                "kpi": c.get("kpi", ""),
                "principle": principle,
                "steps": steps_text,
                "content": content,
            })
            docs.append(document)
            ids.append(cid)

        if ids:
            self._col.upsert(ids=ids, documents=docs, metadatas=metas)
            logger.info("知识库入库：新增 %d 张卡片（累计 %d）", len(ids), self._col.count())
        else:
            logger.info("知识库无需补充，当前共 %d 张", self._col.count())
        return len(ids)

    def ensure_loaded(self) -> None:
        """首次检索前确保知识库非空（为空则自动入库）。"""
        if self._col.count() == 0:
            self.ingest(force=False)

    # ── 检索 ──
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> list[dict]:
        """RAG 检索，返回最相关的方法卡片列表。

        Parameters
        ----------
        query : str
            自然语言查询（如「餐饮 怎么用短视频获客」）。
        top_k : int
            返回条数，默认取 agent_core_config.knowledge_top_k。
        category : str
            按类别过滤（内容运营/获客引流/转化成交/...）。
        industry : str
            按行业过滤（餐饮/家装/...）。

        Returns
        -------
        list[dict]，每项含 id/name/category/industry/channel/kpi/content/score，
        score 为 1-distance（越大越相关）。
        """
        self.ensure_loaded()
        top_k = top_k or agent_core_config.knowledge_top_k

        where = {}
        if category:
            where["category"] = category
        if industry:
            where["industry"] = industry
        if len(where) > 1:
            where = {"$and": [{k: v} for k, v in where.items()]}

        try:
            res = self._col.query(
                query_texts=[query],
                n_results=top_k,
                where=where or None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("知识库检索失败：%s", e)
            return []

        out = []
        if not res or not res["ids"]:
            return out
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            out.append({
                "id": cid,
                "name": meta.get("name", ""),
                "category": meta.get("category", ""),
                "industry": meta.get("industry", ""),
                "channel": meta.get("channel", ""),
                "kpi": meta.get("kpi", ""),
                "principle": meta.get("principle", ""),
                "steps": meta.get("steps", ""),
                "content": meta.get("content", doc),
                "score": round(1.0 - float(dist), 4) if dist is not None else None,
            })
        return out

    def count(self) -> int:
        return self._col.count()
