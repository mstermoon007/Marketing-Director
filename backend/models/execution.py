"""
执行计划数据模型（核心）
参考开发思路文档：第3.3节 SevenDayPlan

约束：每天不超过5个任务，总计不超过2小时。
这是整条链路的核心产出——老板拿到后不需要任何额外思考就能执行。
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Task:
    """单个任务"""
    time_slot: str = ""             # "09:00-09:30" 或 "上午"
    title: str = ""                 # 任务标题
    how_to: str = ""                # 怎么做（1-2句话）
    checklist: list = field(default_factory=list)   # 执行步骤
    done_criteria: str = ""         # 什么叫完成了
    estimated_minutes: int = 0      # 预估耗时（分钟）

    def to_dict(self) -> dict:
        return {
            "time_slot": self.time_slot,
            "title": self.title,
            "how_to": self.how_to,
            "checklist": self.checklist,
            "done_criteria": self.done_criteria,
            "estimated_minutes": self.estimated_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            time_slot=data.get("time_slot", data.get("time", "")),
            title=data.get("title", ""),
            how_to=data.get("how_to", ""),
            checklist=data.get("checklist", []),
            done_criteria=data.get("done_criteria", ""),
            estimated_minutes=data.get("estimated_minutes", data.get("minutes", 0)),
        )


@dataclass
class DayPlan:
    """单天计划"""
    day_label: str = ""             # "周一"、"周二"...
    focus: str = ""                 # 当天重点一句话
    tasks: list = field(default_factory=list)   # list[Task]

    def to_dict(self) -> dict:
        return {
            "day_label": self.day_label,
            "focus": self.focus,
            "tasks": [
                t.to_dict() if isinstance(t, Task) else t
                for t in self.tasks
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DayPlan":
        tasks = [
            Task.from_dict(t) if isinstance(t, dict) else t
            for t in data.get("tasks", [])
        ]
        return cls(
            day_label=data.get("day_label", data.get("day", "")),
            focus=data.get("focus", ""),
            tasks=tasks,
        )

    @property
    def total_minutes(self) -> int:
        """当天任务总耗时"""
        return sum(
            t.estimated_minutes if isinstance(t, Task) else t.get("estimated_minutes", 0)
            for t in self.tasks
        )

    @property
    def task_count(self) -> int:
        return len(self.tasks)


@dataclass
class SevenDayPlan:
    """
    7天执行清单 — 核心数据

    这是产品的核心产出：把诊断结论翻译成老板每天能执行的清单。
    输出质量直接决定产品价值。
    """
    id: str = ""
    diagnosis_id: str = ""
    business_id: str = ""
    start_date: Optional[date] = None
    theme: str = ""                         # 本周主题
    goals: list = field(default_factory=list)       # 本周目标（2-3条）
    key_metrics: dict = field(default_factory=lambda: {
        "新增客户": 0, "咨询量": 0, "成交量": 0
    })
    days: list = field(default_factory=list)        # 7天计划 list[DayPlan]
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "diagnosis_id": self.diagnosis_id,
            "business_id": self.business_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "theme": self.theme,
            "goals": self.goals,
            "key_metrics": self.key_metrics,
            "days": [
                d.to_dict() if isinstance(d, DayPlan) else d
                for d in self.days
            ],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_ai_response(
        cls,
        diagnosis_id: str,
        business_id: str,
        start_date: date,
        data: dict,
    ) -> "SevenDayPlan":
        """从 AI 返回的 JSON 构造 7 天计划"""
        days = [
            DayPlan.from_dict(d) if isinstance(d, dict) else d
            for d in data.get("days", [])
        ]
        return cls(
            diagnosis_id=diagnosis_id,
            business_id=business_id,
            start_date=start_date,
            theme=data.get("theme", ""),
            goals=data.get("goals", []),
            key_metrics=data.get("key_metrics", {"新增客户": 0, "咨询量": 0, "成交量": 0}),
            days=days,
        )

    def validate_constraints(self) -> dict:
        """
        验证执行引擎约束：每天 ≤5 任务，≤120 分钟
        返回 {"valid": true} 或 {"valid": false, "issues": [...]}
        """
        issues = []
        max_tasks, max_minutes = 5, 120

        for day in self.days:
            d = day if isinstance(day, DayPlan) else DayPlan.from_dict(day)
            if d.task_count > max_tasks:
                issues.append(f"{d.day_label}: 任务数 {d.task_count} > {max_tasks}")
            if d.total_minutes > max_minutes:
                issues.append(
                    f"{d.day_label}: 总耗时 {d.total_minutes}分钟 > {max_minutes}分钟"
                )

        return {"valid": len(issues) == 0, "issues": issues}
