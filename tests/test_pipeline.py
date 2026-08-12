"""
Pipeline 端到端测试（开发思路文档 §6 Phase 2 要求）

唯一核心链路：
输入企业信息 → AI 诊断报告 → 7 天执行清单 → 截图复盘报告
"""

import pytest
import json
import uuid
from datetime import date

from sqlalchemy import select

from backend.models.business import BusinessProfile
from backend.models.execution import SevenDayPlan
from backend.services.pipeline import (
    load_business_profile,
    load_diagnosis_report,
    load_execution_plan,
    run_full_pipeline,
    run_weekly_review,
)
from backend.db.models import (
    AsyncSessionLocal, BusinessRecord, ExecutionPlanRecord, ReviewRecord, init_db,
)

from tests.fixtures.industries import ALL_INDUSTRIES
from tests.conftest import make_profile


# ──────────────────────────────────────────────
# DB 辅助：把 make_profile 生成的临时数据存入 DB（带唯一ID，避免冲突）
# ──────────────────────────────────────────────

def _make_bid(base: str) -> str:
    """生成唯一的业务ID，避免跨测试的 UNIQUE 冲突"""
    return f"pipeline_{base}_{uuid.uuid4().hex[:8]}"


async def _save_profile_to_db(profile: BusinessProfile) -> str:
    async with AsyncSessionLocal() as session:
        rec = BusinessRecord(
            id=profile.id,
            business_name=profile.business_name,
            industry=profile.industry,
            city=profile.city,
            product_desc=profile.product_desc,
            price_range=profile.price_range,
            target_customers=profile.target_customers,
            competitors=profile.competitors,
            current_channels=profile.current_channels,
            monthly_revenue=profile.monthly_revenue,
            team_size=profile.team_size,
            biggest_pain=profile.biggest_pain,
        )
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        return rec.id


async def _save_plan_to_db(plan: SevenDayPlan) -> str:
    async with AsyncSessionLocal() as session:
        rec = ExecutionPlanRecord(
            diagnosis_id=plan.diagnosis_id,
            business_id=plan.business_id,
            start_date=plan.start_date or date.today(),
            theme=plan.theme,
            goals=plan.goals,
            key_metrics=plan.key_metrics,
            days=plan.to_dict()["days"],
        )
        session.add(rec)
        await session.commit()
        await session.refresh(rec)
        return rec.id


@pytest.fixture(autouse=True, scope="module")
def _init_db_once():
    init_db()


# ──────────────────────────────────────────────
# 数据加载测试
# ──────────────────────────────────────────────

class TestPipelineLoaders:

    @pytest.mark.asyncio
    async def test_load_business_profile_ok(self):
        p = make_profile("家装")
        p.id = _make_bid("loader_ok")
        bid = await _save_profile_to_db(p)

        loaded = await load_business_profile(bid)
        assert loaded.id == bid
        assert loaded.industry == "家装"
        assert loaded.business_name == p.business_name

    @pytest.mark.asyncio
    async def test_load_business_profile_missing_raises(self):
        with pytest.raises(ValueError, match="企业信息不存在"):
            await load_business_profile("nonexistent_id_xyz")

    @pytest.mark.asyncio
    async def test_load_diagnosis_report_missing_returns_none(self):
        # 未生成诊断时返回 None，而不是抛错
        assert await load_diagnosis_report("nonexistent_biz") is None


# ──────────────────────────────────────────────
# 完整 Pipeline 测试（Mock LLM）
# ──────────────────────────────────────────────

