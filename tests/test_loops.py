"""
阶段四闭环业务接口集成测试
============================

验证：计划确认→排期落库、任务打卡、数据上传解析、复盘触发、反馈更新策略分。
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from backend.api.auth import create_access_token
from backend.api.main import app
from backend.db.models import (
    AsyncSessionLocal,
    BusinessRecord,
    ExecutionPlanRecord,
    MetricRecord,
    StrategyScoreRecord,
)
from backend.agent_core.tools import calculate_kpi


USER = "loop_test_user"


@pytest_asyncio.fixture
async def seeded():
    """插入一个归属用户的企业 + 一条草稿计划。"""
    async with AsyncSessionLocal() as session:
        biz = BusinessRecord(
            id="loop_biz",
            user_id=USER,
            business_name="测试面馆",
            industry="餐饮",
            city="成都",
        )
        session.add(biz)
        plan = ExecutionPlanRecord(
            id="loop_plan",
            business_id="loop_biz",
            diagnosis_id="loop_diag",
            start_date=__import__("datetime").date(2026, 8, 10),
            theme="本周引流",
            key_metrics={"新增客户": 10, "咨询量": 40},
            status="draft",
            days=[
                {
                    "day_index": 1,
                    "day_name": "周一",
                    "date": "2026-08-10",
                    "focus": "筹备",
                    "tasks": [
                        {"title": "拍3条短视频", "time_slot": "上午", "how_to": "展示招牌面", "checklist": ["脚本", "拍摄"]},
                    ],
                },
                {
                    "day_index": 2,
                    "day_name": "周二",
                    "date": "2026-08-11",
                    "focus": "执行",
                    "tasks": [
                        {"title": "群发优惠", "time_slot": "下午", "how_to": "发朋友圈", "checklist": []},
                    ],
                },
            ],
        )
        session.add(plan)
        await session.commit()
    yield "loop_biz"
    # 清理
    async with AsyncSessionLocal() as session:
        await session.execute(
            StrategyScoreRecord.__table__.delete().where(StrategyScoreRecord.card_id == "card_x")
        )
        await session.execute(MetricRecord.__table__.delete().where(MetricRecord.business_id == "loop_biz"))
        await session.execute(BusinessRecord.__table__.delete().where(BusinessRecord.id == "loop_biz"))
        await session.execute(ExecutionPlanRecord.__table__.delete().where(ExecutionPlanRecord.id == "loop_plan"))
        await session.commit()


def _auth():
    return {"Authorization": f"Bearer {create_access_token(USER)}"}


def test_confirm_plan_persists_todos(seeded):
    """确认计划 → 自动排期落库 todos。"""
    with TestClient(app) as client:
        r = client.post("/api/plan/loop_plan/confirm", headers=_auth())
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert len(body["schedule"]) == 2  # 两个任务

        # todos 已落库
        g = client.get("/api/schedule", headers=_auth())
        assert g.status_code == 200
        todos = g.json()["todos"]
        assert len(todos) == 2
        assert todos[0]["status"] == "pending"


def test_checkin_updates_status(seeded):
    """任务打卡 → 状态变为 done。"""
    with TestClient(app) as client:
        client.post("/api/plan/loop_plan/confirm", headers=_auth())
        todos = client.get("/api/schedule", headers=_auth()).json()["todos"]
        tid = todos[0]["id"]
        r = client.put("/api/schedule/checkin", json={"todo_id": tid, "status": "done"}, headers=_auth())
        assert r.status_code == 200
        assert r.json()["todo"]["status"] == "done"
        assert r.json()["todo"]["completed_at"]


def test_review_needs_upload_then_ok(seeded):
    """无上传数据 → 提示先上传；上传后 → 生成复盘与建议。"""
    with TestClient(app) as client:
        r0 = client.post("/api/review/trigger", json={"business_id": "loop_biz"}, headers=_auth())
        assert r0.status_code == 200
        assert r0.json()["needs_upload"] is True

        # 插入指标
        async def _add_metric():
            async with AsyncSessionLocal() as session:
                session.add(MetricRecord(business_id="loop_biz", user_id=USER, source="upload",
                                         numbers={"新增客户": 8, "咨询量": 35}))
                await session.commit()

        import asyncio
        asyncio.get_event_loop().run_until_complete(_add_metric())

        r1 = client.post("/api/review/trigger", json={"business_id": "loop_biz"}, headers=_auth())
        assert r1.status_code == 200
        rev = r1.json()["review"]
        assert rev["summary"]
        assert isinstance(rev["suggestions"], list) and len(rev["suggestions"]) > 0
        # 达成率应低于 100%（8/10）
        assert rev["vs_target"][0]["achievement_rate"] == 80.0


def test_feedback_updates_strategy_score(seeded):
    """反馈 → 策略有效性评分更新。"""
    with TestClient(app) as client:
        r = client.post(
            "/api/agent/feedback",
            json={"target_type": "plan", "target_id": "loop_plan", "rating": 1, "card_ids": ["card_x"]},
            headers=_auth(),
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        updated = [u for u in r.json()["updated_scores"] if u["card_id"] == "card_x"]
        assert updated and updated[0]["score"] > 0


def test_calculate_kpi_unit():
    """KPI 纯函数冒烟。"""
    kpi = calculate_kpi({"新增客户": 12, "咨询量": 45}, targets={"新增客户": 10, "咨询量": 40})
    assert kpi["overall_achievement"] == 116.2
    assert kpi["rows"][0]["achievement_rate"] == 120.0
