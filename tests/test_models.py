"""
数据模型测试

覆盖4个数据模型的创建、序列化、反序列化、约束验证。
"""

from datetime import date

from backend.models.business import BusinessProfile
from backend.models.diagnosis import DiagnosisReport, Problem
from backend.models.execution import DayPlan, SevenDayPlan, Task
from backend.models.review import MetricComparison, ReviewReport


# ──────────────────────────────────────────────
# BusinessProfile
# ──────────────────────────────────────────────

class TestBusinessProfile:

    def test_creation_with_all_fields(self):
        profile = BusinessProfile(
            id="b1",
            business_name="测试公司",
            industry="家装",
            city="杭州",
            product_desc="装修服务",
            price_range="800-1500元/平米",
            target_customers="30-45岁家庭",
            competitors="其他装修公司",
            current_channels="朋友圈+老客户",
            monthly_revenue="30万",
            team_size="8人",
            biggest_pain="获客困难",
        )
        assert profile.business_name == "测试公司"
        assert profile.industry == "家装"

    def test_is_complete_true(self):
        profile = BusinessProfile(
            business_name="测试", industry="家装", city="杭州",
            product_desc="装修", target_customers="家庭",
        )
        assert profile.is_complete() is True

    def test_is_complete_false_missing_required(self):
        """缺必填字段"""
        profile = BusinessProfile(
            business_name="测试", industry="家装", city="杭州",
            product_desc="装修",  # 缺 target_customers
        )
        assert profile.is_complete() is False

    def test_to_prompt_context_contains_all_fields(self):
        profile = BusinessProfile(
            business_name="鼎安装饰", industry="家装", city="杭州",
            product_desc="全案装修", target_customers="改善型家庭",
            biggest_pain="获客难",
        )
        ctx = profile.to_prompt_context()
        assert "鼎安装饰" in ctx
        assert "家装" in ctx
        assert "杭州" in ctx
        assert "全案装修" in ctx
        assert "改善型家庭" in ctx
        assert "获客难" in ctx

    def test_to_prompt_context_skips_empty_fields(self):
        profile = BusinessProfile(
            business_name="测试", industry="家装", city="杭州",
            product_desc="装修", target_customers="家庭",
            # price_range 等为空
        )
        ctx = profile.to_prompt_context()
        assert "价格区间" not in ctx


# ──────────────────────────────────────────────
# DiagnosisReport + Problem
# ──────────────────────────────────────────────

class TestDiagnosisReport:

    def test_from_ai_response(self):
        data = {
            "overall_score": 48,
            "score_summary": "渠道短板明显",
            "score_breakdown": {"定位": 65, "产品": 70, "渠道": 25, "内容": 20, "转化": 55},
            "top3_problems": [
                {"severity": "critical", "category": "渠道", "description": "渠道单一", "quick_fix": "开抖音"},
            ],
            "strategy_summary": "聚焦改善型家庭，用短视频获客",
            "this_week_focus": "注册抖音号",
        }
        report = DiagnosisReport.from_ai_response("biz_1", data)
        assert report.overall_score == 48
        assert report.business_id == "biz_1"
        assert report.score_summary == "渠道短板明显"
        assert len(report.top3_problems) == 1
        assert isinstance(report.top3_problems[0], Problem)
        assert report.top3_problems[0].severity == "critical"

    def test_from_ai_response_missing_fields(self):
        """容错：缺少字段不崩溃"""
        report = DiagnosisReport.from_ai_response("biz_1", {})
        assert report.overall_score == 0
        assert report.top3_problems == []
        assert report.strategy_summary == ""

    def test_to_dict_roundtrip(self):
        data = {
            "overall_score": 72,
            "score_summary": "测试",
            "score_breakdown": {"定位": 80},
            "top3_problems": [
                {"severity": "major", "category": "内容", "description": "问题", "quick_fix": "建议"},
            ],
            "strategy_summary": "策略",
            "this_week_focus": "重点",
        }
        report = DiagnosisReport.from_ai_response("biz_1", data)
        d = report.to_dict()
        assert d["overall_score"] == 72
        assert d["business_id"] == "biz_1"
        assert isinstance(d["top_issues"], list)
        assert d["top_issues"][0]["level"] == "medium"  # major severity → medium level


# ──────────────────────────────────────────────
# SevenDayPlan + DayPlan + Task
# ──────────────────────────────────────────────

class TestTask:

    def test_from_dict_with_field_aliases(self):
        """字段别名兼容：time_slot/time, estimated_minutes/minutes"""
        t1 = Task.from_dict({"time_slot": "上午", "title": "任务", "estimated_minutes": 30})
        assert t1.time_slot == "上午"
        assert t1.estimated_minutes == 30

        t2 = Task.from_dict({"time": "下午", "title": "任务", "minutes": 20})
        assert t2.time_slot == "下午"
        assert t2.estimated_minutes == 20

    def test_to_dict(self):
        t = Task(time_slot="上午", title="测试", how_to="做", checklist=["步骤1"], done_criteria="完成", estimated_minutes=30)
        d = t.to_dict()
        assert d["title"] == "测试"
        assert d["estimated_minutes"] == 30
        assert d["checklist"] == ["步骤1"]


