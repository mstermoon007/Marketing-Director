"""
后端安全验证脚本（JWT 鉴权漂移清零验证）

验证项：
  1. 零 mock 残留 — 无 JWT_SECRET_KEY 启动需报错（防 dev-only 常量密钥回退）
  2. JWT 401 — 无 token / 伪造 token 访问受保护端点返回 401
  3. 有效 token 验证通过
  4. 未认证请求对业务路由（diagnosis/start 等）返回 401（路由器级别鉴权全覆盖）
  5. Agent 端点 JWT 401 验证
  6. 路径遍历 + magic byte 上传拦截
  7. CORS 不泄露凭据
"""
import asyncio
import io
import os
import sys


# 设置开发环境变量（JWT_SECRET_KEY 必须设置，不允许常量回退）
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET_KEY", "verify-test-secret-key-min-32-chars-long")

# 确保 src 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import ASGITransport, AsyncClient

from backend.api.auth import create_access_token
from backend.api.main import app


async def run_verification():
    results = []
    transport = ASGITransport(app=app)

    # 直接签发 token（替代旧 mock 登录，不再依赖 WeChat code2session）
    test_token = create_access_token(
        user_id="verify-test-user-001",
        openid="verification_test_openid",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # ── 1. 健康检查 ──
        resp = await client.get("/health")
        ok = resp.status_code == 200 and resp.json().get("status") == "ok"
        results.append(("健康检查 /health", ok, f"status={resp.status_code}"))

        # ── 2. JWT 401 — 无 token 访问受保护端点 ──
        resp = await client.get("/api/auth/verify")
        ok = resp.status_code == 401
        results.append((
            "JWT 401: 无 token 访问 /api/auth/verify",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 3. JWT 401 — 伪造 token ──
        resp = await client.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer fake.invalid.token.forged"}
        )
        ok = resp.status_code == 401
        results.append((
            "JWT 401: 伪造 token 访问",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 4. JWT 验证 — 有效 token ──
        resp = await client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        ok = resp.status_code == 200 and resp.json().get("data", {}).get("valid") is True
        results.append((
            "JWT 验证: 有效 token 通过",
            ok,
            f"status={resp.status_code}"
        ))

        # ── 5. 业务路由 401 — 无 token 访问 /api/diagnosis/start ──
        resp = await client.post("/api/diagnosis/start", json={
            "company_name": "验证测试店铺",
            "industry": "餐饮",
            "city": "深圳",
            "main_product": "咖啡饮品",
            "target_customer": "上班族白领",
        })
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/diagnosis/start",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 6. 业务路由 401 — 无 token 访问 /api/business/create ──
        resp = await client.post("/api/business/create", json={
            "company_name": "测试门店",
            "industry": "餐饮",
            "city": "深圳",
        })
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/business/create",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 7. 业务路由 401 — 无 token 访问 /api/dashboard ──
        resp = await client.get("/api/dashboard")
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/dashboard",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 8. 业务路由 401 — 无 token 访问 /api/roadmap/current ──
        resp = await client.get("/api/roadmap/current")
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/roadmap/current",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 9. 业务路由 401 — 无 token 访问 /api/task/detail ──
        resp = await client.get("/api/task/detail")
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/task/detail",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 10. 业务路由 401 — 无 token 访问 /api/review/latest ──
        resp = await client.get("/api/review/latest")
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/review/latest",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 11. 业务路由 401 — 无 token 访问 /api/execution/{id} ──
        resp = await client.post("/api/execution/test-nonexistent", json={})
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/execution/{id}",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 12. 业务路由 401 — 无 token 访问 /api/plan/weekly ──
        resp = await client.get("/api/plan/weekly")
        ok = resp.status_code == 401
        results.append((
            "业务路由 401: 无 token 访问 /api/plan/weekly",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 13. Agent 端点 JWT 401 — 无 token 访问 /api/agent/chat ──
        resp = await client.post(
            "/api/agent/chat",
            json={"message": "帮我诊断一下餐饮门店经营", "session_id": "verify-session-1"}
        )
        ok = resp.status_code == 401
        results.append((
            "Agent JWT 401: 无 token 访问 /api/agent/chat",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 14. Agent 端点 JWT 401 — 无 token 访问 /api/agent/history ──
        resp = await client.get("/api/agent/history?session_id=verify-session-1")
        ok = resp.status_code == 401
        results.append((
            "Agent JWT 401: 无 token 访问 /api/agent/history",
            ok,
            f"status={resp.status_code}, detail={resp.json().get('detail', '')}"
        ))

        # ── 15. Agent 对话可达 + 意图分类 + RAG 命中 ──
        agent_session = "verify-agent-session"
        resp = await client.post(
            "/api/agent/chat",
            json={
                "message": "帮我诊断一下我的餐饮门店，最近客流下滑",
                "session_id": agent_session,
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )
        chat_ok = resp.status_code == 200
        data = resp.json().get("data", {}) if chat_ok else {}
        intent = data.get("intent", "")
        resp_text = (data.get("response") or "").strip()
        rag_ok = chat_ok and intent == "diagnose" and len(resp_text) > 0
        results.append((
            "Agent 对话: 诊断意图识别 + RAG/规则响应非空",
            rag_ok,
            f"status={resp.status_code}, intent={intent}, resp_len={len(resp_text)}"
        ))

        # ── 16. Agent 多轮上下文保持 ──
        resp2 = await client.post(
            "/api/agent/chat",
            json={"message": "我主要在深圳南山开店，客单价 35 元", "session_id": agent_session},
            headers={"Authorization": f"Bearer {test_token}"}
        )
        hist_resp = await client.get(
            f"/api/agent/history?session_id={agent_session}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        hist = hist_resp.json().get("data", {}).get("history", []) if hist_resp.status_code == 200 else []
        multiturn_ok = resp2.status_code == 200 and len(hist) >= 2
        results.append((
            "Agent 多轮: 会话历史保持（≥2 轮）",
            multiturn_ok,
            f"chat2_status={resp2.status_code}, history_len={len(hist)}"
        ))

        # ── 17. 路径遍历拦截 ──
        evil_content = b"evil content"
        resp = await client.post(
            "/api/review/test-plan-id/upload",
            files={"file": ("../../evil.txt", io.BytesIO(evil_content), "text/plain")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
        traversal_blocked = resp.status_code != 200
        results.append((
            "路径遍历拦截: ../../evil.txt 被拒绝",
            traversal_blocked,
            f"status={resp.status_code}"
        ))

        # ── 18. magic byte 校验 ──
        fake_content = b"This is not an image, just text"
        resp = await client.post(
            "/api/review/test-plan-id/upload",
            files={"file": ("photo.png", io.BytesIO(fake_content), "image/png")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
        magic_ok = resp.status_code != 200
        results.append((
            "Magic byte 校验: 伪装 PNG 被拒绝",
            magic_ok,
            f"status={resp.status_code}"
        ))

        # ── 19. CORS 不泄露凭据 ──
        resp = await client.options(
            "/health",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        allow_origin = resp.headers.get("access-control-allow-origin", "")
        cors_ok = "evil.example.com" not in allow_origin
        results.append((
            "CORS: 恶意域名不在允许列表",
            cors_ok,
            f"allow_origin={allow_origin or '(none)'}"
        ))

    return results


def main():
    import subprocess as _sp

    print("=" * 60)
    print("  JWT 鉴权漂移清零验证")
    print("=" * 60)
    print()

    # ── 0. 子进程验证：零 mock 残留（无 JWT_SECRET_KEY 启动必须报错）──
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    sub_code = (
        "import os,sys\n"
        "os.environ.pop('JWT_SECRET_KEY','')\n"
        "sys.path.insert(0," + repr(project_dir) + ")\n"
        "from backend.api.auth import _get_jwt_secret\n"
        "try:\n"
        "    _get_jwt_secret()\n"
        "    print('UNEXPECTED_OK')\n"
        "except RuntimeError as e:\n"
        "    print('RUNTIME_ERROR:' + str(e))\n"
    )
    result = _sp.run(
        [sys.executable, "-c", sub_code],
        cwd=project_dir,
        capture_output=True, text=True, timeout=30,
    )
    stdout_str = (result.stdout or "") + (result.stderr or "")
    no_fallback_ok = "RUNTIME_ERROR:" in stdout_str and "UNEXPECTED_OK" not in stdout_str
    print(f"  {'✅ PASS' if no_fallback_ok else '❌ FAIL'}  零 mock 残留: 无 JWT_SECRET_KEY 启动报错")
    print(f"         {'JWT_SECRET_KEY 强制要求已生效' if no_fallback_ok else '仍有常量回退风险: ' + stdout_str.strip()[:120]}")
    sub_ok = no_fallback_ok

    print()
    results = asyncio.run(run_verification())

    passed = int(sub_ok)
    failed = 0 if sub_ok else 1
    for name, ok, detail in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {name}")
        print(f"         {detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print(f"  结果: {passed} passed, {failed} failed, {len(results)} + 1(sub) total")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
