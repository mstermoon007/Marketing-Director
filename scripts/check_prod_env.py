#!/usr/bin/env python3
"""生产环境数据隔离护栏的 CI 自检。

验证 ``backend/config/settings`` 的「按环境分库 + 运行时防护」契约，确保
生产部署不会把客户数据写入开发库 data/app_dev.db：

  1. 误配拦截：生产服务形态（``PORT`` 已设置）却未分库
     （APP_ENV != production 且未指定独立 DATABASE_URL）-> 必须拒绝启动(RuntimeError)。
  2. 正确分库：APP_ENV=production -> 解析为 data/app_prod.db。
  3. 正确放行：生产服务 + 显式 DATABASE_URL(非 app_dev.db) -> 允许通过。
  4. 基线：开发环境（无 PORT）默认可写 app_dev.db，护栏不过度拦截。

退出码非 0 即护栏失效，CI 应判定失败。

用法（在仓库根目录执行）：
    python scripts/check_prod_env.py
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


# 确保仓库根目录在 sys.path，便于 `import backend.config.settings`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import backend.config.settings as settings  # ruff: ignore[module-import-not-at-top-of-file]


_TRACKED = ("PORT", "APP_ENV", "DATABASE_URL")


def _reload(**env: str | None) -> object:
    """在临时环境变量下重新加载 settings 模块，返回模块对象（失败则抛出）。"""
    saved = {k: os.environ.get(k) for k in _TRACKED}
    for k in _TRACKED:
        os.environ.pop(k, None)
    for k, v in env.items():
        if v is not None:
            os.environ[k] = v
    try:
        return importlib.reload(settings)
    finally:
        for k in _TRACKED:
            os.environ.pop(k, None)
            if saved[k] is not None:
                os.environ[k] = saved[k]


def _check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} {detail}")
        sys.exit(1)


def main() -> None:
    print("[check_prod_env] 验证生产环境数据隔离护栏...")

    # 1) 误配：生产服务拉起(PORT)但未分库 -> 必须被拦截
    try:
        _reload(PORT="8000")  # 默认 APP_ENV=development，DATABASE_URL 缺省 -> app_dev.db
        _check(
            "生产服务误配被拦截（PORT 已设却写 app_dev.db）",
            False,
            "：settings 不应在 PORT 下使用 app_dev.db 启动",
        )
    except RuntimeError:
        _check("生产服务误配被拦截（PORT 已设却写 app_dev.db）", True)

    # 2) 正确：APP_ENV=production -> app_prod.db
    mod = _reload(APP_ENV="production")
    _check(
        "APP_ENV=production -> app_prod.db",
        mod.DATABASE_URL.endswith("app_prod.db"),
        f"：实际 {mod.DATABASE_URL}",
    )

    # 2b) 正确：APP_ENV=staging -> app_staging.db（独立预发库，不与开发/生产混用）
    mod = _reload(APP_ENV="staging")
    _check(
        "APP_ENV=staging -> app_staging.db",
        mod.DATABASE_URL.endswith("app_staging.db"),
        f"：实际 {mod.DATABASE_URL}",
    )

    # 3) 正确：生产服务 + 独立 DATABASE_URL 允许通过
    try:
        _reload(
            PORT="8000",
            APP_ENV="production",
            DATABASE_URL="sqlite+aiosqlite:////tmp/ci_prod.db",
        )
        _check("生产服务 + 独立 DATABASE_URL 通过", True)
    except RuntimeError as exc:
        _check("生产服务 + 独立 DATABASE_URL 通过", False, f"：{exc}")

    # 3b) 正确：预发服务（PORT）+ APP_ENV=staging -> app_staging.db 允许启动（已隔离）
    try:
        _reload(PORT="8000", APP_ENV="staging")
        _check("预发服务(PORT) + APP_ENV=staging 隔离启动通过", True)
    except RuntimeError as exc:
        _check("预发服务(PORT) + APP_ENV=staging 隔离启动通过", False, f"：{exc}")

    # 4) 开发环境(无 PORT)默认可用 app_dev.db（基线，确保护栏不过度拦截）
    mod = _reload()
    _check(
        "开发环境(无 PORT)默认可用 app_dev.db",
        mod.DATABASE_URL.endswith("app_dev.db"),
        f"：实际 {mod.DATABASE_URL}",
    )

    print("[check_prod_env] 全部通过 ✅")


if __name__ == "__main__":
    main()
