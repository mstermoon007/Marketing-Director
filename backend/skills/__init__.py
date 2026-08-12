"""
行业技能模块 v2
参考开发思路文档：技能模块 — 按行业分类存储营销知识

支持两种组织方式：
1. 单文件模式：industry_skills/ 下的 .md 文件（旧格式，兼容保留）
2. 目录模式：real_estate/ 等目录下的多个 .md 文件（新格式，更结构化）

地产行业使用目录模式深化诊断，包含：诊断标准、渠道策略、指标基准、客户画像、案例库。
"""

from backend.skills.loader import (
    get_real_estate_subcategories,
    get_skill_injection,
    list_available_skills,
    load_skill_separated,
    match_industry_skill,
    validate_skills_directory,
)


__all__ = [
    "get_real_estate_subcategories",
    "get_skill_injection",
    "list_available_skills",
    "load_skill_separated",
    "match_industry_skill",
    "validate_skills_directory",
]
