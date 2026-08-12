"""
闲聊 / 问答子 Agent
================================

处理通用咨询、问候、知识问答。所有回答都基于 RAG 检索到的营销方法卡片，
并携带用户画像上下文，避免「通用聊天式空洞建议」。
"""

from __future__ import annotations

import re

from backend.agent_core.common import format_cards
from backend.agent_core.tools import search_marketing_knowledge


_GREETING = re.compile(r"^(你好|您好|hi|hello|在吗|你是谁|你是?什么)", re.IGNORECASE)


async def run_chat(state: dict, memory, kb) -> dict:
    user_msg = state.get("user_message", "").strip()

    if _GREETING.match(user_msg):
        state["response"] = (
            "我是你的 AI 营销战略执行助手 🤖\n"
            "你可以直接说：\n"
            "· 「帮我诊断一下我的店」（告诉我行业和痛点）\n"
            "· 「帮我做个本周计划」\n"
            "· 「把计划排成日程并提醒我」\n"
            "· 上传数据后说「帮我复盘」\n"
            "也可以直接问我任何营销打法问题。"
        )
        return state

    # RAG 检索方法卡片作为回答支撑
    rag = await search_marketing_knowledge(user_msg, top_k=3)
    cards = rag.get("cards", [])
    cards_text = format_cards(cards)

    profile = memory.get_profile(state["user_id"])
    prof_text = profile["text"] if profile else "（新用户，暂无画像）"

    if cards_text:
        state["response"] = (
            f"关于「{user_msg}」，结合营销方法库给你几个具体打法：\n\n{cards_text}\n\n"
            f"（基于你的画像：{prof_text[:120]}）\n"
            "需要我针对你的生意直接诊断或做计划吗？告诉我行业和痛点即可。"
        )
    else:
        state["response"] = (
            "我可以帮你做营销诊断、生成执行计划、排期提醒和周复盘。\n"
            "告诉我你的行业和当前最头疼的问题，我直接从诊断开始。"
        )
    state["knowledge_context"] = cards_text
    return state
