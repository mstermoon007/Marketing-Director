"""
复盘 Agent 测试

覆盖：
1. CSV 解析
2. 图片解析（Mock 多模态）
3. 复盘报告生成
4. 数字提取（从非结构化文本）
5. 文件类型判断
6. 数据合并
7. Mock LLM 无效响应容错
"""

import pytest
from backend.agents.reviewer import ReviewAgent
from backend.models.review import ReviewReport, MetricComparison
from backend.utils.document_parser import (
    ParsedData, is_image_file, is_csv_file,
    parse_csv_content, parse_csv_file, merge_parsed_data,
)
from tests.fixtures.industries import ALL_INDUSTRIES
from tests.conftest import make_plan


# ──────────────────────────────────────────────
# 文件类型判断
# ──────────────────────────────────────────────

class TestFileTypeDetection:

    def test_is_image_file(self):
        assert is_image_file("screenshot.png") is True
        assert is_image_file("photo.jpg") is True
        assert is_image_file("photo.JPEG") is True
        assert is_image_file("data.csv") is False
        assert is_image_file("doc.pdf") is False

    def test_is_csv_file(self):
        assert is_csv_file("data.csv") is True
        assert is_csv_file("data.tsv") is True
        assert is_csv_file("data.CSV") is True
        assert is_csv_file("image.png") is False
        assert is_csv_file("doc.xlsx") is False


# ──────────────────────────────────────────────
# CSV 解析
# ──────────────────────────────────────────────

class TestCSVParser:

    def test_parse_key_value_csv(self):
        """两列 key-value 格式"""
        content = "新增客户,7\n咨询量,12\n成交量,1\n"
        result = parse_csv_content(content)
        assert result["新增客户"] == 7.0
        assert result["咨询量"] == 12.0
        assert result["成交量"] == 1.0

    def test_parse_multi_column_csv(self):
        """多列格式"""
        content = "日期,新增客户,咨询量\n7-29,5,8\n7-30,7,12\n"
        result = parse_csv_content(content)
        # 取最后一行的数值
        assert result.get("新增客户") == 7.0
        assert result.get("咨询量") == 12.0

    def test_parse_csv_with_bom(self):
        """带 BOM 的 CSV"""
        content = "\ufeff指标,数值\n新增客户,7\n"
        result = parse_csv_content(content)
        assert result.get("新增客户") == 7.0

    def test_parse_empty_csv(self):
        result = parse_csv_content("")
        assert result == {}

    def test_parse_csv_file_from_disk(self, tmp_path):
        """从文件读取 CSV"""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("指标,数值\n新增客户,7\n咨询量,12\n", encoding="utf-8-sig")

        parsed = parse_csv_file(str(csv_file))
        assert parsed.source_type == "csv"
        assert parsed.numbers["新增客户"] == 7.0
        assert parsed.numbers["咨询量"] == 12.0
        assert len(parsed.errors) == 0

    def test_parse_csv_file_not_found(self):
        """文件不存在"""
        parsed = parse_csv_file("/nonexistent/file.csv")
        assert len(parsed.errors) > 0
        assert parsed.source_type == "csv"

    def test_parse_all_industry_csvs(self):
        """5个行业的 CSV 内容都能正确解析"""
        for industry_key, data in ALL_INDUSTRIES.items():
            content = data["csv_content"]
            result = parse_csv_content(content)
            assert "新增客户" in result, f"{industry_key} CSV 缺少新增客户"
            assert "咨询量" in result, f"{industry_key} CSV 缺少咨询量"
            assert isinstance(result["新增客户"], float)


# ──────────────────────────────────────────────
# 数据合并
# ──────────────────────────────────────────────

class TestDataMerge:

    def test_merge_two_sources(self):
        d1 = ParsedData(numbers={"新增客户": 7, "咨询量": 12})
        d2 = ParsedData(numbers={"成交量": 1, "播放量": 5000})
        merged = merge_parsed_data(d1, d2)
        assert merged == {"新增客户": 7, "咨询量": 12, "成交量": 1, "播放量": 5000}

    def test_merge_first_value_wins(self):
        """同一指标，先出现的值优先"""
        d1 = ParsedData(numbers={"新增客户": 7})
        d2 = ParsedData(numbers={"新增客户": 10})
        merged = merge_parsed_data(d1, d2)
        assert merged["新增客户"] == 7

    def test_merge_empty(self):
        merged = merge_parsed_data()
        assert merged == {}

    def test_merge_with_errors(self):
        """有错误的源不影响合并"""
        d1 = ParsedData(numbers={"咨询量": 12})
        d2 = ParsedData(numbers={}, errors=["解析失败"])
        merged = merge_parsed_data(d1, d2)
        assert merged == {"咨询量": 12}


# ──────────────────────────────────────────────
# 数字提取
# ──────────────────────────────────────────────

class TestNumberExtraction:

    def test_extract_from_text(self):
        text = "本周新增客户：15人，咨询量：20次，成交量：2单，播放量：3500"
        result = ReviewAgent._extract_numbers_from_text(text)
        assert result.get("新增客户") == 15
        assert result.get("咨询量") == 20
        assert result.get("成交量") == 2
        assert result.get("播放量") == 3500

    def test_extract_from_text_no_numbers(self):
        text = "本周表现良好，数据稳定增长"
        result = ReviewAgent._extract_numbers_from_text(text)
        assert result == {}


# ──────────────────────────────────────────────
# 复盘 Agent
# ──────────────────────────────────────────────

