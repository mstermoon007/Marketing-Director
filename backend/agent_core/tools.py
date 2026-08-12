"""
标准化业务工具（Tools）
================================

将后端现有业务能力封装为 6 个标准化工具，供主控 Agent 与子 Agent 调用：

- ``diagnose_business``        ：诊断某企业营销健康度（封装 DiagnosisAgent + 持久化）
- ``generate_plan``            ：生成诊断 + 7 天执行计划（封装 pipeline.run_full_pipeline）
- ``schedule_task``            ：把任务按天分配并生成主动提醒（封装计划拆解 + 排期）
- ``upload_and_parse_data``    ：上传截图/CSV → 解析为结构化数字（封装 document_parser）
- ``calculate_kpi``            ：计算营销指标（达成率/转化率/趋势），纯函数
- ``search_marketing_knowledge``：RAG 检索营销方法卡片（封装 KnowledgeBase）

每个工具都提供：
1. 可直接 await 调用的异步/纯函数实现（子 Agent 内部调用）；
2. 通过 ``get_langchain_tools()`` 暴露为 LangChain ``@tool``，供 LLM 工具调用。

所有工具对「无 LLM Key」环境健壮：诊断/计划会自动降级到本地规则引擎。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select

from backend.agent_core.knowledge import KnowledgeBase
from backend.db.models import (
    AsyncSessionLocal,
    BusinessRecord,
    DiagnosisRecord,
    ExecutionPlanRecord,
    TodoRecord,
)
from backend.models.business import BusinessProfile
from backend.utils.document_parser import (
    ParsedData,
    is_csv_file,
    is_image_file,
    merge_parsed_data,
    parse_csv_file,
)


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 1. diagnose_business
# ──────────────────────────────────────────────
async def diagnose_business(business_id: str) -> dict:
    """诊断某企业营销健康度，返回并持久化诊断报告。"""
    from backend.agents.diagnosis import DiagnosisAgent

    async with AsyncSessionLocal() as session:
        rec = (
            await session.execute(select(BusinessRecord).filter_by(id=business_id))
        ).scalar_one_or_none()
        if not rec:
            return {"ok": False, "error": f"企业不存在：{business_id}"}
        profile = BusinessProfile(
            id=rec.id,
            business_name=rec.business_name,
            industry=rec.industry,
            city=rec.city,
            product_desc=rec.product_desc or "",
            price_range=rec.price_range or "",
            target_customers=rec.target_customers or "",
            competitors=rec.competitors or "",
            current_channels=rec.current_channels or "",
            monthly_revenue=rec.monthly_revenue or "",
            team_size=rec.team_size or "",
            biggest_pain=rec.biggest_pain or "",
        )

    agent = DiagnosisAgent()
    report = await agent.run(profile)

    async with AsyncSessionLocal() as session:
        try:
            d = DiagnosisRecord(
                business_id=business_id,
                overall_score=report.overall_score,
                score_summary=report.score_summary,
                score_breakdown=report.score_breakdown,
                top3_problems=report.to_dict()["top_issues"],
                strategy_summary=report.strategy_summary,
                this_week_focus=report.this_week_focus,
            )
            session.add(d)
            await session.commit()
            await session.refresh(d)
            report.id = d.id
            report.created_at = d.created_at
        except Exception as e:
            logger.error("诊断报告持久化失败：%s", e)
            return {"ok": False, "error": f"持久化失败：{e}"}

    return {"ok": True, "report": report.to_dict()}


# ──────────────────────────────────────────────
# 2. generate_plan
# ──────────────────────────────────────────────
async def generate_plan(business_id: str) -> dict:
    """生成诊断 + 7 天执行计划（完整 pipeline）。"""
    from backend.services.pipeline import run_full_pipeline

    try:
        result = await run_full_pipeline(business_id)
        return {"ok": True, "diagnosis": result["diagnosis"], "plan": result["plan"]}
    except Exception as e:
        logger.error("生成计划失败：%s", e)
        return {"ok": False, "error": str(e)}


# ──────────────────────────────────────────────
# 3. schedule_task（按天分配 + 主动提醒）
# ──────────────────────────────────────────────
_SLOTS = ["上午", "下午", "晚上"]


async def schedule_task(
    business_id: str,
    items: Optional[list[str]] = None,
    days: int = 7,
    start_date: Optional[str] = None,
    goal: Optional[str] = None,
) -> dict:
    """把任务按天分配并生成主动提醒清单。

    Parameters
    ----------
    business_id : str
        企业 ID（用于回退加载已有计划）。
    items : list[str]
        待排期的任务标题；为空则回退加载该企业最新 7 天计划的任务。
    days : int
        排期天数，默认 7。
    start_date : str
        起始日期 ISO（如 2026-08-10），默认今天。
    goal : str
        本周目标一句话，用于提醒文案。
    """
    # 回退：未提供 items 时，加载最新计划的任务
    if not items:
        async with AsyncSessionLocal() as session:
            plan_rec = (
                await session.execute(
                    select(ExecutionPlanRecord)
                    .filter_by(business_id=business_id)
                    .order_by(ExecutionPlanRecord.created_at.desc())
                )
            ).scalars().first()
            if not plan_rec:
                return {
                    "ok": False,
                    "error": "未提供任务列表，且该企业暂无执行计划可加载；请先 generate_plan 或上传任务。",
                }
            loaded = []
            for d in (plan_rec.days or []):
                if isinstance(d, dict):
                    for t in d.get("tasks", []):
                        title = t.get("title") if isinstance(t, dict) else str(t)
                        if title:
                            loaded.append(title)
            items = loaded
            if not goal:
                goal = plan_rec.theme

    if not items:
        return {"ok": False, "error": "没有可排期的任务。"}

    try:
        start = datetime.fromisoformat(start_date).date() if start_date else date.today()
    except ValueError:
        start = date.today()

    total = len(items)
    # 均匀铺到 days 天，每天不超过 5 个；每天轮转时段
    per_day = max(1, (total + days - 1) // days)
    per_day = min(per_day, 5)

    schedule = []
    reminders = []
    idx = 0
    for day_i in range(days):
        day_tasks = []
        for _ in range(per_day):
            if idx >= total:
                break
            title = items[idx]
            slot = _SLOTS[idx % len(_SLOTS)]
            day_tasks.append({"title": title, "time_slot": slot})
            idx += 1
        if not day_tasks:
            break
        cur = start + timedelta(days=day_i)
        schedule.append({
            "day_index": day_i + 1,
            "date": cur.isoformat(),
            "tasks": day_tasks,
        })
        # 主动提醒：每天早上 09:00 推送当天任务
        task_summary = "；".join(t["title"] for t in day_tasks)
        reminders.append({
            "remind_at": f"{cur.isoformat()}T09:00:00",
            "title": f"第{day_i + 1}天执行提醒",
            "content": f"今日目标：{goal or '推进营销动作'}。任务：{task_summary}",
        })

    return {
        "ok": True,
        "business_id": business_id,
        "goal": goal,
        "schedule": schedule,
        "reminders": reminders,
        "total_tasks": len(items),
    }


async def persist_todos(
    business_id: str,
    user_id: str,
    plan_id: Optional[str],
    day_groups: list[dict],
) -> dict:
    """把排期结果持久化到 ``todos`` 表（闭环：计划确认后落库，可被打卡/复盘读取）。

    Parameters
    ----------
    day_groups : list[dict]
        形如 ``[{"day_index":1, "date":"2026-08-10",
                 "tasks":[{"title":..., "time_slot":..., "how_to":..., "checklist":[...]}]}, ...]``
        兼容 ``schedule_task`` 的 ``schedule`` 与 ``SevenDayPlan.days`` 两种结构。
    """
    import json as _json

    rows = []
    for g in day_groups or []:
        day_index = g.get("day_index") or 0
        date_str = g.get("date") or ""
        for t in g.get("tasks", []) or []:
            if isinstance(t, dict):
                title = t.get("title")
                how_to = t.get("how_to")
                checklist = t.get("checklist")
            else:
                title = str(t)
                how_to = None
                checklist = None
            if not title:
                continue
            rows.append(TodoRecord(
                business_id=business_id,
                user_id=user_id,
                plan_id=plan_id,
                day_index=day_index,
                date=date_str,
                title=title,
                time_slot=t.get("time_slot") if isinstance(t, dict) else None,
                status="pending",
                how_to=how_to,
                checklist=_json.dumps(checklist, ensure_ascii=False) if isinstance(checklist, list) else None,
            ))

    async with AsyncSessionLocal() as session:
        # 替换该计划（或该企业未归属计划的）历史待办，保证幂等
        stmt = select(TodoRecord).filter_by(business_id=business_id)
        if plan_id:
            stmt = select(TodoRecord).filter_by(plan_id=plan_id)
        old = (await session.execute(stmt)).scalars().all()
        for o in old:
            await session.delete(o)
        session.add_all(rows)
        await session.commit()

    return {"ok": True, "persisted": len(rows), "plan_id": plan_id}


# ──────────────────────────────────────────────
# 4. upload_and_parse_data
# ──────────────────────────────────────────────
async def upload_and_parse_data(files: list[str]) -> dict:
    """上传截图/CSV → 解析为结构化数字。

    Parameters
    ----------
    files : list[str]
        服务器上的文件路径列表（截图 PNG/JPG 或 CSV）。

    Returns
    -------
    dict：merged_numbers（合并后的指标数字）、parsed（各文件解析明细）、errors。
    """
    from backend.services.llm import llm_config

    image_files = [f for f in files if is_image_file(f)]
    csv_files = [f for f in files if is_csv_file(f)]
    unknown = [f for f in files if not is_image_file(f) and not is_csv_file(f)]

    parsed_results: list[ParsedData] = []

    # CSV 解析（离线可用）
    for cf in csv_files:
        try:
            parsed_results.append(parse_csv_file(cf))
        except Exception as e:
            logger.error("CSV 解析失败 %s: %s", cf, e)
            parsed_results.append(ParsedData(source_type="csv", errors=[str(e)]))

    # 图片解析（需要多模态模型；无 Key 时返回未解析提示）
    if image_files:
        if llm_config.vision_api_key or llm_config.text_api_key:
            from backend.agents.reviewer import ReviewAgent
            agent = ReviewAgent()
            parsed_results.append(await agent._parse_images(image_files))
        else:
            parsed_results.append(ParsedData(
                source_type="image",
                errors=["未配置多模态模型 Key，截图数字需人工录入或配置 OPENAI_API_KEY"],
            ))

    if not parsed_results:
        return {"ok": False, "error": "没有可解析的文件（请上传 CSV 或截图）。"}

    merged = merge_parsed_data(*parsed_results)
    errors = []
    for p in parsed_results:
        errors.extend(getattr(p, "errors", []) or [])

    return {
        "ok": True,
        "merged_numbers": merged,
        "file_count": len(files),
        "csv_count": len(csv_files),
        "image_count": len(image_files),
        "unknown_files": unknown,
        "errors": errors,
    }


# ──────────────────────────────────────────────
# 5. calculate_kpi（纯函数）
# ──────────────────────────────────────────────
def calculate_kpi(
    numbers: dict,
    targets: Optional[dict] = None,
    previous: Optional[dict] = None,
) -> dict:
    """计算营销指标：达成率、转化率等派生指标、环比趋势。

    Parameters
    ----------
    numbers : dict
        实际数据，如 {"新增客户":12,"咨询量":45,"成交量":8}。
    targets : dict
        目标数据（可选），用于计算达成率。
    previous : dict
        上一周期数据（可选），用于计算环比。

    Returns
    -------
    dict：rows / overall_achievement / derived / trend / summary。
    """
    targets = targets or {}
    rows = []
    for k, actual in numbers.items():
        try:
            actual_f = float(actual)
        except (TypeError, ValueError):
            actual_f = 0.0
        t = targets.get(k)
        try:
            t_f = float(t) if t is not None else None
        except (TypeError, ValueError):
            t_f = None
        rate = round(actual_f / t_f * 100, 1) if (t_f and t_f > 0) else None
        rows.append({
            "metric": k,
            "actual": actual_f,
            "target": t_f,
            "achievement_rate": rate,
        })

    rates = [r["achievement_rate"] for r in rows if r["achievement_rate"] is not None]
    overall = round(sum(rates) / len(rates), 1) if rates else None

    # 派生指标
    def _get(name):
        for r in rows:
            if r["metric"] == name:
                return r["actual"]
        return None

    derived: dict = {}
    consult = _get("咨询量")
    deal = _get("成交量")
    if consult and consult > 0 and deal is not None:
        derived["成交转化率(%)"] = round(deal / consult * 100, 1)
    visit = _get("访客数") or _get("曝光量")
    if visit and visit > 0 and consult is not None:
        derived["咨询转化率(%)"] = round(consult / visit * 100, 1)
    new_cust = _get("新增客户")
    revenue = _get("成交额") or _get("营业额")
    if new_cust and new_cust > 0 and revenue is not None:
        derived["客单价"] = round(revenue / new_cust, 1)

    # 环比趋势
    trend = []
    if previous:
        for k, cur in numbers.items():
            if k in previous:
                try:
                    prev_f = float(previous[k])
                    cur_f = float(cur)
                except (TypeError, ValueError):
                    continue
                delta = round(cur_f - prev_f, 1)
                pct = round(delta / prev_f * 100, 1) if prev_f else None
                trend.append({
                    "metric": k,
                    "previous": prev_f,
                    "current": cur_f,
                    "delta": delta,
                    "pct": pct,
                })

    summary = f"整体目标达成率约 {overall}%" if overall is not None else "未提供目标，无法计算达成率"
    if derived:
        summary += "；派生指标：" + "，".join(f"{k}={v}" for k, v in derived.items())

    return {
        "rows": rows,
        "overall_achievement": overall,
        "derived": derived,
        "trend": trend,
        "summary": summary,
    }


# ──────────────────────────────────────────────
# 6. search_marketing_knowledge（RAG）
# ──────────────────────────────────────────────
async def search_marketing_knowledge(
    query: str,
    category: Optional[str] = None,
    top_k: Optional[int] = None,
) -> dict:
    """RAG 检索营销方法卡片，返回相关方法（含原理/步骤/可衡量 KPI）。

    检索结果会融合「策略有效性评分」做重排序（持续学习）。
    """
    kb = KnowledgeBase()
    results = kb.search(query=query, top_k=top_k, category=category)
    try:
        from backend.agent_core.learning import apply_strategy_scores

        results = await apply_strategy_scores(results)
    except Exception as e:  # noqa: BLE001
        logger.warning("策略分重排序失败，回退原始排序：%s", e)
    return {"ok": True, "query": query, "count": len(results), "cards": results}


# ──────────────────────────────────────────────
# 工具注册表 + LangChain @tool 封装
# ──────────────────────────────────────────────
TOOLS = {
    "diagnose_business": diagnose_business,
    "generate_plan": generate_plan,
    "schedule_task": schedule_task,
    "upload_and_parse_data": upload_and_parse_data,
    "calculate_kpi": calculate_kpi,
    "search_marketing_knowledge": search_marketing_knowledge,
}


def get_langchain_tools():
    """返回 LangChain ``BaseTool`` 列表，供 LLM 工具调用使用。"""
    from langchain_core.tools import tool

    @tool("diagnose_business")
    async def t_diagnose(business_id: str) -> dict:
        """诊断某企业营销健康度。参数 business_id: 企业ID。"""
        return await diagnose_business(business_id)

    @tool("generate_plan")
    async def t_plan(business_id: str) -> dict:
        """生成诊断 + 7 天执行计划。参数 business_id: 企业ID。"""
        return await generate_plan(business_id)

    @tool("schedule_task")
    async def t_schedule(
        business_id: str,
        items: Optional[list[str]] = None,
        days: int = 7,
        start_date: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> dict:
        """把任务按天分配并生成主动提醒。business_id 必填；items 为任务标题列表（可空，自动加载已有计划）。"""
        return await schedule_task(business_id, items, days, start_date, goal)

    @tool("upload_and_parse_data")
    async def t_upload(files: list[str]) -> dict:
        """上传截图/CSV 解析为结构化数字。files 为服务器文件路径列表。"""
        return await upload_and_parse_data(files)

    @tool("calculate_kpi")
    def t_kpi(numbers: dict, targets: Optional[dict] = None, previous: Optional[dict] = None) -> dict:
        """计算营销指标（达成率/转化率/趋势）。numbers 为实际数据字典。"""
        return calculate_kpi(numbers, targets, previous)

    @tool("search_marketing_knowledge")
    async def t_search(query: str, category: Optional[str] = None, top_k: Optional[int] = None) -> dict:
        """RAG 检索营销方法卡片。query 为自然语言问题。"""
        return await search_marketing_knowledge(query, category, top_k)

    return [t_diagnose, t_plan, t_schedule, t_upload, t_kpi, t_search]
