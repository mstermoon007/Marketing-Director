"""
执行引擎 Agent — 模块2（核心壁垒）
参考开发思路文档：第4.2节

功能：诊断报告 + 企业信息 → 调用 LLM → 输出7天执行任务清单

翻译逻辑（5步）：
Step 1: 策略分解 → 识别可执行的动作线
Step 2: 子任务生成 → 为每条动作线拆解具体子任务
Step 3: 7天排期 → 按优先级和时间逻辑排布
Step 4: 执行细节 → 每任务附"怎么做"和"完成标准"
Step 5: 目标设定 → 设量化目标，为复盘准备基线

质量验证：
- 每天 ≤5 任务
- 每天总计 ≤120 分钟（2小时）
- 每个任务有 how_to 和 done_criteria
- 7天任务间有递进关系
"""

import json
import logging
from datetime import date as DateType
from typing import Optional

from src.models.business import BusinessProfile
from src.models.diagnosis import DiagnosisReport
from src.models.execution import DayPlan, SevenDayPlan, Task
from src.prompts.loader import load_prompt
from src.services.llm import get_llm_provider


logger = logging.getLogger(__name__)


# 最大重试次数（当约束验证不通过时）
MAX_RETRIES = 2


class ExecutorAgent:
    """
    执行引擎 Agent（核心）

    这是产品的核心壁垒——市面上任何 AI 都能做诊断，
    但没有 AI 能做"把诊断变成每天具体做什么"。

    职责：
    1. 加载 executor/system.txt Prompt 模板
    2. 注入企业信息 + 诊断结论上下文
    3. 调用 LLM 生成 7 天任务清单
    4. 验证约束（任务数、耗时）
    5. 不通过则用反馈修正重试
    """

    def __init__(self):
        self.llm = get_llm_provider()
        self.prompt_template = "executor/system.txt"

    async def run(
        self,
        profile: BusinessProfile,
        diagnosis: DiagnosisReport,
        start_date: Optional[DateType] = None,
    ) -> SevenDayPlan:
        """
        生成7天执行清单

        Args:
            profile: 企业信息
            diagnosis: 诊断报告（关键是 strategy_summary 字段）
            start_date: 本周起始日期，默认今天

        Returns:
            SevenDayPlan: 7天执行计划

        Raises:
            ValueError: 多次重试后仍无法通过约束验证
        """
        if start_date is None:
            start_date = DateType.today()

        logger.info(
            "ExecutorAgent.start | business=%s | strategy=%s",
            profile.business_name,
            diagnosis.strategy_summary[:60] if diagnosis.strategy_summary else "(empty)"
        )

        # Step 1: 渲染 Prompt
        system_prompt = load_prompt(
            self.prompt_template,
            business_context=profile.to_prompt_context(),
            diagnosis_context=self._format_diagnosis_for_prompt(diagnosis),
            start_date=start_date.isoformat(),
        )

        # Step 2: 调用 LLM + 约束验证（最多重试2次）；LLM 失败 fallback 到本地生成
        plan = None
        last_issues: list[str] = []
        try:
            for attempt in range(1 + MAX_RETRIES):
                feedback = ""
                if attempt > 0 and last_issues:
                    feedback = self._format_retry_feedback(last_issues)

                raw_response = await self.llm.chat(
                    system_prompt=system_prompt,
                    user_message=feedback or self._build_user_message(profile, diagnosis),
                    json_mode=True,
                )

                # 解析
                data = self._parse_response(raw_response)

                # 构造
                plan = SevenDayPlan.from_ai_response(
                    diagnosis_id=diagnosis.id,
                    business_id=profile.id,
                    start_date=start_date,
                    data=data,
                )

                # 验证约束
                validation = plan.validate_constraints()
                if validation["valid"]:
                    logger.info(
                        "ExecutorAgent.done | attempts=%d | days=%d | theme=%s",
                        attempt + 1, len(plan.days), plan.theme
                    )
                    return plan

                # 约束不通过，记录问题并重试
                last_issues = validation["issues"]
                logger.warning(
                    "ExecutorAgent.retry | attempt=%d | issues=%s",
                    attempt + 1, last_issues
                )

            # 超过重试次数
            raise ValueError(
                f"执行引擎在 {1 + MAX_RETRIES} 次尝试后仍无法通过约束验证。\n"
                f"最后的问题: {last_issues}\n"
                f"请检查 Prompt 或调整约束条件。"
            )
        except Exception as e:
            logger.warning("ExecutorAgent LLM 调用失败，降级到本地模板生成: %s", e)
            return self._fallback_plan(profile, diagnosis, start_date)

    def _fallback_plan(
        self, profile: BusinessProfile, diagnosis: DiagnosisReport, start_date
    ) -> SevenDayPlan:
        """无 LLM / LLM 失败时的兜底：生成基础 7 天计划"""
        theme = (diagnosis.this_week_focus or f"{profile.industry}营销启动周")[:50]
        goals = [
            diagnosis.this_week_focus or "本周聚焦：核心问题改善",
            "每天至少完成 3 个营销相关动作",
            "汇总本周数据用于周末复盘",
        ]

        # 取 score_breakdown 的最低分 1-2 个维度，作为每日目标
        sorted_dims = sorted(
            (diagnosis.score_breakdown or {}).items(), key=lambda kv: kv[1]
        )
        weak_dims = [d for d, _ in sorted_dims[:2]] or ["营销内容", "获客渠道"]

        # 3 个任务模板，复用 weak_dims
        task_templates = [
            (f"梳理{weak_dims[0]}现状", 30,
             f"整理目前在{weak_dims[0]}方面已做的动作和遇到的问题，形成书面文字",
             "有 300 字以上的书面梳理内容"),
            (f"在{weak_dims[1]}上做一个小动作", 45,
             f"围绕{weak_dims[1]}，在本周确定一个立刻能执行的动作并落地",
             "有实际可追溯的产出（朋友圈/视频/海报/到店沟通话术等）"),
            ("输出今日数据", 10,
             "记录今日新咨询、到店客户、微信新增好友等关键指标",
             "有明确数据记录（哪怕是0也要记下来）"),
        ]

        day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        days = []
        for i, dl in enumerate(day_labels):
            tasks = [
                Task(
                    time_slot="上午" if idx == 0 else ("下午" if idx == 1 else "晚上"),
                    title=t[0],
                    how_to=t[2],
                    done_criteria=t[3],
                    estimated_minutes=t[1],
                    checklist=[t[2]] if t[2] else [],
                )
                for idx, t in enumerate(task_templates)
            ]
            days.append(DayPlan(
                day_label=dl,
                focus=weak_dims[i % len(weak_dims)],
                tasks=tasks,
            ))

        return SevenDayPlan(
            id="",
            diagnosis_id=diagnosis.id,
            business_id=profile.id,
            start_date=start_date,
            theme=theme,
            goals=goals,
            key_metrics={
                "新增客户": 5,
                "咨询量": 5,
                "成交量": 0,
            },
            days=days,
        )

    def _build_user_message(
        self, profile: BusinessProfile, diagnosis: DiagnosisReport
    ) -> str:
        """构建用户消息"""
        return (
            f"企业：{profile.business_name}\n"
            f"行业：{profile.industry}\n"
            f"团队规模：{profile.team_size}\n"
            f"策略方向：{diagnosis.strategy_summary}\n"
            f"本周重点：{diagnosis.this_week_focus}\n\n"
            f"请生成7天执行清单。"
        )

    def _format_diagnosis_for_prompt(self, diagnosis: DiagnosisReport) -> str:
        """将诊断报告格式化为 Prompt 上下文"""
        parts = [
            f"整体评分：{diagnosis.overall_score}/100",
            f"评分理由：{diagnosis.score_summary}",
            f"策略方向：{diagnosis.strategy_summary}",
            f"本周重点：{diagnosis.this_week_focus}",
            "",
            "Top3 问题：",
        ]
        for i, problem in enumerate(diagnosis.top3_problems, 1):
            if isinstance(problem, dict):
                parts.append(
                    f"{i}. [{problem.get('severity', '')}] {problem.get('description', '')}"
                    f" → 建议：{problem.get('quick_fix', '')}"
                )
            else:
                parts.append(
                    f"{i}. [{problem.severity}] {problem.description}"
                    f" → 建议：{problem.quick_fix}"
                )

        return "\n".join(parts)

    def _format_retry_feedback(self, issues: list[str]) -> str:
        """格式化重试时的约束反馈"""
        issue_text = "\n".join(f"- {i}" for i in issues)
        return (
            f"上一次生成的计划没有通过约束检查，请修正以下问题后重新生成：\n\n"
            f"{issue_text}\n\n"
            f"修正要求：\n"
            f"1. 每天不超过5个任务\n"
            f"2. 每天总耗时不超过120分钟（2小时）\n"
            f"3. 确保以上两条硬约束。"
        )

    def _parse_response(self, raw_response: str) -> dict:
        """解析 LLM 返回的 JSON"""
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.error(
                "ExecutorAgent.parse_failed | raw_preview=%s",
                raw_response[:200]
            )
            raise ValueError(
                f"执行引擎返回了无法解析的 JSON。"
                f"原始响应前200字符: {raw_response[:200]}"
            ) from exc


# 便捷函数
async def run_executor(
    profile: BusinessProfile,
    diagnosis: DiagnosisReport,
    start_date: Optional[DateType] = None,
) -> SevenDayPlan:
    """便捷函数：生成7天执行清单"""
    agent = ExecutorAgent()
    return await agent.run(profile, diagnosis, start_date)
