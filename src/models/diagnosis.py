"""
诊断报告数据模型
参考开发思路文档：第3.2节 DiagnosisReport

包含企业营销健康度评分、问题诊断、策略方向。
诊断和策略在一个 Prompt 中完成，不分成两次调用。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Problem:
    """单个营销问题"""
    severity: str = ""              # critical / major / minor
    category: str = ""              # 定位/产品/渠道/内容/转化
    description: str = ""           # 一句话问题描述
    quick_fix: str = ""             # 一个马上能做的事

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "quick_fix": self.quick_fix,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Problem":
        return cls(
            severity=data.get("severity", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            quick_fix=data.get("quick_fix", ""),
        )


@dataclass
class DiagnosisReport:
    """
    诊断报告

    这条链路中诊断报告要解决的问题：
    1. 企业营销健康度打分（让老板意识到问题）
    2. Top3问题和方向性建议（告诉老板该往哪走）
    3. 一句话策略方向（作为执行引擎的关键输入）
    """
    id: str = ""
    business_id: str = ""
    overall_score: int = 0                     # 0-100
    score_summary: str = ""                     # 评分理由一句话
    score_breakdown: dict = field(default_factory=lambda: {
        "定位": 0, "产品": 0, "渠道": 0, "内容": 0, "转化": 0
    })
    top3_problems: list = field(default_factory=list)      # list[Problem]
    strategy_summary: str = ""                  # 一句话策略方向（执行引擎的关键输入）
    this_week_focus: str = ""                   # 本周应重点做的一件事
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "business_id": self.business_id,
            "overall_score": self.overall_score,
            "score_summary": self.score_summary,
            "score_breakdown": self.score_breakdown,
            "top3_problems": [
                p.to_dict() if isinstance(p, Problem) else p
                for p in self.top3_problems
            ],
            "strategy_summary": self.strategy_summary,
            "this_week_focus": self.this_week_focus,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_ai_response(cls, business_id: str, data: dict) -> "DiagnosisReport":
        """从 AI 返回的 JSON 构造诊断报告"""
        problems = [
            Problem.from_dict(p) if isinstance(p, dict) else p
            for p in data.get("top3_problems", [])
        ]
        return cls(
            business_id=business_id,
            overall_score=data.get("overall_score", 0),
            score_summary=data.get("score_summary", ""),
            score_breakdown=data.get("score_breakdown", {
                "定位": 0, "产品": 0, "渠道": 0, "内容": 0, "转化": 0
            }),
            top3_problems=problems,
            strategy_summary=data.get("strategy_summary", ""),
            this_week_focus=data.get("this_week_focus", ""),
        )
