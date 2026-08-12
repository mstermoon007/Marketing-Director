"""
阶段五 · 端到端闭环自动化测试（诊断 → 计划 → 日程）

目标：用最接近真实链路的 HTTP 接口，跑通一条完整业务闭环，并验证
  1. Agent 节点切换正确（diagnose → plan 意图路由到对应子 Agent）；
  2. 数据在节点间一致（诊断产出的 business_id 自动贯穿到计划/排期）；
  3. 确认排期后，落库的待办与计划任务一一对应（数量与标题一致）。

说明：后端工具对「无 LLM Key」环境健壮（自动降级到本地规则引擎），
因此本测试无需 Mock LLM 即可稳定跑通，贴近生产链路。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.api.auth import create_access_token
from backend.api.main import app


def _collect_stream(client: TestClient, token: str, message: str, session_id: str, business_id: str = ""):
    """发起一次 SSE 流式对话，返回 (done_event, all_events)。

    通过遍历 SSE 分块解析出最后一个 ``done`` 事件（承载结构化结果）。
    """
    events: list[dict] = []
    with client.stream(
        "POST",
        "/api/agent/chat/stream",
        json={
            "message": message,
            "session_id": session_id,
            "business_id": business_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    ) as resp:
        assert resp.status_code == 200, f"流式端点返回 {resp.status_code}"
        assert "text/event-stream" in resp.headers.get("content-type", "")
        body = "".join(chunk for chunk in resp.iter_text())

    for frame in [f for f in body.split("\n\n") if f.strip()]:
        assert frame.startswith("data: "), f"事件格式非法：{frame[:40]}"
        events.append(json.loads(frame[len("data "):]))

    types = [e["type"] for e in events]
    assert types[0] == "intent", f"首个事件应为 intent，实际 {types[:3]}"
    assert types[-1] == "done", f"末个事件应为 done，实际 {types[-3:]}"
    done = next((e for e in events if e["type"] == "done"), None)
    return done, events


@pytest.mark.asyncio
async def test_closed_loop_diagnose_plan_schedule():
    """诊断 → 计划 → 确认排期 → 读取日程：验证节点切换与数据一致性。"""
    token = create_access_token("e2e_user_loop")
    sid = f"e2e_session_{__name__}"

    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {token}"}

        # ① 诊断：路由到 diagnose 子 Agent，产出诊断卡片 + 回写 business_id
        done1, _ = _collect_stream(
            client, token,
            "帮我诊断一下我的餐饮店，开在成都，做川菜，痛点没客人",
            sid,
        )
        assert done1["intent"] == "diagnose", "意图应路由到 diagnose 节点"
        assert done1["data"].get("diagnosis"), "诊断应产出 diagnosis 卡片"
        bid = done1["business_id"]
        assert bid, "诊断应回写 business_id（闭环起点）"

        # ② 计划：复用同一会话/企业，验证节点切换 + 上下文保持
        done2, _ = _collect_stream(
            client, token, "帮我做个本周计划", sid, bid,
        )
        assert done2["intent"] == "plan", "意图应路由到 plan 节点"
        # 上下文保持：business_id 应自动贯穿
        assert done2["business_id"] == bid, "计划阶段应复用诊断阶段的企业 ID"
        plan = done2["data"].get("plan")
        assert plan and plan.get("id"), "计划应产出带 id 的 plan"
        assert plan.get("days") and len(plan["days"]) > 0, "计划应含 7 天任务"
        plan_id = plan["id"]

        # ③ 确认计划 → 后端自动排期落库 todos
        r = client.post(f"/api/plan/{plan_id}/confirm", headers=headers)
        assert r.status_code == 200, r.text
        confirm = r.json()
        assert confirm["ok"] is True, f"确认排期失败：{confirm}"
        scheduled = confirm.get("schedule") or []
        assert len(scheduled) > 0, "确认后应产出排期任务"

        # ④ 读取日程，验证数据一致性
        g = client.get(f"/api/schedule?business_id={bid}", headers=headers)
        assert g.status_code == 200, g.text
        body = g.json()
        todos = body.get("todos") or []
        assert body.get("ok") is True
        assert len(todos) == len(scheduled), (
            f"日程待办数({len(todos)})应与排期({len(scheduled)})一致"
        )
        assert all(t["status"] in ("pending", "doing", "done") for t in todos)

        # plan_id 应贯穿到待办（闭环可追溯）
        assert any(t.get("plan_id") == plan_id for t in todos), "待办应关联确认的 plan_id"

        # 计划全部任务标题应出现在落库待办中（无丢任务）
        plan_titles = {
            t["title"]
            for day in plan["days"]
            for t in (day.get("tasks") or [])
            if t.get("title")
        }
        todo_titles = {t["title"] for t in todos}
        assert plan_titles <= todo_titles, "排期后的待办应覆盖计划的全部任务"


@pytest.mark.asyncio
async def test_confirm_unknown_plan_is_safe():
    """确认一个不存在的计划应优雅返回 ok=False，不应 500。"""
    token = create_access_token("e2e_user_unknown")
    with TestClient(app) as client:
        r = client.post("/api/plan/does-not-exist/confirm", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is False
