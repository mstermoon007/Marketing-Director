"""
复盘报告数据模型
参考开发思路文档：第3.4节 ReviewReport

周末上传截图/CSV，AI解析后生成复盘报告，给出下周建议。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class MetricComparison:
    """单个指标的目标 vs 实际对比"""
    metric_name: str = ""
    target: float = 0.0
    actual: float = 0.0
    achieved: bool = False

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "target": self.target,
            "actual": self.actual,
            "achieved": self.achieved,
        }


@dataclass
class ReviewReport:
    """
    复盘报告

    处理流程（参考文档 4.3）：
    用户上传截图/CSV → 多模态识别 → 提取数据 → AI对比分析 → 生成复盘报告
    """
    id: str = ""
    plan_id: str = ""
    business_id: str = ""
    summary: str = ""                               # 本周一句话总结
    numbers: dict = field(default_factory=dict)     # 提取的数字
    vs_target: list = field(default_factory=list)   # list[MetricComparison]
    what_worked: list = field(default_factory=list)      # 做得好的
    what_didnt: list = field(default_factory=list)       # 没做到的
    suggestions: list = field(default_factory=list)      # 3条下周建议
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "business_id": self.business_id,
            "summary": self.summary,
            "numbers": self.numbers,
            "vs_target": [
                m.to_dict() if isinstance(m, MetricComparison) else m
                for m in self.vs_target
            ],
            "what_worked": self.what_worked,
            "what_didnt": self.what_didnt,
            "suggestions": self.suggestions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_ai_response(cls, plan_id: str, business_id: str, data: dict) -> "ReviewReport":
        """从 AI 返回的 JSON 构造复盘报告"""
        comparisons = []
        for item in data.get("vs_target", []):
            if isinstance(item, dict):
                comparisons.append(MetricComparison(
                    metric_name=item.get("metric_name", ""),
                    target=float(item.get("target", 0)),
                    actual=float(item.get("actual", 0)),
                    achieved=item.get("achieved", False),
                ))

        return cls(
            plan_id=plan_id,
            business_id=business_id,
            summary=data.get("summary", ""),
            numbers=data.get("numbers", {}),
            vs_target=comparisons,
            what_worked=data.get("what_worked", []),
            what_didnt=data.get("what_didnt", []),
            suggestions=data.get("suggestions", []),
        )
