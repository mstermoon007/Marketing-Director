"""
Agent 核心框架测试
================================

覆盖：
- calculate_kpi 纯函数（达成率/转化率/趋势）
- 意图分类器
- 营销知识库 RAG 检索
- diagnose_business 离线降级
- schedule_task 排期
- 主控多轮对话（状态图 + 上下文保持 + 企业ID传播）
- 记忆库持久化
- SSE 流式对话（controller.chat_stream 生成器 + HTTP 端点鉴权与事件格式）
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from backend.agent_core import get_controller
from backend.agent_core.intent import classify_intent
from backend.agent_core.memory import MemoryStore
from backend.agent_core.tools import (
    calculate_kpi,
    diagnose_business,
    schedule_task,
    search_marketing_knowledge,
)
from backend.db.models import AsyncSessionLocal, BusinessRecord, gen_id


# ── calculate_kpi ──
def test_calculate_kpi_basic():
    kpi = calculate_kpi(
        {"新增客户": 12, "咨询量": 45, "成交量": 8, "成交额": 3200},
        {"新增客户": 10, "咨询量": 40},
        {"新增客户": 9, "咨询量": 30},
    )
    assert kpi["overall_achievement"] is not None
    assert kpi["derived"]["成交转化率(%)"] == pytest.approx(17.8, abs=0.1)
    assert kpi["derived"]["客单价"] == pytest.approx(266.7, abs=0.1)
    assert len(kpi["trend"]) == 2
    assert kpi["trend"][0]["metric"] == "新增客户"
    assert kpi["trend"][0]["pct"] == pytest.approx(33.3, abs=0.1)


def test_calculate_kpi_no_target():
    kpi = calculate_kpi({"新增客户": 5})
    assert kpi["overall_achievement"] is None
    assert "未提供目标" in kpi["summary"]


# ── 意图分类 ──
@pytest.mark.parametrize("text,expected", [
    ("帮我诊断一下我的店", "diagnose"),
    ("给我做个本周计划", "plan"),
    ("把计划排成日程并提醒我", "schedule"),
    ("上传数据帮我复盘", "review"),
    ("你好，你是谁", "chat"),
])
def test_intent_classification(text, expected):
    assert classify_intent(text) == expected


def test_intent_pending_clarification():
    # 上轮追问（pending=diagnose），本轮短回答 → 沿用
    assert classify_intent("餐饮，开在成都", pending_intent="diagnose") == "diagnose"


# ── RAG 检索 ──
@pytest.mark.asyncio
async def test_search_knowledge():
    res = await search_marketing_knowledge("餐饮 怎么用短视频获客", top_k=3)
    assert res["ok"] is True
    assert res["count"] >= 1
    assert any("餐饮" in c["name"] for c in res["cards"])


# ── diagnose 离线降级 ──
@pytest.mark.asyncio
async def test_diagnose_offline():
    bid = gen_id()
    async with AsyncSessionLocal() as s:
        s.add(BusinessRecord(
            id=bid, business_name="测试面馆", industry="餐饮", city="武汉",
            product_desc="热干面", biggest_pain="没客人",
        ))
        await s.commit()

    res = await diagnose_business(bid)
    assert res["ok"] is True
    assert isinstance(res["report"]["overall_score"], int)
    # 已持久化
    async with AsyncSessionLocal() as s:
        from backend.db.models import DiagnosisRecord
        rec = (await s.execute(select(DiagnosisRecord).filter_by(business_id=bid))).scalar_one_or_none()
        assert rec is not None


# ── schedule_task 显式任务 ──
@pytest.mark.asyncio
async def test_schedule_explicit_items():
    sched = await schedule_task(
        "b_schedule_1",
        items=["发朋友圈", "给老客打电话", "拍短视频", "写复盘", "做海报"],
        days=7,
        goal="本周获客",
    )
    assert sched["ok"] is True
    # 5 个任务均匀铺到 7 天（每天≤5，这里每天1个 → 5 天）
    total = sum(len(d["tasks"]) for d in sched["schedule"])
    assert total == 5
    assert len(sched["reminders"]) == len(sched["schedule"])


# ── 主控多轮对话（状态图 + 上下文保持）──
@pytest.mark.asyncio
async def test_controller_multiturn():
    c = get_controller()
    sid = f"test_session_{gen_id()}"
    uid = "test_user_1"

    r1 = await c.chat(sid, uid, "帮我诊断一下我的餐饮店，开在成都，做川菜，痛点没客人")
    assert r1["intent"] == "diagnose"
    assert r1["business_id"]
    bid = r1["business_id"]

    r2 = await c.chat(sid, uid, "帮我做个本周计划")
    assert r2["intent"] == "plan"
    # 企业ID应自动复用（上下文保持）
    assert r2["business_id"] == bid

    r3 = await c.chat(sid, uid, "餐饮怎么用短视频引流")
    assert r3["intent"] == "chat"
    assert "短视频" in r3["response"] or "引流" in r3["response"]

    # 历史应包含 3 轮 user+assistant
    history = c.memory.get_history(sid, limit=20)
    assert len(history) == 6


# ── 记忆持久化 ──
@pytest.mark.asyncio
async def test_memory_persistence():
    ms = MemoryStore()
    sid = f"mem_session_{gen_id()}"
    ms.append_history(sid, "u_mem", "user", "诊断我的店")
    ms.append_history(sid, "u_mem", "assistant", "已为你诊断")
    h = ms.get_history(sid, limit=10)
    assert len(h) == 2
    assert h[0]["role"] == "user"
    assert h[1]["role"] == "assistant"

    ms.save_profile("u_mem", "餐饮老板", {"industry": "餐饮"})
    prof = ms.get_profile("u_mem")
    assert prof is not None
    assert prof["metadata"]["industry"] == "餐饮"


# ── SSE 流式对话：控制器生成器 ──
@pytest.mark.asyncio
async def test_chat_stream_events():
    """chat_stream 应按 intent → thinking* → (tool*) → done 顺序产出事件。"""
    c = get_controller()
    sid = f"stream_session_{gen_id()}"
    uid = "test_user_stream"

    events = []
    async for evt in c.chat_stream(sid, uid, "帮我诊断一下我的餐饮店，开在成都，做川菜，痛点没客人"):
        events.append(evt)

    types = [e["type"] for e in events]
    assert types[0] == "intent", f"首个事件应为 intent，实际 {types}"
    assert types[-1] == "done", f"末个事件应为 done，实际 {types}"
    assert "thinking" in types, "应至少有一个 thinking 事件"
    assert "error" not in types

    first = events[0]
    assert first["intent"] == "diagnose"
    assert first["intent_label"]

    last = events[-1]
    for key in ("response", "intent", "business_id", "needs_clarification", "data"):
        assert key in last, f"done 事件缺少字段 {key}"
    assert last["response"]

    # 流式与非流式共用同一记忆库：历史应写入 1 轮 user + 1 轮 assistant
    history = c.memory.get_history(sid, limit=10)
    assert len(history) == 2
    assert history[0]["role"] == "user"


# ── SSE HTTP 端点 ──
def test_agent_chat_stream_requires_auth():
    """未带 JWT 访问流式端点应被拒绝（401/403）。"""
    from fastapi.testclient import TestClient

    from backend.api.main import app

    with TestClient(app) as client:
        resp = client.post("/api/agent/chat/stream", json={"message": "你好"})
    assert resp.status_code in (401, 403), f"未鉴权却返回 {resp.status_code}"


def test_agent_chat_stream_sse_format():
    """带 JWT 访问流式端点：返回 text/event-stream，且每个分块为 `data: {json}` 格式。"""
    from fastapi.testclient import TestClient

    from backend.api.auth import create_access_token
    from backend.api.main import app

    token = create_access_token("test_user_sse")
    with TestClient(app) as client, client.stream(
        "POST",
        "/api/agent/chat/stream",
        json={"message": "餐饮怎么用短视频引流"},
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        body = "".join(chunk for chunk in resp.iter_text())

    frames = [f for f in body.split("\n\n") if f.strip()]
    assert frames, "SSE 未产出任何事件"
    parsed = []
    for f in frames:
        assert f.startswith("data: "), f"事件格式非法：{f[:40]}"
        parsed.append(json.loads(f[len("data: "):]))

    types = [p["type"] for p in parsed]
    assert types[0] == "intent"
    assert types[-1] == "done"
