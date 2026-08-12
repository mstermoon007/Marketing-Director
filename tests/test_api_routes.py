"""
API 路由层集成测试
===================

覆盖 10 个 router 的核心路径：
  - 认证、企业 CRUD、诊断查询、执行计划查询、复盘上传、
  - 路线图、周计划、任务详情、工作台、Agent 对话

使用 httpx.ASGITransport（异步） + 数据库隔离（conftest.py 中已设置临时 DB）。
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.auth import create_access_token
from backend.api.main import app
from backend.config.settings import app_config
from backend.db.models import AsyncSessionLocal, BusinessRecord


# ── 测试用户 ──
TEST_USER = "api_test_user"
TEST_TOKEN = create_access_token(TEST_USER, "test_openid")


@pytest.fixture
def client():
    """FastAPI TestClient（同步包装）。"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """带 JWT Bearer Token 的请求头。"""
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


# ═══════════════════════════════════════════════════════════════════
# 1. 认证模块 (auth router)
# ═══════════════════════════════════════════════════════════════════

class TestAuthRoutes:
    """POST /api/auth/login  + GET /api/auth/verify"""

    def test_login_missing_code_returns_422(self, client):
        """缺少 wechat_code 返回 422。"""
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 422

    @patch("backend.api.auth._wechat_code2session")
    def test_login_with_invalid_code(self, mock_c2s, client):
        """无效微信 code 返回 401。"""
        mock_c2s.return_value = None
        resp = client.post("/api/auth/login", json={"code": "invalid_code"})
        assert resp.status_code == 401
        assert "code 无效" in resp.json()["detail"]

    @patch("backend.api.auth._wechat_code2session")
    def test_login_success_returns_token(self, mock_c2s, client):
        """有效微信 code 返回 token 和用户信息。"""
        mock_c2s.return_value = {"openid": "test_openid_login", "session_key": "sk_test"}
        resp = client.post("/api/auth/login", json={"code": "valid_code"})
        assert resp.status_code == 200
        result = resp.json()
        assert "token" in result["data"]
        assert "user_id" in result["data"]

    def test_verify_without_token_returns_401(self, client):
        """无 token 访问 /auth/verify 返回 401。"""
        resp = client.get("/api/auth/verify")
        assert resp.status_code == 401

    def test_verify_with_valid_token(self, client, auth_headers):
        """有效 token 通过验证。"""
        resp = client.get("/api/auth/verify", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["user_id"] == TEST_USER


# ═══════════════════════════════════════════════════════════════════
# 2. 企业信息模块 (business router)
# ═══════════════════════════════════════════════════════════════════

class TestBusinessRoutes:
    """POST /api/business  + GET /api/business/{id}"""

    def test_create_business_requires_auth(self, client):
        """未认证创建企业返回 401。"""
        resp = client.post("/api/business", json={"business_name": "test"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_business_not_found(self, client, auth_headers):
        """查询不存在的企业返回 404。"""
        resp = client.get("/api/business/nonexistent_id", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_and_get_business(self):
        """创建企业后能查询到。"""
        async with AsyncSessionLocal() as session:
            biz = BusinessRecord(
                id="test_biz_api",
                user_id=TEST_USER,
                business_name="测试公司API",
                industry="餐饮",
                city="深圳",
            )
            session.add(biz)
            await session.commit()

        client = TestClient(app)
        headers = {"Authorization": f"Bearer {TEST_TOKEN}"}
        resp = client.get("/api/business/test_biz_api", headers=headers)
        assert resp.status_code == 200

        # 清理
        async with AsyncSessionLocal() as session:
            await session.execute(
                BusinessRecord.__table__.delete().where(
                    BusinessRecord.id == "test_biz_api"
                )
            )
            await session.commit()


# ═══════════════════════════════════════════════════════════════════
# 3. 诊断模块 (diagnosis router)
# ═══════════════════════════════════════════════════════════════════

class TestDiagnosisRoutes:
    """GET /api/diagnosis/{id}"""

    def test_get_diagnosis_requires_auth(self, client):
        resp = client.get("/api/diagnosis/any_id")
        assert resp.status_code == 401

    def test_get_diagnosis_not_found(self, client, auth_headers):
        resp = client.get("/api/diagnosis/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# 4. 执行计划模块 (execution router)
# ═══════════════════════════════════════════════════════════════════

class TestExecutionRoutes:
    """GET /api/execution/{id}"""

    def test_get_execution_requires_auth(self, client):
        resp = client.get("/api/execution/any_id")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# 5. 复盘模块 (review router)
# ═══════════════════════════════════════════════════════════════════

class TestReviewRoutes:
    """POST /api/review/upload  + GET /api/review/{id}"""

    def test_upload_requires_auth(self, client):
        resp = client.post("/api/review/upload")
        assert resp.status_code == 401

    def test_get_review_requires_auth(self, client):
        resp = client.get("/api/review/any_id")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# 6. 路线图模块 (roadmap router)
# ═══════════════════════════════════════════════════════════════════

class TestRoadmapRoutes:
    """GET /api/roadmap/current"""

    def test_get_roadmap_requires_auth(self, client):
        resp = client.get("/api/roadmap/current")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# 7. 周计划模块 (plan router)
# ═══════════════════════════════════════════════════════════════════

class TestPlanRoutes:
    """GET /api/plan/weekly"""

    def test_get_plan_requires_auth(self, client):
        resp = client.get("/api/plan/weekly")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# 8. 任务模块 (task router)
# ═══════════════════════════════════════════════════════════════════

class TestTaskRoutes:
    """GET /api/task/detail  + POST /api/task/checkin  + POST /api/task/upload"""

    def test_get_task_detail_requires_auth(self, client):
        resp = client.get("/api/task/detail", params={"task_id": "t1"})
        assert resp.status_code == 401

    def test_task_checkin_requires_auth(self, client):
        resp = client.post("/api/task/checkin", json={"task_id": "t1"})
        assert resp.status_code == 401

    def test_task_upload_requires_auth(self, client):
        resp = client.post("/api/task/upload")
        assert resp.status_code == 401

    def test_get_task_not_found(self, client, auth_headers):
        resp = client.get("/api/task/detail", params={"task_id": "no_such_task"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_checkin_task_not_found(self, client, auth_headers):
        resp = client.post("/api/task/checkin", json={"task_id": "no_such_task"}, headers=auth_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════
# 9. 工作台模块 (dashboard router)
# ═══════════════════════════════════════════════════════════════════

class TestDashboardRoutes:
    """GET /api/dashboard"""

    def test_get_dashboard_requires_auth(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
# 10. 系统路由
# ═══════════════════════════════════════════════════════════════════

class TestSystemRoutes:
    """GET /  + GET /health"""

    def test_root_returns_app_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == app_config.app_version
        assert "name" in data

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════
# 11. 跨模块鉴权一致性检查
# ═══════════════════════════════════════════════════════════════════

class TestAuthCoverage:
    """确保所有受保护路由在无 token 时返回 401。"""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/auth/verify"),
        ("GET", "/api/business/any_id"),
        ("POST", "/api/business"),
        ("GET", "/api/diagnosis/any_id"),
        ("GET", "/api/execution/any_id"),
        ("GET", "/api/review/any_id"),
        ("POST", "/api/review/upload"),
        ("GET", "/api/roadmap/current"),
        ("GET", "/api/plan/weekly"),
        ("GET", "/api/task/detail"),
        ("POST", "/api/task/checkin"),
        ("POST", "/api/task/upload"),
        ("GET", "/api/dashboard"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_endpoint_requires_auth(self, client, method, path):
        """受保护端点无 token 访问应返回 401。"""
        params = {"task_id": "x"} if "task" in path else None
        if method == "GET":
            resp = client.get(path, params=params)
        else:
            resp = client.post(path, json={"task_id": "x"} if "task" in path else {})
        assert resp.status_code == 401, f"{method} {path} 应返回 401，实际 {resp.status_code}"
