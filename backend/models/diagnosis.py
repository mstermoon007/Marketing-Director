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
    severity: str = ""              # critical / major / minor (AI输出字段)
    level: str = ""                 # high / medium / low (API输出字段，映射自severity)
    title: str = ""                 # 问题标题
    suggestion: str = ""            # 一句话建议
    category: str = ""              # 定位/产品/渠道/内容/转化
    description: str = ""           # 一句话问题描述
    quick_fix: str = ""             # 一个马上能做的事

    def to_dict(self) -> dict:
        return {
            "level": self.level or self._map_severity(),
            "title": self.title or self.category or self.description[:20],
            "suggestion": self.suggestion or self.quick_fix,
            "category": self.category,
            "description": self.description,
            "quick_fix": self.quick_fix,
        }

    def _map_severity(self) -> str:
        """将 AI 输出的 severity(critical/major/minor) 映射为前端 level(high/medium/low)。"""
        mapping = {"critical": "high", "major": "medium", "minor": "low"}
        return mapping.get(self.severity, "medium")

    @classmethod
    def from_dict(cls, data: dict) -> "Problem":
        # Accept both old and new field names from AI
        severity = data.get("severity", "")
        level = data.get("level", "")
        return cls(
            severity=severity,
            level=level or ({"high": "critical", "medium": "major", "low": "minor"}.get(data.get("level", ""), "")),
            title=data.get("title", ""),
            suggestion=data.get("suggestion", ""),
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
    theory_analysis: dict = field(default_factory=dict)   # 离线营销理论分析（框架+工具）
    frameworks: list = field(default_factory=list)        # 适用的营销框架 key 列表
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "business_id": self.business_id,
            "overall_score": self.overall_score,
            "overall_comment": self.score_summary,
            "dimension_scores": self.score_breakdown,
            "top_issues": [
                p.to_dict() if isinstance(p, Problem) else p
                for p in self.top3_problems
            ],
            "strategy_summary": self.strategy_summary,
            "this_week_focus": self.this_week_focus,
            "theory_analysis": self.theory_analysis,
            "frameworks": self.frameworks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_ai_response(cls, business_id: str, data: dict) -> "DiagnosisReport":
        """从 AI 返回的 JSON 构造诊断报告（兼容新旧字段名）。"""
        problems = [
            Problem.from_dict(p) if isinstance(p, dict) else p
            for p in (data.get("top_issues") or data.get("top3_problems", []))
        ]
        return cls(
            business_id=business_id,
            overall_score=data.get("overall_score", 0),
            score_summary=data.get("overall_comment") or data.get("score_summary", ""),
            score_breakdown=data.get("dimension_scores") or data.get("score_breakdown", {
                "定位": 0, "产品": 0, "渠道": 0, "内容": 0, "转化": 0
            }),
            top3_problems=problems,
            strategy_summary=data.get("strategy_summary", ""),
            this_week_focus=data.get("this_week_focus", ""),
        )
