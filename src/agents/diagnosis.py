"""
诊断 Agent — 模块1
参考开发思路文档：第4.1节

功能：输入企业信息 → 调用 LLM → 输出诊断报告（含评分+问题+策略方向）
和策略规划合并到一个 Prompt 中完成，不需要两次调用。

支持行业专属 Prompt 模板：
- 地产行业使用 diagnosis/real_estate.txt（6维度评分框架）
- 其他行业使用 diagnosis/system.txt（通用5维度评分框架）

本地规则引擎 fallback：
- 当 API Key 未配置时，自动使用规则引擎生成诊断报告
- 确保无 API Key 环境下也能完整跑通诊断流程

输入：BusinessProfile
输出：DiagnosisReport
"""

import json
import logging

from src.config.settings import llm_config
from src.models.business import BusinessProfile
from src.models.diagnosis import DiagnosisReport
from src.prompts.loader import load_prompt_with_skill
from src.services.llm import get_llm_provider


logger = logging.getLogger(__name__)

# 行业专属 Prompt 模板映射
INDUSTRY_PROMPT_MAP = {
    "地产": "diagnosis/real_estate.txt",
    "房地产": "diagnosis/real_estate.txt",
    "房产": "diagnosis/real_estate.txt",
    "房产中介": "diagnosis/real_estate.txt",
    "房产经纪": "diagnosis/real_estate.txt",
    "中介": "diagnosis/real_estate.txt",
    "二手房中介": "diagnosis/real_estate.txt",
    "新房代理": "diagnosis/real_estate.txt",
    "商铺租赁": "diagnosis/real_estate.txt",
    "地产经纪": "diagnosis/real_estate.txt",
    "置业顾问": "diagnosis/real_estate.txt",
}


class DiagnosisAgent:
    """
    诊断 Agent

    职责：
    1. 根据行业选择合适的 Prompt 模板
    2. 注入企业信息上下文和行业技能
    3. 调用 LLM 生成诊断报告
    4. 解析 JSON 响应为 DiagnosisReport

    设计原则（参考文档 4.1）：
    - 诊断和策略在一个 Prompt 中完成
    - 地产行业使用专属 6 维度评分框架
    - 输出既让老板"有感觉"（评分、问题），也给执行引擎"有信息"（策略方向）
    """

    def __init__(self):
        self.llm = get_llm_provider()
        self.default_template = "diagnosis/system.txt"
        self._use_local = not llm_config.text_api_key

    def _select_template(self, industry: str) -> str:
        """根据行业选择 Prompt 模板"""
        if industry in INDUSTRY_PROMPT_MAP:
            template = INDUSTRY_PROMPT_MAP[industry]
            logger.info("使用行业专属模板: %s → %s", industry, template)
            return template
        return self.default_template

    def _can_use_llm(self) -> bool:
        """检查是否可以使用 LLM"""
        return bool(llm_config.text_api_key)

    async def run(self, profile: BusinessProfile) -> DiagnosisReport:
        """
        执行诊断

        Args:
            profile: 企业信息

        Returns:
            DiagnosisReport: 诊断报告

        Raises:
            ValueError: LLM 返回的 JSON 无法解析
        """
        logger.info(
            "DiagnosisAgent.start | business=%s | industry=%s | mode=%s",
            profile.business_name, profile.industry,
            "llm" if self._can_use_llm() else "local"
        )

        # 无 API Key 时，使用本地规则引擎
        if not self._can_use_llm():
            logger.info("DiagnosisAgent 使用本地规则引擎（无 API Key）")
            return self._run_local_diagnosis(profile)

        # Step 1: 根据行业选择模板并加载渲染（含行业技能注入）
        template = self._select_template(profile.industry)
        business_context = profile.to_prompt_context()
        system_prompt = load_prompt_with_skill(
            template,
            industry=profile.industry,
            business_context=business_context,
        )

        logger.info(
            "DiagnosisAgent.prompt_loaded | template=%s | industry=%s | prompt_length=%d",
            template, profile.industry, len(system_prompt)
        )

        # Step 2: 调用 LLM
        user_message = f"请为以下{profile.industry}企业生成营销诊断报告：\n\n{business_context}"

        try:
            raw_response = await self.llm.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                json_mode=True,
            )

            # Step 3: 解析 JSON
            data = self._parse_response(raw_response)

            # Step 4: 构造诊断报告
            report = DiagnosisReport.from_ai_response(
                business_id=profile.id,
                data=data,
            )

            logger.info(
                "DiagnosisAgent.done | score=%d | strategy=%s",
                report.overall_score,
                report.strategy_summary[:50] if report.strategy_summary else "(empty)"
            )

            return report

        except Exception as e:
            logger.warning(
                "DiagnosisAgent LLM 调用失败，降级到本地规则引擎: %s", e
            )
            return self._run_local_diagnosis(profile)

    def _run_local_diagnosis(self, profile: BusinessProfile) -> DiagnosisReport:
        """本地规则引擎诊断（无 LLM fallback）"""
        from src.services.rule_based_diagnosis import RuleBasedDiagnosis

        generator = RuleBasedDiagnosis()
        report = generator.generate(profile)

        logger.info(
            "DiagnosisAgent.local_done | score=%d | strategy=%s",
            report.overall_score,
            report.strategy_summary[:50] if report.strategy_summary else "(empty)"
        )

        return report

    def _parse_response(self, raw_response: str) -> dict:
        """解析 LLM 返回的 JSON"""
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.error(
                "DiagnosisAgent.parse_failed | raw_preview=%s",
                raw_response[:200]
            )
            raise ValueError(
                f"诊断 Agent 返回了无法解析的内容，请检查 Prompt。"
                f"原始响应前200字符: {raw_response[:200]}"
            ) from exc

        # 校验必填字段
        required_fields = [
            "overall_score", "score_summary", "score_breakdown",
            "top3_problems", "strategy_summary", "this_week_focus"
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            logger.warning(
                "DiagnosisAgent.missing_fields: %s", missing
            )
            # 不中断，尽量容错

        return data


# 便捷函数
async def run_diagnosis(profile: BusinessProfile) -> DiagnosisReport:
    """便捷函数：运行诊断"""
    agent = DiagnosisAgent()
    return await agent.run(profile)