class TestReviewAgent:

    @pytest.mark.asyncio
    async def test_csv_only_review(self, patched_llm, tmp_path):
        """只用 CSV 上传 → 生成复盘报告"""
        plan = make_plan("家装")

        # 写 CSV 文件
        csv_file = tmp_path / "data.csv"
        csv_file.write_text(ALL_INDUSTRIES["家装"]["csv_content"], encoding="utf-8-sig")

        patched_llm.set_responses(
            review=ALL_INDUSTRIES["家装"]["review_resp"]
        )

        agent = ReviewAgent()
        report = await agent.run(plan, [str(csv_file)])

        assert isinstance(report, ReviewReport)
        assert report.plan_id == plan.id
        assert len(report.summary) > 5
        assert len(report.suggestions) >= 1
        assert "新增客户" in report.numbers

    @pytest.mark.asyncio
    async def test_image_review_with_mock_vision(self, patched_llm, tmp_path):
        """图片上传 → Mock 多模态解析 → 生成复盘报告"""
        plan = make_plan("餐饮")

        # 创建一个假图片文件
        img_file = tmp_path / "screenshot.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # Mock 多模态返回提取的数字
        patched_llm.set_responses(
            vision={"numbers": {"新增客户": 87, "咨询量": 25, "成交量": 12}},
            review=ALL_INDUSTRIES["餐饮"]["review_resp"],
        )

        agent = ReviewAgent()
        report = await agent.run(plan, [str(img_file)])

        assert isinstance(report, ReviewReport)
        assert "新增客户" in report.numbers
        assert report.numbers["新增客户"] == 87

    @pytest.mark.asyncio
    async def test_mixed_files_csv_and_image(self, patched_llm, tmp_path):
        """同时上传 CSV 和图片"""
        plan = make_plan("教培")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(ALL_INDUSTRIES["教培"]["csv_content"], encoding="utf-8-sig")

        img_file = tmp_path / "screenshot.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        patched_llm.set_responses(
            vision={"numbers": {"笔记阅读量": 4800}},
            review=ALL_INDUSTRIES["教培"]["review_resp"],
        )

        agent = ReviewAgent()
        report = await agent.run(plan, [str(csv_file), str(img_file)])

        assert isinstance(report, ReviewReport)
        # CSV 和图片的数据都应在 numbers 中
        assert "新增客户" in report.numbers  # 来自 CSV
        assert "笔记阅读量" in report.numbers  # 来自图片

    @pytest.mark.asyncio
    async def test_no_valid_files_raises(self, patched_llm):
        """没有有效文件 → ValueError"""
        plan = make_plan("家装")
        agent = ReviewAgent()

        with pytest.raises(ValueError, match="没有可解析"):
            await agent.run(plan, ["/nonexistent/file.xyz"])

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back(self, patched_llm, tmp_path):
        """复盘报告 JSON 解析失败 → fallback 到本地规则报告（不抛 ValueError）"""
        plan = make_plan("家装")
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("指标,数值\n新增客户,7\n", encoding="utf-8-sig")

        patched_llm.set_responses(review="invalid{{{json")

        agent = ReviewAgent()
        report = await agent.run(plan, [str(csv_file)])

        # fallback 应返回合法报告
        assert len(report.summary) > 0
        assert len(report.suggestions) >= 1
        assert len(report.vs_target) >= 1

    @pytest.mark.asyncio
    async def test_vision_failure_graceful(self, patched_llm, tmp_path):
        """多模态解析失败 → 容错，不影响 CSV 解析"""
        plan = make_plan("美容")

        img_file = tmp_path / "screenshot.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(ALL_INDUSTRIES["美容"]["csv_content"], encoding="utf-8-sig")

        # Mock vision 抛异常
        async def failing_vision(*args, **kwargs):
            raise Exception("API connection failed")

        patched_llm.set_responses(
            review=ALL_INDUSTRIES["美容"]["review_resp"],
        )
        # 覆盖 chat_with_images 让它抛异常
        original_vision = patched_llm.chat_with_images
        patched_llm.chat_with_images = failing_vision

        agent = ReviewAgent()
        report = await agent.run(plan, [str(img_file), str(csv_file)])

        # 图片解析失败了，但 CSV 的数据还在
        assert isinstance(report, ReviewReport)
        assert "新增客户" in report.numbers  # 来自 CSV


# ──────────────────────────────────────────────
# 5个行业参数化测试
# ──────────────────────────────────────────────

class TestReviewAllIndustries:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_review_report_quality(self, patched_llm, tmp_path, industry_key):
        """5个行业复盘报告质量验证"""
        plan = make_plan(industry_key)

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(ALL_INDUSTRIES[industry_key]["csv_content"], encoding="utf-8-sig")

        patched_llm.set_responses(
            review=ALL_INDUSTRIES[industry_key]["review_resp"],
        )

        agent = ReviewAgent()
        report = await agent.run(plan, [str(csv_file)])

        assert isinstance(report, ReviewReport)
        assert len(report.summary) > 5
        assert len(report.vs_target) >= 1
        assert len(report.what_worked) >= 1
        assert len(report.what_didnt) >= 1
        assert len(report.suggestions) >= 1

        # vs_target 中的 MetricComparison 结构验证
        for comp in report.vs_target:
            assert isinstance(comp, MetricComparison)
            assert len(comp.metric_name) > 0
            assert isinstance(comp.achieved, bool)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_review_numbers_match_csv(self, patched_llm, tmp_path, industry_key):
        """复盘报告中的 numbers 应包含 CSV 提取的数据"""
        plan = make_plan(industry_key)

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(ALL_INDUSTRIES[industry_key]["csv_content"], encoding="utf-8-sig")

        patched_llm.set_responses(
            review=ALL_INDUSTRIES[industry_key]["review_resp"],
        )

        agent = ReviewAgent()
        report = await agent.run(plan, [str(csv_file)])

        assert "新增客户" in report.numbers
        assert "咨询量" in report.numbers
