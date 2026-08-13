"""
离线零售 KPI 公式测试（不依赖大模型）
======================================

覆盖 ``backend.agent_core.kpi_formulas.calculate_retail_kpis``（SKILL-03 19 个指标落地），
以及 ``calculate_kpi``（真实实现，经 importlib 绕过 conftest 的 stub 副本）在合并零售 KPI
后：derived 应含 坪效 等指标，且返回值新增 retail_kpis 字段。

conftest 把 ``backend.agent_core`` 整体替换为 fake 包，故 kpi_formulas / tools 均通过
importlib 直接加载并登记到 sys.modules（kpi_formulas 须先于 tools 登记，使 tools 内部
``from backend.agent_core.kpi_formulas import ...`` 命中真实模块）。
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest


# ── 加载真实 kpi_formulas，登记到 sys.modules ──
_KPI_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "agent_core", "kpi_formulas.py"
)
_kpi_spec = importlib.util.spec_from_file_location(
    "backend.agent_core.kpi_formulas", os.path.abspath(_KPI_PATH)
)
_real_kpi = importlib.util.module_from_spec(_kpi_spec)
sys.modules["backend.agent_core.kpi_formulas"] = _real_kpi
_kpi_spec.loader.exec_module(_real_kpi)

from backend.agent_core.kpi_formulas import (  # noqa: E402
    RETAIL_KPI_FORMULAS,
    calculate_retail_kpis,
)


# ── calculate_retail_kpis ──
def test_calculate_retail_kpis_pingxiao():
    """营业额 + 店铺面积 → 坪效可算。"""
    res = calculate_retail_kpis({"营业额": 8000, "店铺面积": 100})
    ping = [r for r in res if r["key"] == "坪效"]
    assert ping, f"未算出坪效，res={res}"
    assert ping[0]["value"] == pytest.approx(80.0, abs=0.01)
    assert ping[0]["benchmark_level"] == "—"
    assert "diagnosis" in ping[0] and ping[0]["advice"]


def test_calculate_retail_kpis_multiple():
    """多指标齐备 → 同时算出坪效/人效/ATV/VIP占比等。"""
    numbers = {
        "营业额": 8000, "店铺面积": 100, "总人数": 5, "客单数": 40,
        "VIP消费额": 4000, "销售件数": 80, "业绩指标": 10000,
    }
    res = calculate_retail_kpis(numbers)
    keys = {r["key"] for r in res}
    names = {r["name"] for r in res}
    for needed in ("坪效", "人效", "ATV", "VIP占比", "连带率", "ASP"):
        assert needed in keys, f"缺少 {needed}，keys={keys}"
    assert "连带销售率" in names, f"name 未含 连带销售率，names={names}"
    vip = [r for r in res if r["key"] == "VIP占比"][0]
    assert vip["value"] == pytest.approx(50.0, abs=0.01)
    assert vip["benchmark_level"] == "健康"


def test_calculate_retail_kpis_missing_inputs_skipped():
    """输入不全 → 跳过，不报错。"""
    res = calculate_retail_kpis({"营业额": 8000})  # 缺 店铺面积/业绩指标 等
    assert isinstance(res, list)
    assert all("value" in r and "diagnosis" in r for r in res)


def test_retail_kpi_formulas_registry_complete():
    """SKILL-03 核心公式应登记（≥16 条）。"""
    assert len(RETAIL_KPI_FORMULAS) >= 16


# ── calculate_kpi 合并零售 KPI（真实实现，importlib 绕过 stub）──
_TOOLS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "agent_core", "tools.py"
)
_spec = importlib.util.spec_from_file_location("real_agent_tools_kpi", os.path.abspath(_TOOLS_PATH))
_real_tools = importlib.util.module_from_spec(_spec)
# tools.py 内部 import 的 agent_core 子模块仍为 conftest 的 stub，仅 kpi_formulas 已替换为真实
_spec.loader.exec_module(_real_tools)
calculate_kpi = _real_tools.calculate_kpi


def test_calculate_kpi_includes_retail_pingxiao():
    """含 营业额/面积 → derived 含 坪效；返回新增 retail_kpis 字段。"""
    kpi = calculate_kpi({"营业额": 8000, "店铺面积": 100, "新增客户": 12, "咨询量": 45})
    assert "retail_kpis" in kpi
    assert "坪效" in kpi["derived"]
    assert kpi["derived"]["坪效"] == pytest.approx(80.0, abs=0.01)
    # retail_kpis 中也应含坪效
    keys = {r["key"] for r in kpi["retail_kpis"]}
    assert "坪效" in keys


def test_calculate_kpi_legacy_derived_preserved():
    """原有派生指标（成交转化率/咨询转化率/客单价）仍保留，未回归。"""
    kpi = calculate_kpi(
        {"新增客户": 12, "咨询量": 45, "成交量": 8, "成交额": 3200},
        {"新增客户": 10, "咨询量": 40},
        {"新增客户": 9, "咨询量": 30},
    )
    # 不含零售指标键时，retail_kpis 为空，derived 仅原三件套
    assert kpi["derived"]["成交转化率(%)"] == pytest.approx(17.8, abs=0.1)
    assert kpi["derived"]["客单价"] == pytest.approx(266.7, abs=0.1)
    assert kpi["retail_kpis"] == []
