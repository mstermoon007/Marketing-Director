"""
Agent 核心框架（后端大脑）
================================

多 Agent 协作层：可推理、可记忆、可调度工具。替代旧的线性 API，使后端具备
主动诊断、规划与复盘能力。

主要导出：
- ``MainController`` / ``get_controller``：统一对话入口
- ``build_agent_graph``：LangGraph 状态图
- ``KnowledgeBase`` / ``MemoryStore``：RAG 知识库与记忆库
- ``TOOLS`` / ``get_langchain_tools``：标准化业务工具
"""

from __future__ import annotations

from backend.agent_core.controller import MainController, get_controller
from backend.agent_core.graph import build_agent_graph
from backend.agent_core.knowledge import KnowledgeBase
from backend.agent_core.memory import MemoryStore
from backend.agent_core.tools import TOOLS, get_langchain_tools


__all__ = [
    "MainController",
    "get_controller",
    "build_agent_graph",
    "KnowledgeBase",
    "MemoryStore",
    "TOOLS",
    "get_langchain_tools",
]