class TestDayPlan:

    def test_total_minutes(self):
        day = DayPlan(
            day_label="周一",
            focus="测试",
            tasks=[
                Task(estimated_minutes=30),
                Task(estimated_minutes=20),
                Task(estimated_minutes=15),
            ],
        )
        assert day.total_minutes == 65

    def test_task_count(self):
        day = DayPlan(
            day_label="周一",
            focus="测试",
            tasks=[Task(), Task(), Task()],
        )
        assert day.task_count == 3

    def test_from_dict_with_day_alias(self):
        """day_label/day 字段别名"""
        d = DayPlan.from_dict({"day": "周二", "focus": "测试", "tasks": []})
        assert d.day_label == "周二"


class TestSevenDayPlan:

    def test_from_ai_response(self):
        data = {
            "theme": "启动短视频",
            "goals": ["发3条视频", "获10个咨询"],
            "key_metrics": {"新增客户": 5, "咨询量": 8},
            "days": [
                {"day_label": "周一", "focus": "准备", "tasks": [
                    {"time_slot": "上午", "title": "注册账号", "how_to": "下载注册", "checklist": [], "done_criteria": "完成", "estimated_minutes": 30},
                ]},
            ],
        }
        plan = SevenDayPlan.from_ai_response("d1", "b1", date(2026, 7, 29), data)
        assert plan.theme == "启动短视频"
        assert len(plan.goals) == 2
        assert len(plan.days) == 1
        assert isinstance(plan.days[0], DayPlan)
        assert isinstance(plan.days[0].tasks[0], Task)

    def test_validate_constraints_pass(self):
        """合规计划通过验证"""
        plan = SevenDayPlan(
            days=[
                DayPlan(day_label="周一", focus="t", tasks=[
                    Task(estimated_minutes=30),
                    Task(estimated_minutes=20),
                ]),
            ],
        )
        result = plan.validate_constraints()
        assert result["valid"] is True
        assert result["issues"] == []

    def test_validate_constraints_too_many_tasks(self):
        """超过5个任务"""
        plan = SevenDayPlan(
            days=[
                DayPlan(day_label="周一", focus="t", tasks=[
                    Task(estimated_minutes=10) for _ in range(6)
                ]),
            ],
        )
        result = plan.validate_constraints()
        assert result["valid"] is False
        assert any("任务数" in i for i in result["issues"])

    def test_validate_constraints_too_many_minutes(self):
        """超过120分钟"""
        plan = SevenDayPlan(
            days=[
                DayPlan(day_label="周一", focus="t", tasks=[
                    Task(estimated_minutes=60),
                    Task(estimated_minutes=70),
                ]),
            ],
        )
        result = plan.validate_constraints()
        assert result["valid"] is False
        assert any("耗时" in i for i in result["issues"])

    def test_validate_constraints_boundary_5_tasks_ok(self):
        """恰好5个任务：通过"""
        plan = SevenDayPlan(
            days=[
                DayPlan(day_label="周一", focus="t", tasks=[
                    Task(estimated_minutes=20) for _ in range(5)
                ]),
            ],
        )
        assert plan.validate_constraints()["valid"] is True

    def test_validate_constraints_boundary_120_minutes_ok(self):
        """恰好120分钟：通过"""
        plan = SevenDayPlan(
            days=[
                DayPlan(day_label="周一", focus="t", tasks=[
                    Task(estimated_minutes=60),
                    Task(estimated_minutes=60),
                ]),
            ],
        )
        assert plan.validate_constraints()["valid"] is True


# ──────────────────────────────────────────────
# ReviewReport + MetricComparison
# ──────────────────────────────────────────────

class TestReviewReport:

    def test_from_ai_response(self):
        data = {
            "summary": "本周达标",
            "numbers": {"新增客户": 7, "咨询量": 12},
            "vs_target": [
                {"metric_name": "新增客户", "target": 5, "actual": 7, "achieved": True},
                {"metric_name": "成交量", "target": 3, "actual": 1, "achieved": False},
            ],
            "what_worked": ["短视频效果好"],
            "what_didnt": ["转介绍响应低"],
            "suggestions": ["优化话术", "增加视频"],
        }
        report = ReviewReport.from_ai_response("p1", "b1", data)
        assert report.summary == "本周达标"
        assert len(report.vs_target) == 2
        assert isinstance(report.vs_target[0], MetricComparison)
        assert report.vs_target[0].achieved is True
        assert report.vs_target[1].achieved is False
        assert len(report.suggestions) == 2

    def test_to_dict(self):
        report = ReviewReport(
            id="r1", plan_id="p1", business_id="b1",
            summary="测试",
            numbers={"咨询量": 10},
            vs_target=[MetricComparison(metric_name="咨询量", target=8, actual=10, achieved=True)],
            what_worked=["A"],
            what_didnt=["B"],
            suggestions=["C"],
        )
        d = report.to_dict()
        assert d["summary"] == "测试"
        assert d["vs_target"][0]["achieved"] is True
