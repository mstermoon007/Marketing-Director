"""
诊断 Agent 测试

覆盖：
1. Mock LLM 返回有效 JSON → DiagnosisReport 正确创建
2. Mock LLM 返回无效 JSON → ValueError
3. Mock LLM 返回缺少字段 → 容错处理
4. Prompt 模板加载和渲染
5. 5个行业诊断报告质量验证
"""

import pytest
from src.agents.diagnosis import DiagnosisAgent
from src.models.diagnosis import DiagnosisReport, Problem
from src.prompts.loader import load_prompt, list_available_prompts
from tests.fixtures.industries import ALL_INDUSTRIES
from tests.conftest import make_profile


# ──────────────────────────────────────────────
# Prompt 模板
# ──────────────────────────────────────────────

class TestDiagnosisPrompt:

    def test_prompt_template_exists(self):
        prompts = list_available_prompts()
        assert "diagnosis/system.txt" in prompts

    def test_prompt_renders_with_business_context(self):
        ctx = "- 企业名称：测试公司\n- 行业：家装"
        rendered = load_prompt("diagnosis/system.txt", business_context=ctx)
        assert "测试公司" in rendered
        assert "家装" in rendered
        assert "overall_score" in rendered  # 包含 JSON 输出格式说明

    def test_prompt_contains_key_constraints(self):
        rendered = load_prompt("diagnosis/system.txt", business_context="测试")
        assert "strategy_summary" in rendered
        assert "top3_problems" in rendered
        assert "this_week_focus" in rendered


# ──────────────────────────────────────────────
# Agent 基础功能
# ──────────────────────────────────────────────

class TestDiagnosisAgentBasic:

    @pytest.mark.asyncio
    async def test_valid_json_response(self, patched_llm):
        """Mock 返回有效 JSON → 正确创建 DiagnosisReport"""
        profile = make_profile("家装")
        patched_llm.set_responses(
            diagnosis=ALL_INDUSTRIES["家装"]["diagnosis_resp"]
        )

        agent = DiagnosisAgent()
        report = await agent.run(profile)

        assert isinstance(report, DiagnosisReport)
        assert report.business_id == profile.id
        assert 0 <= report.overall_score <= 100
        assert len(report.strategy_summary) > 0
        assert len(report.top3_problems) > 0
        assert all(isinstance(p, Problem) for p in report.top3_problems)

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back_to_local(self, patched_llm):
        """Mock 返回无效 JSON → 不抛异常，fallback 到本地规则引擎，返回有效报告"""
        profile = make_profile("家装")
        patched_llm.set_responses(diagnosis="这不是JSON{{{")

        agent = DiagnosisAgent()
        # 新的设计：不抛 ValueError，fallback 到本地规则引擎
        report = await agent.run(profile)

        assert isinstance(report, DiagnosisReport)
        assert 0 <= report.overall_score <= 100
        # fallback 返回本地规则生成的报告
        assert report.strategy_summary  # 有策略
        assert len(report.top3_problems) >= 1

    @pytest.mark.asyncio
    async def test_missing_fields_graceful(self, patched_llm):
        """Mock 返回缺少字段（有效JSON但缺字段）→ 不崩溃，用默认值补齐"""
        profile = make_profile("家装")
        patched_llm.set_responses(diagnosis={"overall_score": 50})

        agent = DiagnosisAgent()
        report = await agent.run(profile)

        # LLM 路径被走到，返回的字段被保留
        assert report.overall_score == 50
        # 缺少字段用默认值补齐
        assert report.top3_problems == []
        assert report.strategy_summary == ""

    @pytest.mark.asyncio
    async def test_llm_called_with_json_mode(self, patched_llm):
        """验证 LLM 被调用时 json_mode=True"""
        profile = make_profile("家装")
        patched_llm.set_responses(
            diagnosis=ALL_INDUSTRIES["家装"]["diagnosis_resp"]
        )

        agent = DiagnosisAgent()
        await agent.run(profile)

        assert len(patched_llm.calls) >= 1
        assert patched_llm.calls[0]["json_mode"] is True


# ──────────────────────────────────────────────
# 5个行业参数化测试
# ──────────────────────────────────────────────

class TestDiagnosisAllIndustries:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_diagnosis_report_quality(self, patched_llm, industry_key):
        """5个行业诊断报告质量验证"""
        profile = make_profile(industry_key)
        patched_llm.set_responses(
            diagnosis=ALL_INDUSTRIES[industry_key]["diagnosis_resp"]
        )

        agent = DiagnosisAgent()
        report = await agent.run(profile)

        # 基础结构验证
        assert isinstance(report, DiagnosisReport)
        assert 0 <= report.overall_score <= 100
        assert len(report.score_summary) > 5  # 不是空字符串
        assert len(report.top3_problems) >= 1
        assert len(report.strategy_summary) > 10  # 有实质内容
        assert len(report.this_week_focus) > 3

        # score_breakdown：根据行业选择合适的维度断言
        # 地产行业（中介/房产）使用专属 6 维度，其他行业使用 5 维度
        real_estate_industries = {"中介", "房产", "地产", "房产中介", "房地产"}
        if industry_key in real_estate_industries:
            expected_dims = [
                "房源获取", "带看转化", "社区渗透",
                "线上获客", "专业形象", "数据运营"
            ]
        else:
            expected_dims = ["定位", "产品", "渠道", "内容", "转化"]

        for dim in expected_dims:
            assert dim in report.score_breakdown, (
                f"{industry_key} score_breakdown 缺少维度: {dim}, "
                f"实际有: {list(report.score_breakdown.keys())}"
            )
            assert 0 <= report.score_breakdown[dim] <= 100

        # 问题严重程度必须在合法范围
        valid_severities = {"critical", "major", "minor"}
        for problem in report.top3_problems:
            assert problem.severity in valid_severities
            assert len(problem.description) > 5
            assert len(problem.quick_fix) > 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_strategy_summary_is_specific(self, patched_llm, industry_key):
        """策略方向必须具体可执行（不是空泛建议）"""
        profile = make_profile(industry_key)
        patched_llm.set_responses(
            diagnosis=ALL_INDUSTRIES[industry_key]["diagnosis_resp"]
        )

        agent = DiagnosisAgent()
        report = await agent.run(profile)

        strategy = report.strategy_summary
        # 不能是空泛建议
        vague_phrases = ["做好品牌建设", "提升服务质量", "加强营销"]
        for phrase in vague_phrases:
            assert phrase not in strategy, f"策略方向包含空泛建议: {phrase}"
