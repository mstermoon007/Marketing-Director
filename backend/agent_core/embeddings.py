"""
向量化（Embedding）层
================================

为 ChromaDB 提供可插拔的 EmbeddingFunction（兼容 chromadb 1.5+ 的 "known" 接口）：

- ``LocalHashingEmbedding``：纯本地、零网络依赖的哈希向量（signed hashing + TF 加权 + L2 归一化）。
  维度 384，能在无 API Key、无外网环境下对中文营销语料做可用的语义/词面检索。
- ``OpenAIEmbedding``：当有 ``OPENAI_API_KEY`` 时，使用 ``text-embedding-3-small`` 做高质量语义向量。
- ``get_embedding_function(provider)``：按配置返回对应实现，默认 local。

每个 EmbeddingFunction 都实现 chromadb 1.5 要求的 ``__call__`` / ``embed_documents`` /
``embed_query`` / ``name`` / ``is_legacy`` / ``get_config`` / ``build_from_config`` 方法，
以 ``known``（非 legacy）方式注册，避免弃用警告。
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from typing import List

from chromadb.api.collection_configuration import register_embedding_function

from backend.config.settings import llm_config


logger = logging.getLogger(__name__)

# 本地向量维度
LOCAL_EMBED_DIM = 384

# CJK 字符范围（用于切分中文字符与二元组）
_CJK = r"[\u4e00-\u9fff]"
_CJK_RE = re.compile(_CJK)
# 英文/数字词
_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """把文本切成特征单元：英文数字词 + 单个汉字 + 汉字二元组。

    中文没有空格分词，靠字 + 二元组兼顾词面与局部语序，对营销领域检索足够。
    """
    low = (text or "").lower()
    features: List[str] = []
    features.extend(_WORD_RE.findall(low))
    cjk = "".join(_CJK_RE.findall(low))
    features.extend(cjk)  # 单字
    for i in range(len(cjk) - 1):  # 二元组
        features.append(cjk[i:i + 2])
    return features


@register_embedding_function
class LocalHashingEmbedding:
    """本地哈希向量化（无网络依赖）。

    实现 signed hashing embedding：每个特征映射到固定维度桶，按出现次数累加并带符号，
    最后 L2 归一化。查询与文档用同一函数，保证余弦相似度可比。
    """

    def __init__(self, dim: int = LOCAL_EMBED_DIM):
        self.dim = dim

    def is_legacy(self) -> bool:
        """声明为非 legacy 的 known embedding function，避免 chromadb 弃用警告。"""
        return False

    def get_config(self) -> dict:
        """序列化配置，供 chromadb 持久化。"""
        return {"dim": self.dim}

    @classmethod
    def build_from_config(cls, config: dict) -> "LocalHashingEmbedding":
        """从持久化配置重建实例。"""
        return cls(dim=int(config.get("dim", LOCAL_EMBED_DIM)))

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 31) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in input]

    def embed_query(self, input) -> List[float]:
        if isinstance(input, list):
            return [self._embed(t) for t in input]
        return self._embed(input)

    def __call__(self, input: List[str]) -> List[List[float]]:
        """ChromaDB 新接口：统一以列表形式调用。"""
        return self.embed_documents(input)

    @classmethod
    def name(cls) -> str:
        """ChromaDB 要求的 embedding function 标识。"""
        return "local_hashing"

    def default_space(self) -> str:
        """向量已 L2 归一化，使用余弦距离。"""
        return "cosine"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    @staticmethod
    def validate_config(config: dict) -> None:
        """本地哈希无额外配置约束。"""
        return None


@register_embedding_function
class OpenAIEmbedding:
    """OpenAI 语义向量化（需 OPENAI_API_KEY）。

    仅在 provider=openai 且配置了 Key 时使用，提供比本地哈希更优的语义检索。
    """

    def __init__(self, model: str = "text-embedding-3-small", dim: int = 1536):
        self.model = model
        self.dim = dim
        api_key = llm_config.vision_api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("使用 OpenAI embedding 需要设置 OPENAI_API_KEY")
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)

    def is_legacy(self) -> bool:
        """声明为非 legacy 的 known embedding function。"""
        return False

    def get_config(self) -> dict:
        return {"model": self.model, "dim": self.dim}

    @classmethod
    def build_from_config(cls, config: dict) -> "OpenAIEmbedding":
        return cls(model=config.get("model", "text-embedding-3-small"),
                   dim=int(config.get("dim", 1536)))

    def _embed_sync(self, texts: List[str]) -> List[List[float]]:
        resp = self._client.embeddings.create(model=self.model, input=texts)
        return [list(d.embedding) for d in resp.data]

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        # ChromaDB 的 embedding_function 接口为同步调用
        return self._embed_sync(input)

    def embed_query(self, input) -> List[float]:
        if isinstance(input, list):
            return self._embed_sync(input)
        return self._embed_sync([input])[0]

    def __call__(self, input: List[str]) -> List[List[float]]:
        """ChromaDB 新接口：统一以列表形式调用。"""
        return self.embed_documents(input)

    @classmethod
    def name(cls) -> str:
        """ChromaDB 要求的 embedding function 标识。"""
        return "openai"

    def default_space(self) -> str:
        """OpenAI text-embedding-3-small 输出归一化向量，使用余弦距离。"""
        return "cosine"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    @staticmethod
    def validate_config(config: dict) -> None:
        return None


def get_embedding_function(provider: str = "local"):
    """按 provider 返回 EmbeddingFunction 实例。

    Parameters
    ----------
    provider : str
        "local"（默认，离线）或 "openai"（需 Key）。

    Returns
    -------
    具备 embed_documents / embed_query 方法的对象。
    """
    provider = (provider or "local").lower()
    if provider == "openai":
        try:
            return OpenAIEmbedding()
        except RuntimeError as e:
            logger.warning("OpenAI embedding 不可用（%s），回退到本地哈希向量", e)
            return LocalHashingEmbedding()
    return LocalHashingEmbedding()
