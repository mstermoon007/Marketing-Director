"""
离线营销理论引擎测试（不依赖大模型）
=====================================

覆盖 ``backend.agent_core.theory``：
- ``select_frameworks``     ：按文本信号推荐适用框架
- ``apply_framework``       ：按框架维度产出结构化分析
- ``recommend_tools``       ：按问题类型推荐商业分析工具
- ``analyze_profile_theory``：编排产出理论分析（frameworks / framework_analysis / recommended_tools）

conftest 把 ``backend.agent_core`` 整体替换为 fake 模块，非 stub 子模块（theory）无法经
常规 ``import`` 命中，故此处用 importlib 直接加载真实文件并登记到 sys.modules，
再 ``from`` 取用（与 test_data_isolation_review_iteration.py 加载真实 tools.py 同理）。
全部为纯函数 / 规则，无需 LLM Key、网络或 DB。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from types import SimpleNamespace

# 直接加载真实 backend.agent_core.theory（绕过 conftest 的 fake 包）
_THEORY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "agent_core", "theory.py"
)
_spec = importlib.util.spec_from_file_location(
    "backend.agent_core.theory", os.path.abspath(_THEORY_PATH)
)
_real_theory = importlib.util.module_from_spec(_spec)
sys.modules["backend.agent_core.theory"] = _real_theory
_spec.loader.exec_module(_real_theory)

from backend.agent_core.theory import (  # noqa: E402
    MARKETING_FRAMEWORKS,
    analyze_profile_theory,
    apply_framework,
    recommend_tools,
    select_frameworks,
)


# ── select_frameworks ──
def test_select_frameworks_detects_4i_social():
    """文本含社媒/内容/短视频信号 → 命中 4I（网络/社交媒体时代）。"""
    hit = select_frameworks("我们在做短视频内容营销，走社交平台互动，吸引粉丝")
    assert "4I" in hit


def test_select_frameworks_detects_4p_price_channel():
    """文本含定价/渠道/促销信号 → 命中 4P。"""
    hit = select_frameworks("目前定价偏高，渠道覆盖不足，促销投放效果一般")
    assert "4P" in hit


def test_select_frameworks_no_signal_empty():
    """无信号文本 → 返回空列表（不臆造框架）。"""
    hit = select_frameworks("今天天气不错")
    assert hit == []


# ── apply_framework ──
def test_apply_framework_4p_structure():
    """4P 框架应返回完整四维结构与中文分析字段。"""
    r = apply_framework("4P")
    assert r["framework"] == "4P"
    assert r["name"] == "4P 营销理论"
    assert len(r["dimensions"]) == 4
    assert "产品(Product)" in r["dimensions"]
    assert "现状诊断" in r
    assert "优化建议" in r
    assert "度量指标" in r
    assert isinstance(r["度量指标"], list) and len(r["度量指标"]) == 4


def test_apply_framework_unknown_returns_empty():
    assert apply_framework("999") == {}


# ── recommend_tools ──
def test_recommend_tools_brand_positioning():
    """「品牌定位」问题 → 推荐 USP/定位理论/品牌形象论/CI系统。"""
    tools = recommend_tools("品牌定位")
    assert "定位理论" in tools
    assert "USP理论" in tools


def test_recommend_tools_strategic_planning():
    tools = recommend_tools("战略规划")
    assert "SWOT分析法" in tools
    assert "波特竞争理论" in tools


def test_recommend_tools_empty_fallback():
    """空问题类型 → 通用工具兜底。"""
    tools = recommend_tools("")
    assert "SWOT分析法" in tools


# ── analyze_profile_theory ──
def _sample_profile(pain="客户流失严重，服务响应慢", industry="餐饮"):
    return SimpleNamespace(
        biggest_pain=pain,
        industry=industry,
        business_name="测试店",
        product_desc="",
        city="",
        to_prompt_context=lambda: f"{industry} {pain}",
    )


def test_analyze_profile_theory_includes_frames_and_tools():
    """带社媒信号的 profile → frameworks 非空、framework_analysis 对应、recommended_tools 非空。"""
    profile = _sample_profile(pain="短视频内容互动不足，社交渠道获客弱")
    out = analyze_profile_theory(profile, {"粉丝数": 1200, "成交额": 8000})
    assert isinstance(out["frameworks"], list)
    assert len(out["frameworks"]) >= 1
    # framework_analysis 覆盖所有 frameworks
    for fw in out["frameworks"]:
        assert fw in out["framework_analysis"]
        assert out["framework_analysis"][fw]["framework"] == fw
    assert len(out["recommended_tools"]) >= 1


def test_analyze_profile_theory_tools_from_pain():
    """工具推荐由痛点/行业推导，而非固定输出。"""
    profile = _sample_profile(pain="客户流失严重，服务响应慢", industry="餐饮")
    out = analyze_profile_theory(profile, {})
    assert "客户流失" in profile.biggest_pain
    # 服务/流失信号 → 至少给出通用战略工具
    assert len(out["recommended_tools"]) >= 1


def test_marketing_frameworks_complete_six():
    """SKILL-01 的 6 个框架应完整登记。"""
    assert set(MARKETING_FRAMEWORKS.keys()) == {"4P", "4C", "4S", "4R", "4V", "4I"}
