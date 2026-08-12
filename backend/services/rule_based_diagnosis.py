"""
本地规则引擎 — 无 LLM 模式下的诊断报告生成
当 API Key 未配置或 LLM 调用失败时，作为 fallback 方案

设计思路：
1. 基于行业诊断标准（diagnosis_criteria.md）进行维度评分
2. 根据企业信息字段的完整度和关键词进行规则打分
3. 结合行业指标基准（metrics.md）生成问题列表
4. 使用行业获客策略（channels.md）生成建议

参考：backend/skills/real_estate/ 下的诊断标准和指标基准
"""

import logging
import re

from backend.models.business import BusinessProfile
from backend.models.diagnosis import DiagnosisReport, Problem


logger = logging.getLogger(__name__)


def diagnose(profile: BusinessProfile) -> DiagnosisReport:
    """兼容入口：生成规则引擎诊断报告。"""
    return RuleBasedDiagnosis().generate(profile)


# ── 地产行业诊断维度（6维度）──
REAL_ESTATE_DIMENSIONS = [
    {"key": "房源获取", "weight": 0.25},
    {"key": "带看转化", "weight": 0.20},
    {"key": "社区渗透", "weight": 0.20},
    {"key": "线上获客", "weight": 0.15},
    {"key": "专业形象", "weight": 0.10},
    {"key": "数据运营", "weight": 0.10},
]

# ── 通用行业诊断维度（5维度）──
GENERIC_DIMENSIONS = [
    {"key": "定位", "weight": 0.20},
    {"key": "产品", "weight": 0.20},
    {"key": "渠道", "weight": 0.25},
    {"key": "内容", "weight": 0.15},
    {"key": "转化", "weight": 0.20},
]

# ── 关键词 → 维度映射（用于 biggest_pain 分析）──
PAIN_KEYWORD_MAP = {
    # 地产行业
    "real_estate": {
        "房源获取": ["房源", "独家", "业主", "委托", "盘源", "客源"],
        "带看转化": ["带看", "转化", "成交", "客户跟进", "逼单"],
        "社区渗透": ["社区", "业主群", "转介绍", "老客户", "口碑"],
        "线上获客": ["短视频", "抖音", "小红书", "线上", "引流", "朋友圈", "私域"],
        "专业形象": ["专业", "口碑", "形象", "信任", "纠纷"],
        "数据运营": ["数据", "客户管理", "复盘", "指标", "报表"],
    },
    # 通用
    "generic": {
        "定位": ["定位", "客户", "目标", "精准", "市场"],
        "产品": ["产品", "服务", "质量", "价格", "性价比"],
        "渠道": ["渠道", "获客", "引流", "流量", "推广"],
        "内容": ["内容", "文案", "短视频", "宣传", "品牌"],
        "转化": ["转化", "成交", "客户跟进", "复购", "留存"],
    },
}

# ── 渠道关键词 → 线上/线下判断 ──
ONLINE_CHANNEL_KEYWORDS = [
    "短视频", "抖音", "视频号", "小红书", "公众号", "朋友圈",
    "私域", "直播", "58同城", "安居客", "大众点评", "本地生活",
    "线上", "互联网", "电商", "社群",
]

# ── 地产行业标准建议模板 ──
REAL_ESTATE_SUGGESTIONS = {
    "房源获取": [
        "建立老业主回访机制，每周联系5位老业主获取委托",
        "打造业主群，提供小区市场分析等增值服务",
        "每周至少新增10套独家房源，目标占比30%以上",
    ],
    "带看转化": [
        "带看前必须做客户需求分析，填写带看准备表",
        "带看后2小时内跟进，发送房源对比资料",
        "每周复盘带看成功率，目标提升到8%以上",
    ],
    "社区渗透": [
        "维护3-5个服务小区的业主群，每周提供2次价值信息",
        "每月组织1次社区活动（如房产知识沙龙）",
        "建立老客户转介绍激励机制（成功推荐送家电）",
    ],
    "线上获客": [
        "每周发布3-5条短视频（实景看房+区域分析）",
        "小红书每周2篇购房攻略笔记，建立专业人设",
        "朋友圈每日3-5条内容，打造专业+有温度的人设",
    ],
    "专业形象": [
        "每周学习最新政策和税费知识，参加1次行业培训",
        "建立客户信任体系，提供方案对比和价值呈现",
        "主动处理客户纠纷，维护好口碑评价",
    ],
    "数据运营": [
        "使用客户管理系统（如房友、好房通）管理客户信息",
        "每周复盘带看量、成交量、转化率等关键指标",
        "建立团队业绩跟踪和激励机制",
    ],
}

