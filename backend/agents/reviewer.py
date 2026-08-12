"""
复盘 Agent — 模块3
参考开发思路文档：第4.3节

功能：上传截图/CSV → 多模态解析 → AI对比分析 → 生成复盘报告

处理流程：
1. 图片 → GPT-4o 多模态识别数据
2. CSV  → pandas 解析结构化数据
3. 合并数据 → 对比本周目标 → 生成复盘报告
4. 输出下周3条优化建议（可直接喂给执行引擎）
"""

import json
import logging

from backend.models.execution import SevenDayPlan
from backend.models.review import MetricComparison, ReviewReport
from backend.prompts.loader import load_prompt, load_raw_prompt
from backend.services.llm import get_llm_provider
from backend.utils.document_parser import (
    ParsedData,
    is_csv_file,
    is_image_file,
    merge_parsed_data,
    parse_csv_file,
)


logger = logging.getLogger(__name__)


class ReviewAgent:
    """
    复盘 Agent

    职责：
    1. 接收上传文件（截图/CSV）
    2. 用多模态模型解析截图中的数字
    3. 用 pandas 解析 CSV 文件
    4. 对比本周目标 vs 实际数据
    5. 生成复盘报告（含下周优化建议）

    数据源：用户自己上传，不依赖平台 API。
    """

    def __init__(self):
        self.llm = get_llm_provider()
        self.parse_prompt = "reviewer/parse_image.txt"
        self.report_prompt = "reviewer/report.txt"

    async def run(
        self,
        plan: SevenDayPlan,
        uploaded_files: list[str],
    ) -> ReviewReport:
        """
        执行复盘全流程

        Args:
            plan: 本周执行计划（包含目标 key_metrics）
            uploaded_files: 上传文件路径列表（截图 + CSV）

        Returns:
            ReviewReport: 复盘报告
        """
        logger.info(
            "ReviewAgent.start | plan_id=%s | files=%d",
            plan.id, len(uploaded_files)
        )

        # Step 1: 分离图片和 CSV
        image_files = [f for f in uploaded_files if is_image_file(f)]
        csv_files = [f for f in uploaded_files if is_csv_file(f)]
        unknown_files = [
            f for f in uploaded_files
            if not is_image_file(f) and not is_csv_file(f)
        ]

        if unknown_files:
            logger.warning("ReviewAgent.unknown_files: %s", unknown_files)

        # Step 2: 解析所有数据源
        parsed_results: list[ParsedData] = []

        # 解析图片（多模态）
        if image_files:
            logger.info("ReviewAgent.parsing_images | count=%d", len(image_files))
            image_data = await self._parse_images(image_files)
            parsed_results.append(image_data)

        # 解析 CSV
        for csv_file in csv_files:
            logger.info("ReviewAgent.parsing_csv | file=%s", csv_file)
            csv_data = parse_csv_file(csv_file)
            parsed_results.append(csv_data)

        if not parsed_results:
            raise ValueError(
                "没有可解析的文件。请上传截图（PNG/JPG）或 CSV 文件。"
            )

        # Step 3: 合并所有数据
        merged_numbers = merge_parsed_data(*parsed_results)
        logger.info(
            "ReviewAgent.merged | metrics=%s",
            list(merged_numbers.keys())
        )

        # Step 4: 生成复盘报告（LLM 失败时用本地规则兜底）
        try:
            report = await self._generate_report(
                plan=plan,
                numbers=merged_numbers,
            )
        except Exception as e:
            logger.warning("ReviewAgent LLM 生成失败，降级到本地规则报告: %s", e)
            report = self._fallback_report(plan=plan, numbers=merged_numbers)

        logger.info(
            "ReviewAgent.done | summary=%s | suggestions=%d",
            report.summary[:50], len(report.suggestions)
        )

        return report

    async def _parse_images(self, image_paths: list[str]) -> ParsedData:
        """
        用多模态模型解析截图中的数字

        Args:
            image_paths: 截图文件路径列表

        Returns:
            ParsedData: 解析后的数据
        """
        # 加载解析 Prompt
        system_prompt = load_raw_prompt(self.parse_prompt)

        try:
            raw_response = await self.llm.chat_with_images(
                system_prompt=system_prompt,
                image_paths=image_paths,
            )
        except Exception as e:
            logger.error("ReviewAgent.vision_failed: %s", e)
            return ParsedData(
                source_type="image",
                errors=[f"多模态解析失败: {e}"]
            )

        # 解析 JSON
        try:
            data = json.loads(raw_response)
            numbers = data.get("numbers", {})
        except json.JSONDecodeError:
            logger.warning("ReviewAgent.parse_image_json_failed, using raw text")
            numbers = {}
            # 尝试从非 JSON 响应中提取数字
            extracted = self._extract_numbers_from_text(raw_response)
            numbers.update(extracted)

        return ParsedData(
            numbers=numbers,
            raw_text=raw_response,
            source_type="image",
        )

    async def _generate_report(
        self,
        plan: SevenDayPlan,
        numbers: dict,
    ) -> ReviewReport:
        """
        调用 LLM 生成复盘报告

        Args:
            plan: 本周执行计划
            numbers: 从截图/CSV 中提取的数据

        Returns:
            ReviewReport: 复盘报告
        """
        # 加载报告生成 Prompt
        system_prompt = load_prompt(
            self.report_prompt,
            goals_context=self._format_goals(plan),
            numbers_context=json.dumps(numbers, ensure_ascii=False, indent=2),
        )

        user_message = (
            f"本周目标：{json.dumps(plan.key_metrics, ensure_ascii=False)}\n"
            f"实际数据：{json.dumps(numbers, ensure_ascii=False, indent=2)}\n\n"
            f"请生成复盘报告。"
        )

        raw_response = await self.llm.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            json_mode=True,
        )

        # 解析
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.error("ReviewAgent.report_parse_failed")
            raise ValueError(
                f"复盘报告生成失败，无法解析 JSON。"
                f"原始响应: {raw_response[:300]}"
            ) from exc

        # 合并解析出的数字到报告数据中
        data["numbers"] = numbers

        # 构造报告
        report = ReviewReport.from_ai_response(
            plan_id=plan.id,
            business_id=plan.business_id,
            data=data,
        )

        return report

    def _fallback_report(self, plan: SevenDayPlan, numbers: dict) -> ReviewReport:
        """无 LLM / LLM 失败时：本地规则生成基础复盘报告"""
        from backend.models.review import ReviewReport

        vs_target_list = []
        target = plan.key_metrics or {}

        for key, t_val in target.items():
            actual = numbers.get(key, 0)
            try:
                t_num = float(t_val) if t_val is not None else 0.0
            except (TypeError, ValueError):
                t_num = 0.0
            try:
                a_num = float(actual) if actual is not None else 0.0
            except (TypeError, ValueError):
                a_num = 0.0

            ratio = (a_num / t_num * 100) if t_num > 0 else (0.0 if a_num == 0 else 999.0)
            achieved = ratio >= 100
            vs_target_list.append(MetricComparison(
                metric_name=str(key),
                target=t_num,
                actual=a_num,
                achieved=achieved,
            ))

        # 总结
        completed_count = sum(1 for x in vs_target_list if x.achieved)
        total_count = max(1, len(vs_target_list))
        overall_rate = (
            sum((x.actual / x.target * 100) if x.target > 0 else 0 for x in vs_target_list)
            / total_count
        )

        what_worked = [
            f"{v.metric_name}达成（目标 {v.target}，实际 {v.actual}）"
            for v in vs_target_list if v.achieved
        ]
        if not what_worked:
            what_worked = ["本周按计划完成了7天每日任务的执行，具备稳定执行力"]

        what_didnt = [
            f"{v.metric_name}未达成（目标 {v.target}，实际 {v.actual}，差距 {round(v.target - v.actual, 1)}）"
            for v in vs_target_list if not v.achieved
        ]
        if not what_didnt:
            what_didnt = ["数据记录不完整，部分关键指标未能量化回溯，下周需完善每日记录机制"]

        suggestions = []
        for v in vs_target_list:
            if not v.achieved:
                suggestions.append(
                    f"针对 {v.metric_name}：下周目标保持不变，加一条晨间10分钟的 {v.metric_name} 任务前置准备"
                )
        if len(suggestions) < 3:
            suggestions.append("下周继续保持7天节奏，周一先做上周复盘总结（15分钟）再定本周计划")
            suggestions.append("每周三和周六分别做一次期中数据回顾，防止最后一天补数据")

        summary = (
            f"本周总完成率约 {round(overall_rate, 0)}%（{completed_count}/{total_count} 项达标），"
            + (f"重点优势在：{what_worked[0]}；" if what_worked else "")
            + (f"薄弱项为：{what_didnt[0]}" if what_didnt else "整体达标，可适度加量挑战")
        )

        return ReviewReport(
            id="",
            plan_id=plan.id,
            business_id=plan.business_id or "",
            summary=summary,
            numbers=numbers,
            vs_target=vs_target_list,
            what_worked=what_worked,
            what_didnt=what_didnt,
            suggestions=suggestions,
        )

    def _format_goals(self, plan: SevenDayPlan) -> str:
        """格式化本周目标为 Prompt 文本"""
        lines = ["本周目标："]
        for goal in plan.goals:
            lines.append(f"- {goal}")
        lines.append("")
        lines.append("关键指标目标：")
        for key, val in plan.key_metrics.items():
            lines.append(f"- {key}: {val}")
        return "\n".join(lines)

    @staticmethod
    def _extract_numbers_from_text(text: str) -> dict:
        """
        从非结构化文本中尝试提取数字
        简单实现：找 "数字 + 指标名" 的模式
        """
        import re
        numbers = {}
        # 中文数字提取：如 "新增客户 12 人"
        patterns = [
            (r'新增客户[：:\s]*(\d+)', '新增客户'),
            (r'咨询[量数][：:\s]*(\d+)', '咨询量'),
            (r'成交[量数][：:\s]*(\d+)', '成交量'),
            (r'播放[量数][：:\s]*(\d+)', '播放量'),
        ]
        for pattern, name in patterns:
            match = re.search(pattern, text)
            if match:
                numbers[name] = int(match.group(1))
        return numbers


# 便捷函数
async def run_review(
    plan: SevenDayPlan,
    uploaded_files: list[str],
) -> ReviewReport:
    """便捷函数：执行复盘"""
    agent = ReviewAgent()
    return await agent.run(plan, uploaded_files)