class TestRunFullPipeline:

    @pytest.mark.asyncio
    async def test_pipeline_full_chain(self, patched_llm):
        """
        端到端：企业信息 → 诊断报告 → 7天执行清单
        验证 run_full_pipeline 产生三段业务模型，
        且都被持久化到数据库可被 load_* 重新读取。
        """
        # 准备企业 + Mock 响应（使用唯一 bid）
        industry = "家装"
        p = make_profile(industry)
        p.id = _make_bid("pipeline_full")
        bid = await _save_profile_to_db(p)

        patched_llm.set_responses(
            diagnosis=ALL_INDUSTRIES[industry]["diagnosis_resp"],
            executor=ALL_INDUSTRIES[industry]["executor_resp"],
        )

        # Step 1: 调用主流程
        result = await run_full_pipeline(bid)

        # Step 2: 结构校验
        assert "business" in result
        assert "diagnosis" in result
        assert "plan" in result

        diag = result["diagnosis"]
        plan = result["plan"]

        assert diag["business_id"] == bid
        assert 0 <= diag["overall_score"] <= 100
        assert len(diag["top_issues"]) >= 1

        assert plan["diagnosis_id"]  # 诊断 ID 被关联
        assert plan["business_id"] == bid
        assert len(plan["days"]) == 7  # 必须 7 天

        # Step 3: 持久化校验 — load_* 能读到刚写入的数据
        loaded_diag = await load_diagnosis_report(bid)
        assert loaded_diag is not None
        assert loaded_diag.id == diag["id"]
        assert loaded_diag.overall_score == diag["overall_score"]

        loaded_plan = await load_execution_plan(plan["id"])
        assert loaded_plan.id == plan["id"]
        assert len(loaded_plan.days) == 7

    @pytest.mark.asyncio
    async def test_pipeline_no_llm_falls_back(self, monkeypatch, patched_llm):
        """
        无 API Key / LLM 失败：fallback 到本地规则引擎
        run_full_pipeline 仍能产出有效报告和计划，不抛异常。
        """
        p = make_profile("餐饮")
        p.id = _make_bid("pipeline_fallback")
        bid = await _save_profile_to_db(p)

        # 设置 mock 让 LLM 抛出异常，触发 fallback
        async def _raise(*args, **kwargs):
            raise RuntimeError("Simulated LLM unavailable")
        patched_llm.chat = _raise
        patched_llm.chat_with_images = _raise

        result = await run_full_pipeline(bid)

        # fallback 仍应成功（本地规则引擎 + 本地执行计划）
        assert result["diagnosis"]["overall_score"] > 0
        assert len(result["plan"]["days"]) == 7


# ──────────────────────────────────────────────
# 复盘 Pipeline 测试
# ──────────────────────────────────────────────

class TestRunWeeklyReview:

    @pytest.mark.asyncio
    async def test_weekly_review_with_csv(self, patched_llm, tmp_path):
        """
        run_weekly_review：上传 CSV 截图 → 生成复盘报告
        """
        industry = "家装"
        p = make_profile(industry)
        p.id = _make_bid("review_csv")
        bid = await _save_profile_to_db(p)

        # Mock 诊断 + 计划
        patched_llm.set_responses(
            diagnosis=ALL_INDUSTRIES[industry]["diagnosis_resp"],
            executor=ALL_INDUSTRIES[industry]["executor_resp"],
        )
        pipe_result = await run_full_pipeline(bid)

        # 为了让 ReviewAgent 不走真实 LLM，重新 mock reviewer 响应
        patched_llm.set_responses(
            review=ALL_INDUSTRIES[industry]["review_resp"],
            vision=json.dumps({"新增客户": 10, "到店数": 2}, ensure_ascii=False),
        )

        plan_id = pipe_result["plan"]["id"]

        # 造一个假 CSV 文件
        csv_path = tmp_path / "week_data.csv"
        csv_path.write_text(ALL_INDUSTRIES[industry]["csv_content"], encoding="utf-8")

        result = await run_weekly_review(plan_id=plan_id, uploaded_files=[str(csv_path)])

        assert "review" in result
        rev = result["review"]
        assert len(rev["summary"]) > 0
        assert "vs_target" in rev
        assert len(rev["suggestions"]) >= 1

        # DB 里能查到（异步查询）
        async with AsyncSessionLocal() as session:
            result_q = await session.execute(
                select(ReviewRecord).filter_by(plan_id=plan_id)
            )
            recs = result_q.scalars().all()
            assert len(recs) >= 1

    @pytest.mark.asyncio
    async def test_weekly_review_plan_missing_raises(self):
        """plan_id 不存在 → ValueError"""
        with pytest.raises(ValueError, match="执行计划不存在"):
            await run_weekly_review(plan_id="ghost_plan_xyz", uploaded_files=[])
