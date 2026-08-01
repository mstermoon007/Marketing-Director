"""
企业信息数据模型
参考开发思路文档：第3.1节 BusinessProfile

设计原则：表单字段尽量少，自由文本为主。
小老板没耐心填结构化问卷，用大白话说，AI负责理解和结构化。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BusinessProfile:
    """用户在第一步填写的企业信息，整个链路的起点"""
    id: str = ""
    business_name: str = ""
    industry: str = ""              # 家装/餐饮/教培/美容/中介/其他
    city: str = ""
    product_desc: str = ""          # 卖什么，自由文本
    price_range: str = ""           # 价格区间
    target_customers: str = ""      # 目标客户，自由文本
    competitors: str = ""           # 竞品是谁，自由文本
    current_channels: str = ""      # 现在怎么获客，自由文本
    monthly_revenue: str = ""       # 月营业额（允许填"不便透露"）
    team_size: str = ""             # 几个人干
    biggest_pain: str = ""          # 最大痛点，自由文本
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_prompt_context(self) -> str:
        """将企业信息格式化为 Prompt 可用的上下文文本"""
        fields = {
            "企业名称": self.business_name,
            "行业": self.industry,
            "所在城市": self.city,
            "产品/服务": self.product_desc,
            "价格区间": self.price_range,
            "目标客户": self.target_customers,
            "竞争对手": self.competitors,
            "当前获客方式": self.current_channels,
            "月营业额": self.monthly_revenue,
            "团队规模": self.team_size,
            "最大痛点": self.biggest_pain,
        }
        lines = []
        for label, value in fields.items():
            if value:
                lines.append(f"- {label}：{value}")
        return "\n".join(lines)

    def is_complete(self) -> bool:
        """检查必填字段是否完整"""
        required = [
            self.business_name,
            self.industry,
            self.city,
            self.product_desc,
            self.target_customers,
        ]
        return all(required)
