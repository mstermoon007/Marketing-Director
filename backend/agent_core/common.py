"""
Agent 共享工具
================================

子 Agent 之间复用的辅助函数：
- 行业识别（从自然语言抽取行业）
- 从文本创建企业档案（让 Agent 能直接基于自然语言开诊）
- RAG 卡片文本拼接
- 各意图的结构化回复渲染（模板化，保证离线可用、输出具体不空洞）
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy import select

from backend.db.models import AsyncSessionLocal, BusinessRecord, ExecutionPlanRecord
from backend.skills.loader import INDUSTRY_ALIASES, INDUSTRY_CANONICAL


logger = logging.getLogger(__name__)


# 行业别名按长度降序，保证「咖啡馆」优先于「餐饮」等长前缀匹配
_INDUSTRY_CANON_ITEMS = sorted(
    INDUSTRY_CANONICAL.items(), key=lambda kv: len(kv[0]), reverse=True
)


# ── 行业识别 ──
def detect_industry(text: str) -> Optional[str]:
    """从用户文本中识别行业，返回知识库行业标签（如『餐饮』『烘焙坊』）。

    未能识别返回 None。识别结果用于：
    - 企业档案 industry 字段（与知识库卡片 industry 元数据一致）
    - RAG 检索的 ``industry`` 过滤条件，确保方法库按行业精确命中
    """
    if not text:
        return None
    # 精确包含（长别名优先，避免被短别名抢先匹配）
    for alias, canon in _INDUSTRY_CANON_ITEMS:
        if alias in text:
            return canon
    # 模糊包含（兜底）
    for alias, canon in _INDUSTRY_CANON_ITEMS:
        if alias in text or text in alias:
            return canon
    return None


# ── 从文本创建企业档案 ──
async def create_business_from_text(
    text: str, industry: Optional[str] = None, user_id: Optional[str] = None
) -> str:
    """基于自然语言创建企业档案，返回 business_id。

    Parameters
    ----------
    text : str
        用户输入的自然语言描述。
    industry : Optional[str]
        行业（可选，缺省自动识别）。
    user_id : Optional[str]
        归属用户 ID。务必传入当前 JWT 用户，否则企业档案无所有者，
        后续对象级授权（防 IDOR）会拒绝访问。
    """
    from backend.db.models import gen_id

    industry = industry or detect_industry(text) or "其他"
    # 尝试抽取城市
    city_match = re.search(r"([\u4e00-\u9fff]{2,10}?(?:市|区|县))", text)
    city = city_match.group(1) if city_match else "未填写"
    # 店名：『我的X店』/『叫X』之类，缺省用行业占位
    name_match = re.search(r"(?:叫|名为|是|开了?|店名[是为]?)([\u4e00-\u9fffA-Za-z0-9]{2,12}?)(?:店|馆|铺|公司|工作室|号)", text)
    business_name = name_match.group(1) + "店" if name_match else f"我的{industry}店"

    bid = gen_id()
    async with AsyncSessionLocal() as session:
        session.add(BusinessRecord(
            id=bid,
            user_id=user_id,
            business_name=business_name,
            industry=industry,
            city=city,
            product_desc=text[:200],
            biggest_pain=text[:200],
        ))
        await session.commit()
    logger.info("Agent 从文本创建企业档案：%s（%s / %s）", bid, business_name, industry)
    return bid


async def business_exists(bid: str) -> bool:
    """企业档案是否存在。"""
    if not bid:
        return False
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(select(BusinessRecord).filter_by(id=bid))
        ).scalar_one_or_none()
        return rec is not None


async def business_owned_by(bid: str, user_id: str) -> bool:
    """校验企业档案归属当前用户（防 IDOR）。

    Agent 接口允许客户端携带 ``business_id``（用于复用既有企业、跨轮连续对话）。
    若该 ID 属于其他用户，必须拒绝下钻他人数据——但在对话流里不应直接抛 404 打断用户，
    而是返回 False，由调用方将其视为 None，回退到「按本会话 / 自动建档」的逻辑。
    """
    if not bid or not user_id:
        return False
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(
                select(BusinessRecord).filter_by(id=bid, user_id=user_id)
            )
        ).scalar_one_or_none()
        return rec is not None


async def load_latest_plan_targets(bid: str) -> dict:
    """读取某企业最新执行计划的关键指标目标，供复盘对比。"""
    if not bid:
        return {}
    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(
                select(ExecutionPlanRecord)
                .filter_by(business_id=bid)
                .order_by(ExecutionPlanRecord.created_at.desc())
            )
        ).scalars().first()
        if rec and rec.key_metrics:
            return rec.key_metrics
    return {}


# ── RAG 卡片文本拼接 ──
def format_cards(cards: list[dict], max_cards: int = 3) -> str:
    """把检索到的营销方法卡片拼成可读文本块。"""
    if not cards:
        return ""
    lines = []
    for i, c in enumerate(cards[:max_cards], 1):
        lines.append(
            f"【方法{i}】{c.get('name', '')}（类别：{c.get('category', '')}｜行业：{c.get('industry', '')}｜渠道：{c.get('channel', '')}）\n"
            f"  原理：{c.get('principle', '')}\n"
            f"  可衡量 KPI：{c.get('kpi', '')}\n"
            f"  正文：{c.get('content', '')}"
        )
    return "\n".join(lines)


# ── 回复渲染 ──
def render_diagnosis(report: dict, cards_text: str) -> str:
    score = report.get("overall_score", 0)
    summary = report.get("score_summary", "")
    breakdown = report.get("score_breakdown", {}) or {}
    problems = report.get("top3_problems", []) or []
    strategy = report.get("strategy_summary", "")
    focus = report.get("this_week_focus", "")

    bd = "、".join(f"{k}{v}" for k, v in breakdown.items()) if breakdown else "—"

    prob_lines = []
    for i, p in enumerate(problems, 1):
        if isinstance(p, dict):
            prob_lines.append(
                f"  {i}. [{p.get('severity', '')}] {p.get('description', '')}\n"
                f"     马上能做：{p.get('quick_fix', '')}"
            )
        else:
            prob_lines.append(f"  {i}. {p}")
    prob_text = "\n".join(prob_lines) if prob_lines else "  （暂无明显问题）"

    out = (
        f"📊 营销健康度评分：{score}/100\n"
        f"评分理由：{summary}\n"
        f"各维度：{bd}\n\n"
        f"🔍 诊断出的核心问题：\n{prob_text}\n\n"
        f"🎯 策略方向：{strategy}\n"
        f"本周重点：{focus}\n"
    )
    if cards_text:
        out += f"\n💡 参考打法（来自营销方法库）：\n{cards_text}\n"
    out += "\n下一步可说「帮我做计划」生成 7 天执行清单，或「排个日程」把动作分配到每天。"
    return out


def render_plan(plan: dict, schedule: dict | None, cards_text: str) -> str:
    theme = plan.get("theme", "")
    goals = plan.get("goals", []) or []
    days = plan.get("days", []) or []
    key_metrics = plan.get("key_metrics", {}) or {}

    out = f"🗂️ 本周主题：{theme}\n"
    if goals:
        out += "本周目标：\n" + "\n".join(f"  - {g}" for g in goals) + "\n"
    if key_metrics:
        out += "关键指标目标：" + "、".join(f"{k}={v}" for k, v in key_metrics.items()) + "\n"
    out += f"\n📅 7 天计划（共 {len(days)} 天）：\n"
    for d in days:
        if isinstance(d, dict):
            out += f"  · {d.get('day_label', '')}：{d.get('focus', '')}（{len(d.get('tasks', []))} 个任务）\n"
    if schedule and schedule.get("ok"):
        out += f"\n⏰ 已生成每日提醒（共 {len(schedule.get('reminders', []))} 条），每天 09:00 推送当天任务。\n"
    if cards_text:
        out += f"\n💡 计划可借鉴的打法：\n{cards_text}\n"
    out += "\n执行中可随时说「帮我复盘」，上传数据我做周复盘对比。"
    return out


def render_schedule(schedule: dict) -> str:
    if not schedule.get("ok"):
        return f"⚠️ {schedule.get('error', '无法排期')}"
    out = f"⏰ {schedule.get('goal') or '本周任务'} 排期如下（共 {schedule.get('total_tasks')} 个任务）：\n\n"
    for day in schedule.get("schedule", []):
        out += f"【{day.get('date')} 第{day.get('day_index')}天】\n"
        for t in day.get("tasks", []):
            out += f"  - {t.get('time_slot')}：{t.get('title')}\n"
    out += "\n🔔 主动提醒已就绪：\n"
    for r in schedule.get("reminders", []):
        out += f"  · {r.get('remind_at')}  {r.get('title')}\n"
    return out


def render_review(kpi: dict, cards_text: str, summary_text: str) -> str:
    out = f"📈 复盘结果：\n{kpi.get('summary', '')}\n\n"
    rows = kpi.get("rows", [])
    if rows:
        out += "指标明细：\n"
        for r in rows:
            rate = r.get("achievement_rate")
            rate_s = f"{rate}%" if rate is not None else "无目标"
            out += f"  - {r.get('metric')}：实际 {r.get('actual')} / 目标 {r.get('target')}（达成 {rate_s}）\n"
    trend = kpi.get("trend", [])
    if trend:
        out += "环比变化：\n"
        for t in trend:
            pct = t.get("pct")
            pct_s = f"{pct}%" if pct is not None else "—"
            out += f"  - {t.get('metric')}：{t.get('previous')} → {t.get('current')}（{pct_s}）\n"
    if summary_text:
        out += f"\n📝 归因与建议：\n{summary_text}\n"
    if cards_text:
        out += f"\n💡 可借鉴的调整打法：\n{cards_text}\n"
    return out
