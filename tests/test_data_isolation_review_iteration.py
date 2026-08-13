"""
数据隔离 + 复盘迭代 测试

覆盖本次迭代的两块修复：

一、数据隔离（防 IDOR）
  - ``business_owned_by`` 仅当 business 归属当前用户时返回 True；
  - 跨用户传入他人 business_id 必须被拒绝（返回 False），
    由 controller 回退为 None，不下钻他人数据。

二、复盘迭代（单客户数据复盘迭代是否有效）
  - 复盘链路依赖 ``calculate_kpi(numbers, targets, previous)`` 产出环比趋势；
  - ``_build_review_summary`` 在 KPI 带趋势时给出迭代对比（环比）叙述。
  此处直接对这两个「真实实现」做单元验证（conftest 对 agent_core 做了去重依赖
  stub，端到端走真实后端见 8001 实测）。
"""

from __future__ import annotations

import importlib.util
import os

import pytest
from sqlalchemy import select

from backend.agent_core.common import business_owned_by
from backend.agent_core.sub_agents.reviewer_agent import _build_review_summary
from backend.db.models import AsyncSessionLocal, BusinessRecord, gen_id

# 直接加载真实 backend.agent_core.tools（绕过 conftest 注入的 stub 副本），
# 确保验证的是线上真实使用的 calculate_kpi。
_TOOLS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "agent_core", "tools.py"
)
_spec = importlib.util.spec_from_file_location("real_agent_tools", os.path.abspath(_TOOLS_PATH))
_real_tools = importlib.util.module_from_spec(_spec)
# tools.py 内部 import 的 agent_core 子模块仍是 conftest 的 stub，不影响本验证
_spec.loader.exec_module(_real_tools)
calculate_kpi = _real_tools.calculate_kpi


# ──────────────────────────────────────────────
# 一、数据隔离
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_business_owned_by_isolation():
    owner = f"owner_{gen_id()}"
    other = f"other_{gen_id()}"
    bid = gen_id()
    async with AsyncSessionLocal() as s:
        s.add(BusinessRecord(
            id=bid,
            user_id=owner,
            business_name="隔离测试店",
            industry="餐饮",
            city="成都",
            product_desc="x",
            biggest_pain="y",
        ))
        await s.commit()

    # 归属当前用户 → True
    assert await business_owned_by(bid, owner) is True
    # 跨用户 → False（不下钻他人数据）
    assert await business_owned_by(bid, other) is False
    # 不存在的企业 → False
    assert await business_owned_by("nonexistent_id", owner) is False
    # 空参数 → False
    assert await business_owned_by("", owner) is False


# ──────────────────────────────────────────────
# 二、复盘迭代
# ──────────────────────────────────────────────
def test_review_iteration_previous_produces_trend():
    """上一周期 新增客户=9，本周期=15 → KPI 应带出环比趋势。"""
    kpi = calculate_kpi(
        {"新增客户": 15, "咨询量": 30},
        {},  # 无目标
        {"新增客户": 9},  # 上一周期
    )
    trend = kpi.get("trend", [])
    matched = [t for t in trend if t.get("metric") == "新增客户"]
    assert matched, f"复盘未产出新增客户的环比趋势，trend={trend}"
    assert matched[0]["previous"] == pytest.approx(9)
    assert matched[0]["current"] == pytest.approx(15)
    assert matched[0]["delta"] == pytest.approx(6)


def test_review_iteration_summary_mentions_trend():
    """KPI 带趋势时，复盘归因文本应包含迭代对比（环比）叙述。"""
    kpi = calculate_kpi(
        {"新增客户": 15, "咨询量": 30},
        {},
        {"新增客户": 9, "咨询量": 20},
    )
    summary = _build_review_summary(kpi, {"新增客户": 15, "咨询量": 30}, {})
    assert "环比" in summary or "迭代对比" in summary, (
        f"复盘回复缺少迭代对比叙述：{summary[:80]}"
    )
