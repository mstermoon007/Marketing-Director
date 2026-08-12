"""
会话管理
================================

维护多轮对话的会话状态：用户ID、绑定的企业ID、以及「待澄清意图」（用于追问回流）。

说明：会话为进程内内存态，重启后清空；对话历史本身持久化在 MemoryStore（ChromaDB），
因此重启后仍能加载历史上下文，只是会话级的 business_id / pending_intent 需重新建立。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    session_id: str
    user_id: str
    business_id: str = ""
    pending_intent: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class SessionManager:
    """进程内会话表。"""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str, user_id: str) -> Session:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess is None:
                sess = Session(session_id=session_id, user_id=user_id)
                self._sessions[session_id] = sess
            else:
                sess.updated_at = time.time()
            return sess

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def set_business(self, session_id: str, business_id: str) -> None:
        with self._lock:
            sess = self._sessions.get(session_id)
            if sess:
                sess.business_id = business_id
                sess.updated_at = time.time()
