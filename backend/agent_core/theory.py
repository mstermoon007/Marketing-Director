"""
营销理论分析引擎（离线，无大模型依赖）
========================================

把 ``/Users/zhanggaozhang/TRAE-CN/SKILL-/`` 中的两份理论资产落地为可调用、可测试的
纯函数，供本地诊断（rule_based_diagnosis）在「不靠大模型」的前提下产出结构化理论分析：

- ``SKILL-01 marketing-theory``：4P / 4C / 4S / 4R / 4V / 4I 六大框架诊断引擎。
- ``SKILL-02 business-analysis-tools``：19 个经典商业分析工具（SWOT、二八、USP、定位…）。

设计原则：
- 全部为纯函数 / 纯数据，不调用 LLM、不碰数据库、可单测。
- 作为**附加产出**接入诊断，不改动既有评分与维度键（零回归风险）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# 一、六大营销理论框架（SKILL-01）
# ──────────────────────────────────────────────

@dataclass
class Framework:
    key: str
    name: str
    dimensions: list[str]          # 4 个核心要素
    orientation: str               # 核心导向
    era: str                       # 时代背景
    angle: str                     # 分析切入点（用于「优化建议」）


MARKETING_FRAMEWORKS: dict[str, Framework] = {
    "4P": Framework(
        key="4P", name="4P 营销理论",
        dimensions=["产品(Product)", "价格(Price)", "渠道(Place)", "促销(Promotion)"],
        orientation="企业/产品导向", era="传统市场经济",
        angle="从企业可控的产品、价格、渠道、促销四要素组合诊断营销短板，形成统一配套战略。",
    ),
    "4C": Framework(
        key="4C", name="4C 营销理论",
        dimensions=["消费者(Consumer)", "成本(Cost)", "便利(Convenience)", "沟通(Communication)"],
        orientation="消费者需求导向", era="整合营销时代",
        angle="以消费者需求为中心，审视需求满足、总成本、购买便利与双向沟通。",
    ),
    "4S": Framework(
        key="4S", name="4S 营销理论",
        dimensions=["满意(Satisfaction)", "服务(Service)", "速度(Speed)", "诚意(Sincerity)"],
        orientation="消费者占有导向", era="服务营销时代",
        angle="以服务品质最优化使消费者满意最大化，进而建立忠诚与指名度。",
    ),
    "4R": Framework(
        key="4R", name="4R 营销理论",
        dimensions=["关联(Relevance)", "反应(Reaction)", "关系(Relationship)", "回报(Reward)"],
        orientation="竞争/关系导向", era="关系营销时代",
        angle="在更高层次以有效方式与顾客建立关联、快速反应、长期关系与回报。",
    ),
    "4V": Framework(
        key="4V", name="4V 营销理论",
        dimensions=["差异化(Variation)", "功能化(Versatility)", "附加价值(Value)", "共鸣(Vibration)"],
        orientation="价值创新导向", era="高科技/互联网时代",
        angle="通过差异化、柔性功能、无形附加价值与价值共鸣实现与对手区隔。",
    ),
    "4I": Framework(
        key="4I", name="4I 营销理论",
        dimensions=["趣味(Interesting)", "利益(Interests)", "互动(Interaction)", "个性(Individuality)"],
        orientation="用户参与导向", era="网络/社交媒体时代",
        angle="网络时代用趣味、利益、互动与个性化让营销信息被主动接受与传播。",
    ),
}

# 数据类型信号 → 推荐框架（SKILL-01「第一步：识别数据类型」）
_SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "4P": ["产品", "定价", "价格", "成本", "渠道", "分销", "促销", "广告", "投放", "活动"],
    "4C": ["消费者", "用户调研", "客单价", "购物路径", "客户投诉", "nps", "需求", "便利", "沟通"],
    "4S": ["满意度", "服务", "响应", "客诉", "复购", "流失", "售后", "体验"],
    "4R": ["crm", "客户生命周期", "市场份额", "roi", "忠诚", "关联", "回报"],
    "4V": ["竞品", "竞对", "差异化", "产品矩阵", "品牌资产", "技术壁垒", "品牌"],
    "4I": ["社媒", "社交", "内容", "互动", "用户画像", "转化漏斗", "短视频", "直播", "粉丝"],
}


def select_frameworks(text: str) -> list[str]:
    """根据文本信号推荐适用的营销框架（可多选）。

    Parameters
    ----------
    text : str
        由企业信息（profile 各字段）与指标名（numbers 键）拼接而成的文本。

    Returns
    -------
    list[str]：命中的框架 key 列表（如 ["4P", "4I"]）；无信号时返回空列表。
    """
    text = (text or "").lower()
    hit = []
    for fw, kws in _SIGNAL_KEYWORDS.items():
        if any(kw in text for kw in kws):
            hit.append(fw)
    return hit


def apply_framework(framework_key: str, profile_text: str = "", numbers: Optional[dict] = None) -> dict:
    """按框架维度输出结构化分析（现状诊断 / 优化建议 / 度量指标）。

    不依赖大模型：框架维度套入企业文本与指标名做针对性提示。

    Returns
    -------
    dict：{framework, name, dimensions, orientation, 现状诊断, 优化建议, 度量指标}
    """
    fw = MARKETING_FRAMEWORKS.get(framework_key)
    if not fw:
        return {}
    numbers = numbers or {}

    # 维度级现状提示：若指标名命中该维度关键词，给出更具体的提示
    dim_notes = []
    for dim in fw.dimensions:
        dim_notes.append(dim)

    # 度量指标：与框架导向相关的可跟踪指标
    metrics_map = {
        "4P": ["产品满意度", "价格竞争力", "渠道覆盖率", "促销 ROI"],
        "4C": ["消费者满意度", "获客成本(CAC)", "购买便利评分", "互动沟通频次"],
        "4S": ["满意度 NPS", "服务响应时长", "复购率", "客户流失率"],
        "4R": ["客户关联度", "需求响应速度", "客户生命周期价值(LTV)", "ROI"],
        "4V": ["差异化认知度", "功能组合满意度", "品牌附加价值", "价值共鸣指数"],
        "4I": ["内容趣味度", "利益点覆盖率", "互动率", "个性化触达率"],
    }

    return {
        "framework": fw.key,
        "name": fw.name,
        "dimensions": fw.dimensions,
        "orientation": fw.orientation,
        "现状诊断": f"建议从 {fw.name}（{fw.orientation}）的 { '、'.join(fw.dimensions) } 四个维度审视当前营销：{fw.angle}",
        "优化建议": f"针对最薄弱维度重点突破，{fw.angle}",
        "度量指标": metrics_map.get(fw.key, []),
        "_dim_notes": dim_notes,
    }


# ──────────────────────────────────────────────
# 二、19 个经典商业分析工具（SKILL-02）
# ──────────────────────────────────────────────

@dataclass
class BusinessTool:
    name: str
    scenario: str                       # 适用场景
    applicable_problems: list[str]      # 对应的问题类型（用于 recommend_tools）
    interpretation: str = ""           # 工具解读（一句话）


BUSINESS_TOOLS: dict[str, BusinessTool] = {
    "二八法则": BusinessTool("二八法则", "资源分配、客户管理、效率优化",
        ["资源分配", "效率优化"], "抓关键人员/客户/项目，聚焦核心资源。"),
    "现代策划": BusinessTool("现代策划", "方案制定、项目规划",
        ["方案制定", "项目落地"], "基于调查与创意的科学可行性方案，重可操作性。"),
    "USP理论": BusinessTool("USP理论", "广告创意、品牌定位",
        ["品牌定位", "广告创意"], "向消费者提出一个独具、有力、能吸引人的销售主张。"),
    "SWOT分析法": BusinessTool("SWOT分析法", "战略规划、竞争分析",
        ["战略规划", "竞争分析"], "从优势/劣势/机会/威胁系统匹配对策。"),
    "5W2H法": BusinessTool("5W2H法", "任务拆解、方案落地",
        ["方案制定", "项目落地"], "从 Why/What/Where/When/Who/How/How much 条理化推进。"),
    "马太效应": BusinessTool("马太效应", "竞争格局、资源分配",
        ["资源分配", "竞争分析"], "强者恒强，赢家通吃，需建立积累优势。"),
    "马斯洛需求理论": BusinessTool("马斯洛需求理论", "消费者洞察、产品设计",
        ["消费者洞察", "产品设计"], "把握人类需求五层次，更好服务营销。"),
    "波特竞争理论": BusinessTool("波特竞争理论", "竞争战略、市场定位",
        ["战略规划", "竞争分析", "市场定位"], "低成本 / 差异化 / 聚焦 三种通用战略。"),
    "蓝海战略": BusinessTool("蓝海战略", "市场创新、避免红海",
        ["战略规划", "市场创新"], "开创全新市场，差异化获得更快增长与更高利润。"),
    "长尾理论": BusinessTool("长尾理论", "互联网商业、品类管理",
        ["营销组合", "品类管理"], "众多小市场汇聚成可与主流匹敌的能量。"),
    "定位理论": BusinessTool("定位理论", "品牌定位、心智争夺",
        ["品牌定位", "广告创意"], "在潜在顾客心智中确定适当位置，攻心为上。"),
    "品牌形象论": BusinessTool("品牌形象论", "品牌建设、广告策略",
        ["品牌定位", "品牌建设"], "广告维护高知名度品牌形象，重长期投资。"),
    "木桶理论": BusinessTool("木桶理论", "团队管理、短板分析",
        ["团队管理", "短板分析"], "决定战斗力的是最短木板，补长短板。"),
    "羊群效应": BusinessTool("羊群效应", "市场行为、消费者心理",
        ["竞争格局", "消费者心理"], "竞争激烈行业模仿领头羊，需差异化突围。"),
    "4P理论": BusinessTool("4P理论", "营销组合、产品策略",
        ["营销组合", "渠道策略"], "产品/价格/渠道/促销自上而下的企业立场组合。"),
    "4C理论": BusinessTool("4C理论", "消费者导向、营销策略",
        ["消费者洞察", "营销组合"], "需求/成本/便利/沟通，以消费者为中心。"),
    "果子效应": BusinessTool("果子效应", "品牌延伸、信任建设",
        ["品牌延伸", "信任建设"], "利用原品牌影响力统领市场，实现品牌延伸。"),
    "魏斯曼竞争战略": BusinessTool("魏斯曼竞争战略", "市场角色定位",
        ["竞争分析", "市场定位"], "按市场地位分领导者/挑战者/追随者/利基者。"),
    "CI系统": BusinessTool("CI系统", "企业/品牌形象建设",
        ["品牌建设", "品牌定位"], "MI/VI/BI 三大识别系统塑造标准化品牌形象。"),
}

# 问题类型 → 推荐工具（SKILL-02「诊断流程 第一步」）
_PROBLEM_TOOLS: dict[str, list[str]] = {
    "资源分配": ["二八法则", "马太效应"],
    "效率优化": ["二八法则", "马太效应"],
    "战略规划": ["SWOT分析法", "波特竞争理论", "蓝海战略", "魏斯曼竞争战略"],
    "竞争分析": ["SWOT分析法", "波特竞争理论", "蓝海战略", "魏斯曼竞争战略", "羊群效应"],
    "方案制定": ["现代策划", "5W2H法"],
    "项目落地": ["现代策划", "5W2H法"],
    "品牌定位": ["USP理论", "定位理论", "品牌形象论", "CI系统"],
    "广告创意": ["USP理论", "定位理论", "品牌形象论"],
    "消费者洞察": ["马斯洛需求理论", "4C理论"],
    "产品设计": ["马斯洛需求理论", "4C理论"],
    "营销组合": ["4P理论", "4C理论", "长尾理论"],
    "渠道策略": ["4P理论", "4C理论", "长尾理论"],
    "团队管理": ["木桶理论", "羊群效应"],
    "短板分析": ["木桶理论"],
    "消费者心理": ["羊群效应", "马斯洛需求理论"],
    "市场定位": ["波特竞争理论", "魏斯曼竞争战略", "定位理论"],
    "市场创新": ["蓝海战略"],
    "品类管理": ["长尾理论"],
    "品牌建设": ["品牌形象论", "CI系统", "果子效应"],
    "品牌延伸": ["果子效应"],
    "信任建设": ["果子效应", "CI系统"],
}


def recommend_tools(problem_type: str) -> list[str]:
    """根据问题类型推荐经典分析工具。

    Parameters
    ----------
    problem_type : str
        问题类型描述（如「品牌定位」「资源分配」「战略规划」）。

    Returns
    -------
    list[str]：推荐工具名；无法归类时返回通用工具。
    """
    pt = (problem_type or "").strip()
    if not pt:
        return ["SWOT分析法", "二八法则"]
    # 直接命中
    for key, tools in _PROBLEM_TOOLS.items():
        if key in pt:
            return tools
    # 关键词模糊匹配
    for key, tools in _PROBLEM_TOOLS.items():
        if any(seg in pt for seg in key):
            return tools
    return ["SWOT分析法", "二八法则"]


# ──────────────────────────────────────────────
# 三、编排：基于企业信息产出理论分析
# ──────────────────────────────────────────────

def _derive_signals_text(profile, numbers: Optional[dict] = None) -> str:
    """把 profile 文本与指标名拼成可匹配信号的长文本。"""
    parts: list[str] = []
    try:
        parts.append(profile.to_prompt_context() if hasattr(profile, "to_prompt_context") else str(profile))
    except Exception:
        parts.append(str(profile))
    if numbers:
        parts.append(" ".join(str(k) for k in numbers.keys()))
    return " ".join(parts)


def analyze_profile_theory(profile, numbers: Optional[dict] = None) -> dict:
    """对一家企业产出离线理论分析。

    Returns
    -------
    dict：{
        frameworks: list[str],                       # 适用的营销框架 key
        framework_analysis: dict[key, dict],         # 各框架的结构化分析
        recommended_tools: list[str],                # 推荐的商业分析工具
    }
    """
    numbers = numbers or {}
    text = _derive_signals_text(profile, numbers)
    frameworks = select_frameworks(text)

    framework_analysis = {}
    for fw in frameworks:
        framework_analysis[fw] = apply_framework(fw, profile_text=text, numbers=numbers)

    # 推荐工具：由最大痛点推断问题类型，否则给通用组合
    pain = getattr(profile, "biggest_pain", "") or ""
    industry = getattr(profile, "industry", "") or ""
    problem_type = pain or industry or "战略规划"
    recommended_tools = recommend_tools(problem_type)

    return {
        "frameworks": frameworks,
        "framework_analysis": framework_analysis,
        "recommended_tools": recommended_tools,
    }
