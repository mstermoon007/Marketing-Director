"""
Prompt 模板测试

覆盖：
1. 所有模板文件存在且可加载
2. Jinja2 变量正确渲染
3. 模板包含关键字段约束
4. 模板版本号存在
"""

from backend.prompts.loader import load_prompt, load_raw_prompt, list_available_prompts, validate_template_structure


class TestPromptTemplates:

    def test_all_templates_exist(self):
        """4个模板文件全部存在"""
        prompts = list_available_prompts()
        assert "diagnosis/system.txt" in prompts
        assert "executor/system.txt" in prompts
        assert "reviewer/parse_image.txt" in prompts
        assert "reviewer/report.txt" in prompts

    def test_template_structure_valid(self):
        """模板结构验证通过"""
        assert validate_template_structure() is True


class TestDiagnosisPrompt:

    def test_renders_business_context(self):
        ctx = "- 企业名称：测试公司\n- 行业：家装\n- 城市：杭州"
        rendered = load_prompt("diagnosis/system.txt", business_context=ctx)
        assert "测试公司" in rendered
        assert "家装" in rendered

    def test_contains_json_output_format(self):
        rendered = load_prompt("diagnosis/system.txt", business_context="测试")
        assert "overall_score" in rendered
        assert "score_breakdown" in rendered
        assert "top3_problems" in rendered
        assert "strategy_summary" in rendered

    def test_contains_role_definition(self):
        rendered = load_prompt("diagnosis/system.txt", business_context="测试")
        assert "营销顾问" in rendered

    def test_contains_constraints(self):
        rendered = load_prompt("diagnosis/system.txt", business_context="测试")
        # 约束：不要空泛建议
        assert "空泛" in rendered or "具体" in rendered

    def test_version_in_header(self):
        raw = load_raw_prompt("diagnosis/system.txt")
        assert "版本" in raw or "version" in raw.lower()


class TestExecutorPrompt:

    def test_renders_all_variables(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="企业信息上下文",
            diagnosis_context="诊断结论上下文",
            start_date="2026-07-29",
        )
        assert "企业信息上下文" in rendered
        assert "诊断结论上下文" in rendered
        assert "2026-07-29" in rendered

    def test_contains_5_step_translation(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="测试", diagnosis_context="测试", start_date="2026-07-29",
        )
        assert "Step 1" in rendered or "策略分解" in rendered
        assert "Step 2" in rendered or "子任务" in rendered
        assert "Step 3" in rendered or "排期" in rendered

    def test_contains_hard_constraints(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="测试", diagnosis_context="测试", start_date="2026-07-29",
        )
        assert "5个任务" in rendered or "不超过5" in rendered
        assert "2小时" in rendered or "120分钟" in rendered

    def test_contains_json_output_format(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="测试", diagnosis_context="测试", start_date="2026-07-29",
        )
        assert "theme" in rendered
        assert "goals" in rendered
        assert "key_metrics" in rendered
        assert "days" in rendered
        assert "tasks" in rendered

    def test_contains_saturday_constraint(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="测试", diagnosis_context="测试", start_date="2026-07-29",
        )
        assert "周六" in rendered
        assert "数据汇总" in rendered or "数据" in rendered

    def test_version_in_header(self):
        raw = load_raw_prompt("executor/system.txt")
        assert "版本" in raw or "version" in raw.lower()


class TestReviewerPrompts:

    def test_parse_image_prompt_loads(self):
        raw = load_raw_prompt("reviewer/parse_image.txt")
        assert len(raw) > 50
        assert "数字" in raw or "数据" in raw

    def test_report_prompt_renders(self):
        rendered = load_prompt(
            "reviewer/report.txt",
            goals_context="本周目标：新增客户10人",
            numbers_context='{"新增客户": 7}',
        )
        assert "本周目标：新增客户10人" in rendered
        assert '"新增客户": 7' in rendered

    def test_report_prompt_contains_output_structure(self):
        rendered = load_prompt(
            "reviewer/report.txt",
            goals_context="测试", numbers_context="{}",
        )
        assert "summary" in rendered or "总结" in rendered
        assert "vs_target" in rendered or "对比" in rendered
        assert "suggestions" in rendered or "建议" in rendered
