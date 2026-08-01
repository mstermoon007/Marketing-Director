"""
执行引擎 Agent 测试（核心壁垒模块）

覆盖：
1. Mock LLM 返回有效计划 → SevenDayPlan 正确创建
2. 约束验证：≤5任务/天，≤120分钟/天
3. 约束不通过时的重试逻辑
4. Mock LLM 返回无效 JSON → ValueError
5. 5个行业执行计划质量验证
6. Prompt 模板加载和渲染
7. 7天结构完整性验证
"""

import pytest
from datetime import date
from src.agents.executor import ExecutorAgent
from src.models.execution import SevenDayPlan
from src.prompts.loader import load_prompt
from tests.fixtures.industries import ALL_INDUSTRIES
from tests.conftest import make_profile, make_diagnosis


# ──────────────────────────────────────────────
# Prompt 模板
# ──────────────────────────────────────────────

class TestExecutorPrompt:

    def test_prompt_template_exists(self):
        from src.prompts.loader import list_available_prompts
        prompts = list_available_prompts()
        assert "executor/system.txt" in prompts

    def test_prompt_renders_with_contexts(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="企业信息",
            diagnosis_context="诊断信息",
            start_date="2026-07-29",
        )
        assert "企业信息" in rendered
        assert "诊断信息" in rendered
        assert "2026-07-29" in rendered

    def test_prompt_contains_constraints(self):
        rendered = load_prompt(
            "executor/system.txt",
            business_context="测试",
            diagnosis_context="测试",
            start_date="2026-07-29",
        )
        assert "5个任务" in rendered or "不超过5" in rendered
        assert "2小时" in rendered or "120分钟" in rendered
        assert "how_to" in rendered
        assert "done_criteria" in rendered


# ──────────────────────────────────────────────
# Agent 基础功能
# ──────────────────────────────────────────────

class TestExecutorAgentBasic:

    @pytest.mark.asyncio
    async def test_valid_plan_creation(self, patched_llm):
        """Mock 返回有效计划 → 正确创建 SevenDayPlan"""
        profile = make_profile("家装")
        diagnosis = make_diagnosis("家装")
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES["家装"]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        assert isinstance(plan, SevenDayPlan)
        assert plan.diagnosis_id == diagnosis.id
        assert plan.business_id == profile.id
        assert len(plan.theme) > 0
        assert len(plan.goals) >= 1
        assert "新增客户" in plan.key_metrics

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back_to_local(self, patched_llm):
        profile = make_profile("家装")
        diagnosis = make_diagnosis("家装")
        patched_llm.set_responses(executor="invalid{{{json")

        agent = ExecutorAgent()
        # 新的设计：不抛 ValueError，fallback 到本地生成计划
        plan = await agent.run(profile, diagnosis)

        assert len(plan.days) == 7
        assert len(plan.theme) > 0
        assert all(len(d.tasks) > 0 for d in plan.days)

    @pytest.mark.asyncio
    async def test_llm_called_with_json_mode(self, patched_llm):
        profile = make_profile("家装")
        diagnosis = make_diagnosis("家装")
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES["家装"]["executor_resp"]
        )

        agent = ExecutorAgent()
        await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        assert len(patched_llm.calls) >= 1
        assert patched_llm.calls[0]["json_mode"] is True


# ──────────────────────────────────────────────
# 约束验证 + 重试逻辑
# ──────────────────────────────────────────────