# ── 通用行业建议模板 ──
GENERIC_SUGGESTIONS = {
    "定位": [
        "明确目标客户画像，聚焦1-2个核心客群",
        "分析竞争对手，找到差异化定位",
        "细化市场细分，避免盲目扩张",
    ],
    "产品": [
        "梳理产品/服务的核心卖点",
        "收集客户反馈，持续优化产品",
        "建立产品对比优势，做价值呈现",
    ],
    "渠道": [
        "选择1-2个核心获客渠道，先跑通再扩展",
        "建立线上线下结合的获客体系",
        "跟踪各渠道投入产出比，优化投放",
    ],
    "内容": [
        "持续输出有价值的内容，建立专业形象",
        "制作产品/服务的展示物料",
        "建立内容SOP，确保稳定输出频率",
    ],
    "转化": [
        "建立客户跟进SOP，提升转化率",
        "设计转化激励方案（限时优惠、赠品等）",
        "重视老客户复购和转介绍",
    ],
}


class RuleBasedDiagnosis:
    """
    本地规则引擎诊断生成器

    功能：根据企业信息字段，通过规则匹配生成诊断报告
    优势：无需 LLM API，即时生成，隐私安全
    限制：报告质量和个性化程度有限
    """

    def __init__(self):
        self.is_real_estate = False

    def generate(self, profile: BusinessProfile) -> DiagnosisReport:
        """
        生成本地诊断报告

        Args:
            profile: 企业信息

        Returns:
            DiagnosisReport: 诊断报告（规则引擎生成）
        """
        self.is_real_estate = self._is_real_estate_industry(profile.industry)

        dimensions = (
            REAL_ESTATE_DIMENSIONS if self.is_real_estate else GENERIC_DIMENSIONS
        )

        # Step 1: 计算各维度评分
        scores = self._calculate_scores(profile, dimensions)

        # Step 2: 生成 Top3 问题
        top3_problems = self._identify_problems(profile, scores, dimensions)

        # Step 3: 生成策略方向
        strategy_summary = self._generate_strategy(profile, scores, top3_problems)

        # Step 4: 生成本周重点
        this_week_focus = self._generate_weekly_focus(profile, top3_problems)

        # Step 5: 计算总分和评分理由
        overall_score = self._calculate_overall_score(scores, dimensions)
        score_summary = self._generate_score_summary(overall_score, profile)

        report = DiagnosisReport(
            business_id=profile.id,
            overall_score=overall_score,
            score_summary=score_summary,
            score_breakdown=scores,
            top3_problems=top3_problems,
            strategy_summary=strategy_summary,
            this_week_focus=this_week_focus,
        )

        logger.info(
            "规则引擎诊断完成 | business=%s | score=%d | is_real_estate=%s",
            profile.business_name,
            overall_score,
            self.is_real_estate,
        )

        return report

    def _is_real_estate_industry(self, industry: str) -> bool:
        """判断是否为地产行业。"""
        real_estate_keywords = [
            "地产", "房产", "中介", "经纪", "置业", "商铺",
            "二手房", "新房", "房地产", "物业",
        ]
        return any(keyword in industry for keyword in real_estate_keywords)

    def _calculate_scores(
        self, profile: BusinessProfile, dimensions: list
    ) -> dict:
        """
        计算各维度评分

        评分逻辑：
        1. 基础分 60（有填写基本信息）
        2. 根据字段完整度加分
        3. 根据渠道信息评分
        4. 根据痛点关键词扣分
        """
        scores = {}
        pain_text = f"{profile.biggest_pain} {profile.current_channels}"

        for dim in dimensions:
            key = dim["key"]
            score = 60  # 基础分

            # 根据渠道信息评分
            score = self._score_by_channel(profile, key, score)

            # 根据字段完整度加分
            score = self._score_by_completeness(profile, key, score)

            # 根据痛点关键词扣分
            score = self._score_by_pain_analysis(pain_text, key, score)

            # 根据团队规模调整
            score = self._score_by_team_size(profile, key, score)

            # 限制在 0-100
            scores[key] = max(20, min(95, score))

        return scores

    def _score_by_channel(
        self, profile: BusinessProfile, dimension: str, base_score: int
    ) -> int:
        """根据渠道信息评分"""
        channels = profile.current_channels.lower() if profile.current_channels else ""

        if not channels:
            return base_score - 10  # 无渠道信息，扣分

        # 地产行业：线上获客维度检测
        if self.is_real_estate and dimension == "线上获客":
            has_online = any(kw in channels for kw in ONLINE_CHANNEL_KEYWORDS)
            if has_online:
                base_score += 15
                if "短视频" in channels or "抖音" in channels:
                    base_score += 10
            else:
                base_score -= 15  # 只有传统渠道，扣分

        # 地产行业：社区渗透维度检测
        if self.is_real_estate and dimension == "社区渗透":
            community_keywords = ["业主群", "社区", "物业", "老客户", "转介绍"]
            has_community = any(kw in channels for kw in community_keywords)
            if has_community:
                base_score += 20

        # 通用行业：渠道维度检测
        if not self.is_real_estate and dimension == "渠道":
            has_online = any(kw in channels for kw in ONLINE_CHANNEL_KEYWORDS)
            if has_online:
                base_score += 10
            if "线下" in channels or "门店" in channels:
                base_score += 5

        return base_score

    def _score_by_completeness(
        self, profile: BusinessProfile, dimension: str, base_score: int
    ) -> int:
        """根据字段完整度加分"""
        filled_fields = 0
        total_fields = 6

        if profile.product_desc:
            filled_fields += 1
        if profile.target_customers:
            filled_fields += 1
        if profile.competitors:
            filled_fields += 1
        if profile.current_channels:
            filled_fields += 1
        if profile.monthly_revenue:
            filled_fields += 1
        if profile.biggest_pain:
            filled_fields += 1

        # 每填一个字段加3分
        completeness_bonus = (filled_fields / total_fields) * 15

        # 目标客户描述详细度
        if len(profile.target_customers) > 30:
            completeness_bonus += 5

        return base_score + int(completeness_bonus)

    def _score_by_pain_analysis(
        self, pain_text: str, dimension: str, base_score: int
    ) -> int:
        """根据痛点关键词扣分"""
        keyword_map = (
            PAIN_KEYWORD_MAP["real_estate"]
            if self.is_real_estate
            else PAIN_KEYWORD_MAP["generic"]
        )

        keywords = keyword_map.get(dimension, [])
        matched = sum(1 for kw in keywords if kw in pain_text)

        if matched >= 2:
            base_score -= 15  # 多个痛点关键词，扣分
        elif matched == 1:
            base_score -= 5

        return base_score

    def _score_by_team_size(
        self, profile: BusinessProfile, dimension: str, base_score: int
    ) -> int:
        """根据团队规模调整评分"""
        team_size = profile.team_size

        if not team_size:
            return base_score

        # 解析团队规模
        numbers = re.findall(r"\d+", team_size)
        if not numbers:
            return base_score

        try:
            size = int(numbers[0])
            # 小团队（1-3人）可能在数据运营、专业形象方面扣分
            if size <= 3 and dimension in ["数据运营", "专业形象", "定位"]:
                base_score -= 5
            # 中大团队在社区渗透、带看转化方面有优势
            if size >= 5 and dimension in ["社区渗透", "带看转化"]:
                base_score += 5
        except (ValueError, IndexError):
            pass

        return base_score

    def _identify_problems(
        self, profile: BusinessProfile, scores: dict, dimensions: list
    ) -> list:
        """
        识别 Top3 问题

        逻辑：
        1. 找出得分最低的 3 个维度
        2. 结合痛点关键词生成具体问题描述
        3. 提供 quick_fix（7天内能做的事）
        """
        # 按得分排序，找出问题维度
        sorted_dims = sorted(
            dimensions, key=lambda d: scores.get(d["key"], 50)
        )

        problems = []
        for _i, dim in enumerate(sorted_dims[:3]):
            key = dim["key"]
            score = scores.get(key, 50)
            severity = self._get_severity(score)

            description = self._generate_problem_description(
                key, score, profile
            )
            quick_fix = self._generate_quick_fix(key, score, profile)

            problems.append(
                Problem(
                    severity=severity,
                    category=key,
                    description=description,
                    quick_fix=quick_fix,
                )
            )

        return problems

    def _get_severity(self, score: int) -> str:
        """根据分数确定严重程度"""
        if score < 40:
            return "critical"
        elif score < 60:
            return "major"
        else:
            return "minor"

    def _generate_problem_description(
        self, dimension: str, score: int, profile: BusinessProfile
    ) -> str:
        """生成问题描述。"""
        # 通用问题模板
        pain_templates = {
            # 地产行业
            "房源获取": [
                f"独家房源获取能力待加强（当前评分{score}分），建议建立系统化的业主委托机制",
                f"房源信息管理不够完善（{score}分），可能存在更新不及时或信息不完整的问题",
                f"业主关系维护深度不足（{score}分），转介绍占比可能低于行业平均20%",
            ],
            "带看转化": [
                f"带看转化效率有提升空间（{score}分），带看后跟进机制可能不够及时",
                f"客户需求匹配精准度待优化（{score}分），可能存在盲目带看的情况",
                f"带看话术和逼单技巧需要加强（{score}分），成交率可能低于行业平均5-8%",
            ],
            "社区渗透": [
                f"社区深耕力度不足（{score}分），业主群覆盖和转介绍机制待建立",
                f"与服务小区的物业/业主关系有待加强（{score}分），可通过提供增值服务切入",
                f"社区活动参与度低（{score}分），建议定期组织房产知识沙龙等活动",
            ],
            "线上获客": [
                f"线上获客能力需要系统性提升（{score}分），建议建立短视频+小红书内容体系",
                f"私域运营深度不够（{score}分），朋友圈和社群缺少持续价值输出",
                f"线上线索转化率偏低（{score}分），需优化内容质量和跟进响应速度",
            ],
            "专业形象": [
                f"专业服务形象有待强化（{score}分），建议加强最新政策和税费知识学习",
                f"客户信任建立需要更系统化的方法（{score}分），可通过方案对比提升专业性",
                f"口碑管理机制不完善（{score}分），需要主动收集和维护客户评价",
            ],
            "数据运营": [
                f"数据化管理水平待提升（{score}分），建议引入客户管理系统",
                f"关键指标监控不够系统（{score}分），缺乏定期复盘机制",
                f"团队业绩跟踪和激励机制不完善（{score}分），可能存在凭感觉管理的情况",
            ],
            # 通用行业
            "定位": [
                f"市场定位不够聚焦（{score}分），建议明确1-2个核心客群",
                f"目标客户画像不够清晰（{score}分），需深化客户需求洞察",
                f"差异化优势不明显（{score}分），需要找到独特的价值主张",
            ],
            "产品": [
                f"产品/服务的核心卖点不够突出（{score}分），建议梳理价值体系",
                f"客户反馈收集和产品优化机制待建立（{score}分）",
                f"产品对比优势呈现不足（{score}分），需要更好地展示差异化",
            ],
            "渠道": [
                f"获客渠道需要优化（{score}分），建议聚焦1-2个核心渠道",
                f"渠道投入产出比缺乏追踪（{score}分），可能存在盲目投放",
                f"线上线下渠道结合度不够（{score}分），建议建立全链路获客体系",
            ],
            "内容": [
                f"内容输出缺乏系统性（{score}分），建议建立稳定的内容SOP",
                f"内容价值不够突出（{score}分），需要更多有干货的内容",
                f"内容渠道单一（{score}分），可探索短视频、公众号等新渠道",
            ],
            "转化": [
                f"客户转化率有提升空间（{score}分），建议建立标准化跟进SOP",
                f"转化激励机制待完善（{score}分），可设计限时优惠等方案",
                f"老客户复购和转介绍比例偏低（{score}分），需要加强客户关系维护",
            ],
        }

        templates = pain_templates.get(dimension, ["待改进"])
        # 根据得分选择不同严重程度的描述
        if score < 40:
            idx = 0  # 最严重的描述
        elif score < 60:
            idx = 1  # 中等描述
        else:
            idx = 2  # 较轻微描述

        return templates[idx] if idx < len(templates) else templates[-1]

    def _generate_quick_fix(
        self, dimension: str, score: int, profile: BusinessProfile
    ) -> str:
        """生成7天内能做的具体动作"""
        suggestions = (
            REAL_ESTATE_SUGGESTIONS
            if self.is_real_estate
            else GENERIC_SUGGESTIONS
        )

        dim_suggestions = suggestions.get(dimension, [])
        if not dim_suggestions:
            return f"在{dimension}方面制定改进计划，本周开始执行第一步"

        # 选择最紧迫的建议
        severity = self._get_severity(score)
        if severity == "critical":
            return dim_suggestions[0] if len(dim_suggestions) > 0 else f"立即改进{dimension}"
        elif severity == "major":
            return dim_suggestions[1] if len(dim_suggestions) > 1 else dim_suggestions[0]
        else:
            return dim_suggestions[-1] if len(dim_suggestions) > 2 else dim_suggestions[0]

    def _generate_strategy(
        self, profile: BusinessProfile, scores: dict, top3_problems: list
    ) -> str:
        """生成策略方向"""
        if self.is_real_estate:
            return self._generate_real_estate_strategy(profile, scores, top3_problems)
        else:
            return self._generate_generic_strategy(profile, scores, top3_problems)

    def _generate_real_estate_strategy(
        self, profile: BusinessProfile, scores: dict, top3_problems: list
    ) -> str:
        """生成地产行业策略。"""
        # 识别最弱的维度（仅用于直观排序展示，其值不参与后续逻辑）
        weakest = min(scores, key=scores.get)

        # 根据目标客户确定核心策略
        target = profile.target_customers
        if "刚需" in target or "首套" in target:
            customer_type = "刚需首套客户"
        elif "改善" in target or "置换" in target:
            customer_type = "改善置换客户"
        elif "投资" in target or "出租" in target:
            customer_type = "投资客群"
        elif "学区" in target:
            customer_type = "学区房客户"
        else:
            customer_type = "精准客群"

        # 确定核心渠道
        channels = profile.current_channels
        if "短视频" in channels or "抖音" in channels:
            core_channel = "短视频获客"
        elif "小红书" in channels:
            core_channel = "小红书种草"
        elif "业主群" in channels or "社区" in channels:
            core_channel = "社区深耕"
        elif "朋友圈" in channels or "私域" in channels:
            core_channel = "私域运营"
        else:
            core_channel = "线上线下结合"

        # 关键动作
        key_action = self._get_key_action(weakest)

        return f"聚焦{customer_type}，以{core_channel}为核心，重点改善{weakest}能力，本周执行：{key_action}"

    def _generate_generic_strategy(
        self, profile: BusinessProfile, scores: dict, top3_problems: list
    ) -> str:
        """生成通用行业策略"""
        weakest = min(scores, key=scores.get)
        target = profile.target_customers or "目标客户"
        key_action = self._get_key_action(weakest)

        return f"聚焦{target}，以{weakest}为突破口，本周重点执行：{key_action}"

    def _get_key_action(self, dimension: str) -> str:
        """获取关键行动建议"""
        actions = {
            "房源获取": "建立老业主回访机制，每周联系5位老业主",
            "带看转化": "优化带看流程，带看后2小时内跟进",
            "社区渗透": "维护3-5个业主群，每周提供2次价值信息",
            "线上获客": "发布3条短视频+2篇小红书笔记",
            "专业形象": "学习最新政策，参加1次行业培训",
            "数据运营": "引入客户管理系统，建立周复盘机制",
            "定位": "细化目标客户画像，聚焦1-2个核心客群",
            "产品": "梳理产品核心卖点，制作价值对比表",
            "渠道": "聚焦1-2个核心渠道，跟踪投入产出比",
            "内容": "建立内容SOP，保证每周稳定输出",
            "转化": "优化客户跟进流程，设计转化激励方案",
        }
        return actions.get(dimension, f"制定{dimension}改进计划")

    def _generate_weekly_focus(
        self, profile: BusinessProfile, top3_problems: list
    ) -> str:
        """生成本周重点行动"""
        if not top3_problems:
            return "梳理业务现状，制定本周营销执行计划"

        # 选择最严重的问题作为本周重点
        critical = [p for p in top3_problems if p.severity == "critical"]
        target_problem = critical[0] if critical else top3_problems[0]

        return target_problem.quick_fix

    def _calculate_overall_score(
        self, scores: dict, dimensions: list
    ) -> int:
        """计算加权总分"""
        total = 0
        total_weight = 0

        for dim in dimensions:
            key = dim["key"]
            weight = dim["weight"]
            score = scores.get(key, 50)
            total += score * weight
            total_weight += weight

        return int(total / total_weight) if total_weight > 0 else 50

    def _generate_score_summary(
        self, score: int, profile: BusinessProfile
    ) -> str:
        """生成评分理由"""
        if score >= 80:
            return f"{profile.business_name}营销基础扎实，在同行业中处于优秀水平，重点在于持续优化薄弱环节"
        elif score >= 60:
            return f"{profile.business_name}具备较好的营销基础，有明确的改进空间，需要系统性提升薄弱环节"
        elif score >= 40:
            return f"{profile.business_name}营销体系存在明显短板，建议聚焦核心问题进行重点突破"
        else:
            return f"{profile.business_name}亟需系统性提升营销能力，建议从最紧迫的问题开始改进"


def generate_local_diagnosis(profile: BusinessProfile) -> DiagnosisReport:
    """便捷函数：本地规则引擎诊断"""
    generator = RuleBasedDiagnosis()
    return generator.generate(profile)
