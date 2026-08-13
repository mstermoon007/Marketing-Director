"""环境数据隔离测试（development / staging / production）。

覆盖 backend/config/settings 的「按环境分库 + 运行时防护」契约：
  - APP_ENV=development -> data/app_dev.db
  - APP_ENV=staging    -> data/app_staging.db（独立预发库，不与开发/生产混用）
  - APP_ENV=production -> data/app_prod.db
  - 显式 DATABASE_URL 始终优先
  - 以服务形态运行（CloudRun 注入 PORT）却解析到 app_dev.db -> 拒绝启动（RuntimeError）
  - 以服务形态运行的 staging / production（各自独立库）-> 允许启动（已隔离）

注意：每个测试通过 monkeypatch 临时改写环境变量后 reload settings 模块；
测试结束恢复 conftest 注入的原始 DATABASE_URL 并再次 reload，避免污染其它用例。
"""

import importlib
import os

import pytest

import backend.config.settings as settings


_TRACKED = ("PORT", "APP_ENV", "DATABASE_URL")


@pytest.fixture
def settings_env(monkeypatch):
    """在指定环境变量下 reload settings；测试后恢复原始环境并 reload 回 conftest 的临时库。

    usage::
        mod = settings_env(APP_ENV="staging")          # 仅设置 APP_ENV，其余清空
        mod = settings_env(PORT="8000", APP_ENV="staging")
    """
    saved = {k: os.environ.get(k) for k in _TRACKED}

    def _apply(**env):
        for k in _TRACKED:
            if env.get(k) is not None:
                monkeypatch.setenv(k, env[k])
            else:
                monkeypatch.delenv(k, raising=False)
        return importlib.reload(settings)

    yield _apply

    # 恢复 conftest 注入的临时库环境，并 reload 回原状态
    for k in _TRACKED:
        if saved[k] is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, saved[k])
    importlib.reload(settings)


# ── 按环境分库 ──
def test_development_resolves_dev_db(settings_env):
    mod = settings_env(APP_ENV="development")
    assert mod.DATABASE_URL.endswith("app_dev.db")


def test_staging_resolves_staging_db(settings_env):
    mod = settings_env(APP_ENV="staging")
    assert mod.DATABASE_URL.endswith("app_staging.db")


def test_production_resolves_prod_db(settings_env):
    mod = settings_env(APP_ENV="production")
    assert mod.DATABASE_URL.endswith("app_prod.db")


def test_unknown_env_falls_back_to_dev_db(settings_env):
    # 未识别的 APP_ENV 视为开发环境，落到 app_dev.db（隔离基线）
    mod = settings_env(APP_ENV="whatever")
    assert mod.DATABASE_URL.endswith("app_dev.db")


def test_explicit_database_url_wins(settings_env):
    mod = settings_env(DATABASE_URL="sqlite+aiosqlite:////tmp/ci_explicit.db")
    assert mod.DATABASE_URL == "sqlite+aiosqlite:////tmp/ci_explicit.db"


# ── 运行时防护（PORT = 服务形态）──
def test_served_instance_writing_dev_db_is_rejected(settings_env):
    # PORT 已设置（CloudRun），但未分库（APP_ENV 缺失、无 DATABASE_URL）-> app_dev.db -> 必须拒绝
    with pytest.raises(RuntimeError):
        settings_env(PORT="8000")


def test_served_staging_with_own_db_is_allowed(settings_env):
    # 预发服务：PORT 已设 + APP_ENV=staging -> app_staging.db（隔离，非 dev）-> 允许启动
    mod = settings_env(PORT="8000", APP_ENV="staging")
    assert mod.DATABASE_URL.endswith("app_staging.db")


def test_served_production_is_allowed(settings_env):
    mod = settings_env(PORT="8000", APP_ENV="production")
    assert mod.DATABASE_URL.endswith("app_prod.db")


def test_served_with_explicit_db_is_allowed(settings_env):
    # 服务形态 + 显式独立库（如托管 Postgres / 独立 sqlite）-> 允许
    mod = settings_env(PORT="8000", DATABASE_URL="sqlite+aiosqlite:////tmp/ci_served.db")
    assert mod.DATABASE_URL.endswith("ci_served.db")


def test_local_dev_without_port_is_allowed(settings_env):
    # 本地开发无 PORT，默认可写 app_dev.db，护栏不过度拦截
    mod = settings_env()
    assert mod.DATABASE_URL.endswith("app_dev.db")