class TestExecutorConstraints:

    @pytest.mark.asyncio
    async def test_constraint_violation_triggers_retry(self, patched_llm):
        """约束不通过时触发重试"""
        profile = make_profile("家装")
        diagnosis = make_diagnosis("家装")

        # 第一次：超6个任务（不合规）
        bad_plan = {
            "theme": "测试",
            "goals": ["目标"],
            "key_metrics": {"新增客户": 0},
            "days": [
                {
                    "day_label": "周一",
                    "focus": "测试",
                    "tasks": [
                        {"time_slot": "上午", "title": f"任务{i}", "how_to": "做",
                         "checklist": [], "done_criteria": "完成", "estimated_minutes": 10}
                        for i in range(7)  # 7个任务，超过5
                    ],
                },
            ],
        }
        # 第二次：合规
        good_plan = ALL_INDUSTRIES["家装"]["executor_resp"]

        patched_llm.set_executor_retry_sequence([bad_plan, good_plan])

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        # 验证用了2次调用
        assert len(patched_llm.calls) == 2
        # 最终计划通过了约束
        validation = plan.validate_constraints()
        assert validation["valid"] is True

    @pytest.mark.asyncio
    async def test_retry_feedback_contains_issues(self, patched_llm):
        """重试时的 user_message 包含具体问题"""
        profile = make_profile("家装")
        diagnosis = make_diagnosis("家装")

        bad_plan = {
            "theme": "测试",
            "goals": ["目标"],
            "key_metrics": {"新增客户": 0},
            "days": [
                {
                    "day_label": "周一",
                    "focus": "测试",
                    "tasks": [
                        {"time_slot": "上午", "title": "任务", "how_to": "做",
                         "checklist": [], "done_criteria": "完成", "estimated_minutes": 200}
                    ],
                },
            ],
        }
        good_plan = ALL_INDUSTRIES["家装"]["executor_resp"]

        patched_llm.set_executor_retry_sequence([bad_plan, good_plan])

        agent = ExecutorAgent()
        await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        # 第二次调用的 user_message 应包含修正要求
        second_call = patched_llm.calls[1]
        assert "修正" in second_call["user_message"] or "约束" in second_call["user_message"]

    @pytest.mark.asyncio
    async def test_max_retries_falls_back(self, patched_llm):
        """超过最大重试次数 → fallback 到本地计划（不抛 ValueError）"""
        profile = make_profile("家装")
        diagnosis = make_diagnosis("家装")

        bad_plan = {
            "theme": "测试",
            "goals": ["目标"],
            "key_metrics": {"新增客户": 0},
            "days": [
                {
                    "day_label": "周一",
                    "focus": "测试",
                    "tasks": [
                        {"time_slot": "上午", "title": f"任务{i}", "how_to": "做",
                         "checklist": [], "done_criteria": "完成", "estimated_minutes": 10}
                        for i in range(7)
                    ],
                },
            ],
        }
        # 所有3次都返回不合规
        patched_llm.set_executor_retry_sequence([bad_plan, bad_plan, bad_plan])

        agent = ExecutorAgent()
        # 新的设计：3次都不通过 → fallback 到本地生成有效计划
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))
        assert len(plan.days) == 7
        # 本地 fallback 生成的计划通过约束（每天 <=5 任务，<= 2h）
        v = plan.validate_constraints()
        assert v["valid"] is True


# ──────────────────────────────────────────────
# 5个行业参数化测试
# ──────────────────────────────────────────────

class TestExecutorAllIndustries:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_plan_passes_constraints(self, patched_llm, industry_key):
        """5个行业执行计划全部通过约束验证"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        validation = plan.validate_constraints()
        assert validation["valid"] is True, f"{industry_key}计划约束不通过: {validation['issues']}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_plan_has_seven_days(self, patched_llm, industry_key):
        """5个行业计划都有7天"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        assert len(plan.days) == 7, f"{industry_key}计划天数不是7: {len(plan.days)}"
        day_labels = [d.day_label for d in plan.days]
        for label in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]:
            assert label in day_labels, f"{industry_key}缺少{label}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_plan_has_theme_and_goals(self, patched_llm, industry_key):
        """计划有主题和目标"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        assert len(plan.theme) > 5
        assert len(plan.goals) >= 2
        assert len(plan.goals) <= 5
        assert "新增客户" in plan.key_metrics
        assert "咨询量" in plan.key_metrics

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_saturday_has_data_summary(self, patched_llm, industry_key):
        """周六安排了数据汇总（文档要求）"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        saturday = next(d for d in plan.days if d.day_label == "周六")
        # 周六的 focus 或某个 task title 应该和"数据"相关
        all_text = saturday.focus + " ".join(t.title for t in saturday.tasks)
        assert "数据" in all_text or "汇总" in all_text or "截图" in all_text, \
            f"{industry_key}周六没有安排数据汇总"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_tasks_have_how_to_and_done_criteria(self, patched_llm, industry_key):
        """每个任务都有 how_to 和 done_criteria"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        for day in plan.days:
            for task in day.tasks:
                assert len(task.how_to) > 3, f"{industry_key} {day.day_label} '{task.title}' 缺少 how_to"
                assert len(task.done_criteria) > 3, f"{industry_key} {day.day_label} '{task.title}' 缺少 done_criteria"
                assert task.estimated_minutes > 0, f"{industry_key} {day.day_label} '{task.title}' estimated_minutes 为0"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_daily_minutes_under_120(self, patched_llm, industry_key):
        """每天总耗时不超过120分钟"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        for day in plan.days:
            assert day.total_minutes <= 120, \
                f"{industry_key} {day.day_label} 总耗时 {day.total_minutes} > 120"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    async def test_daily_tasks_under_5(self, patched_llm, industry_key):
        """每天任务数不超过5个"""
        profile = make_profile(industry_key)
        diagnosis = make_diagnosis(industry_key)
        patched_llm.set_responses(
            executor=ALL_INDUSTRIES[industry_key]["executor_resp"]
        )

        agent = ExecutorAgent()
        plan = await agent.run(profile, diagnosis, start_date=date(2026, 7, 29))

        for day in plan.days:
            assert day.task_count <= 5, \
                f"{industry_key} {day.day_label} 任务数 {day.task_count} > 5"
