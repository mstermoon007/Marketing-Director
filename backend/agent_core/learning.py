"""
持续学习（Continuous Learning）
================================

把用户对 Agent 产出的反馈（点赞 👍 / 点踩 👎 / 计划修改）转化为「策略有效性评分」，
落库到 ``strategy_scores`` 表，并在后续 RAG 检索时对方法卡片做重排序，
实现「越用越懂你」。
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select

from backend.db.models import AsyncSessionLocal, FeedbackRecord, StrategyScoreRecord


logger = logging.getLogger(__name__)


async def record_feedback(
    user_id: str,
    target_type: str,
    target_id: Optional[str] = None,
    rating: int = 0,
    comment: Optional[str] = None,
    business_id: Optional[str] = None,
    card_ids: Optional[list[str]] = None,
) -> dict:
    """记录一条反馈，并更新相关方法卡片的策略有效性评分。

    Parameters
    ----------
    user_id : str
        反馈者（JWT user_id）。
    target_type : str
        diagnosis | plan | schedule | review | card | suggestion。
    target_id : str | None
        被反馈对象的 ID。
    rating : int
        +1 赞 / -1 踩 / 0 中性。
    comment : str | None
        文字反馈。
    business_id : str | None
        关联企业。
    card_ids : list[str] | None
        该结果所引用的营销方法卡片 ID 列表（用于归因到策略分）。
    """
    async with AsyncSessionLocal() as session:
        fb = FeedbackRecord(
            user_id=user_id,
            business_id=business_id,
            target_type=target_type,
            target_id=target_id,
            rating=rating,
            comment=comment,
            meta={"card_ids": card_ids or []},
        )
        session.add(fb)

        updated: list[dict] = []
        for cid in card_ids or []:
            rec = (
                await session.execute(select(StrategyScoreRecord).filter_by(card_id=cid))
            ).scalar_one_or_none()
            if rec is None:
                rec = StrategyScoreRecord(card_id=cid)
                session.add(rec)
            if rating > 0:
                rec.positive = (rec.positive or 0) + 1
            elif rating < 0:
                rec.negative = (rec.negative or 0) + 1
            # 有效性评分：正反馈加权 +1，负反馈加权 -2（更敏感地抑制无效策略）
            rec.score = (rec.score or 0) + (2 if rating > 0 else -3 if rating < 0 else 0)
            updated.append({"card_id": cid, "score": rec.score})

        await session.commit()

    return {"ok": True, "target_type": target_type, "rating": rating, "updated_scores": updated}


async def get_strategy_scores() -> dict[str, int]:
    """返回 card_id -> 有效性评分 的映射。"""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(StrategyScoreRecord))).scalars().all()
        return {r.card_id: (r.score or 0) for r in rows}


async def apply_strategy_scores(cards: list[dict]) -> list[dict]:
    """根据策略有效性评分对 RAG 卡片做重排序。

    Parameters
    ----------
    cards : list[dict]
        知识库检索结果（含 ``id`` / ``name`` / ``category`` / ``score`` 等）。

    Returns
    -------
    list[dict]：按「向量相似度 + 策略有效性」综合打分后的新顺序（原列表被复制，不破坏入参）。
    """
    scores = await get_strategy_scores()
    boosted: list[dict] = []
    for c in cards:
        c = dict(c)
        base = float(c.get("score") or 0.0)
        c["strategy_score"] = scores.get(c.get("id", ""), 0)
        # 综合：向量相似度（0~1）* 10 + 策略分（约 -N~+N），再给无评分卡片轻微惩罚以避免噪声
        c["rank_score"] = round(base * 10 + c["strategy_score"], 3)
        boosted.append(c)
    boosted.sort(key=lambda x: x["rank_score"], reverse=True)
    return boosted
