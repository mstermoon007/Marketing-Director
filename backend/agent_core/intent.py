"""
意图分类器
================================

将用户自然语言输入分类为 5 类意图之一：

- ``diagnose`` 诊断  ：把脉/打分/分析健康问题
- ``plan``    计划  ：要 7 天执行方案/策略
- ``schedule`` 日程  ：要按天排期/提醒
- ``review``  复盘  ：上传数据做周复盘/对比达成
- ``chat``    问答  ：通用咨询/闲聊/知识问答

策略：规则关键词匹配（零依赖、离线可用）为主；当配置了 LLM 且 ``AGENT_USE_LLM_INTENT=true`` 时，
可用 LLM 增强（当前默认回退规则，保证无 Key 环境稳定）。若上轮是追问（pending_intent），
且本轮输入像是在回答而非新指令，则沿用 pending_intent。
"""

from __future__ import annotations

from backend.agent_core.state import (
    INTENT_CHAT,
    INTENT_DIAGNOSE,
    INTENT_PLAN,
    INTENT_REVIEW,
    INTENT_SCHEDULE,
)

# 各意图触发词
_REVIEW_KW = ["复盘", "回顾", "总结上周", "上周", "本周总结", "对比", "达成", "上传截图", "上传数据", "上传文件", "截图", "看看数据"]
_DIAGNOSE_KW = ["诊断", "把脉", "打分", "健康度", "体检", "分析一下", "问题在哪", "哪里有问题", "什么问题", "现状", "诊断报告"]
_PLAN_KW = ["计划", "方案", "7天", "七天", "执行清单", "怎么做", "策略", "本周", "行动", "落地", "规划"]
_SCHEDULE_KW = ["日程", "排期", "安排", "提醒", "每天", "周几", "排到", "时间表", "提醒我"]

# 用于判断「本轮是否像在回答追问」的强指令词
_COMMAND_KW = (
    _REVIEW_KW + _DIAGNOSE_KW + _PLAN_KW + _SCHEDULE_KW
    + ["诊断", "计划", "排期", "复盘", "你好", "你是", "什么是", "怎么", "如何"]
)


def _has_command(text: str) -> bool:
    return any(k in text for k in _COMMAND_KW)


def classify_intent(text: str, pending_intent: str | None = None) -> str:
    """分类意图。

    Parameters
    ----------
    text : str
        用户当前输入。
    pending_intent : str | None
        上轮留下的待澄清意图（追问场景）。

    Returns
    -------
    str：INTENT_* 常量。
    """
    text = (text or "").strip()

    # 追问回流：上轮在问问题，本轮像在回答（短、无新指令）→ 沿用 pending
    if pending_intent and 0 < len(text) <= 40 and not _has_command(text):
        return pending_intent

    # 规则优先级：复盘 > 诊断 > 日程 > 计划 > 闲聊
    # （「日程」比「计划」更具体；含排期/提醒类词时优先日程，避免被「计划」一词抢占）
    if any(k in text for k in _REVIEW_KW):
        return INTENT_REVIEW
    if any(k in text for k in _DIAGNOSE_KW):
        return INTENT_DIAGNOSE
    if any(k in text for k in _SCHEDULE_KW):
        return INTENT_SCHEDULE
    if any(k in text for k in _PLAN_KW):
        return INTENT_PLAN
    return INTENT_CHAT
