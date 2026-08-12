#!/usr/bin/env python3
"""
依赖漂移检查 —— 校验 pyproject.toml 的依赖声明与代码实际 import 是否一致。

检查两个方向：
  1. 缺失（missing）：代码里 import 了，但 pyproject 没声明 → 生产环境会 ModuleNotFoundError
  2. 冗余（unused）：pyproject 声明了，但全项目零引用 → 拖慢安装、扩大攻击面

用 AST 而不是 grep：grep "^import" 抓不到函数内延迟导入和 try/except 软导入，
本项目的 langchain_core / openai / uvicorn 就全藏在缩进块里。

用法：
    python scripts/check_dependency_drift.py          # 检查，有漂移则退出码 1
    python scripts/check_dependency_drift.py -v       # 同时列出每个包的引用位置

接入 CI：直接把本脚本加进流水线，退出码非 0 即阻断。
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

import tomllib


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 扫描范围：运行时代码目录（tests/scripts 的依赖归 dev，不参与主依赖比对）
RUNTIME_DIRS = ["backend"]

# 本项目自有包名，不算第三方
FIRST_PARTY = {
    "backend", "tests", "agents", "api", "config", "db", "models",
    "services", "prompts", "skills", "utils", "agent_core", "conftest",
}

# 导入名 → PyPI 分发包名（两者不一致的情况）
IMPORT_TO_DIST = {
    "jwt": "pyjwt",
    "langchain_core": "langchain-core",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "multipart": "python-multipart",
    "PIL": "pillow",
    "sqlalchemy": "sqlalchemy",
}

# 隐式依赖白名单：无 import 但运行时必需，需写明理由，否则会被误判为冗余
IMPLICIT_DEPS = {
    "aiosqlite": "SQLAlchemy 按 DATABASE_URL 的 sqlite+aiosqlite:// 经 entry point 加载异步驱动",
    "python-multipart": "FastAPI 解析 UploadFile/File/Form 的运行时依赖",
}


def normalize(name: str) -> str:
    """PEP 503 包名规范化：忽略大小写，- _ . 视为等价，并剥离 extras。"""
    name = name.split("[")[0]
    return name.lower().replace("_", "-").replace(".", "-")


def collect_imports(dirs: list[str]) -> dict[str, list[str]]:
    """AST 扫描，返回 {顶层第三方模块名: [引用位置...]}。"""
    stdlib = set(sys.stdlib_module_names)
    found: dict[str, list[str]] = defaultdict(list)

    for d in dirs:
        for py in sorted((PROJECT_ROOT / d).rglob("*.py")):
            if "__pycache__" in py.parts or ".venv" in py.parts:
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            except SyntaxError as exc:
                print(f"  ! 跳过语法错误文件 {py}: {exc}", file=sys.stderr)
                continue

            rel = py.relative_to(PROJECT_ROOT)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    # level > 0 是相对导入，必为本项目代码
                    if node.level:
                        continue
                    mods = [node.module] if node.module else []
                else:
                    continue

                for mod in mods:
                    top = mod.split(".")[0]
                    if top in stdlib or top in FIRST_PARTY:
                        continue
                    found[top].append(f"{rel}:{node.lineno}")

    return dict(found)


def read_declared() -> list[str]:
    """读取 pyproject.toml 的 [project].dependencies 原始声明。"""
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    return data.get("project", {}).get("dependencies", [])


def read_requirements() -> dict[str, str]:
    """读取 requirements.txt 的包名（规范化）→ 原始行。"""
    path = PROJECT_ROOT / "requirements.txt"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pkg = line.split("==")[0].split(">=")[0].split("<")[0].split("~=")[0]
        out[normalize(pkg.strip())] = line
    return out


def check_requirements_sync(declared: dict[str, str]) -> bool:
    """requirements.txt 应与 pyproject 运行时依赖同集合（dev 测试包除外）。"""
    reqs = read_requirements()
    if not reqs:
        return True

    dev_only = {"pytest", "pytest-asyncio", "pytest-cov", "ruff", "black", "mypy"}
    req_runtime = {k for k in reqs if k not in dev_only}

    only_in_pyproject = set(declared) - req_runtime
    only_in_reqs = req_runtime - set(declared)

    if not only_in_pyproject and not only_in_reqs:
        print("[通过] requirements.txt 与 pyproject.toml 依赖集合一致。")
        return True

    if only_in_pyproject:
        print(f"[不同步] {len(only_in_pyproject)} 个包在 pyproject 有、requirements.txt 缺：")
        for p in sorted(only_in_pyproject):
            print(f"  - {p}")
    if only_in_reqs:
        print(f"[不同步] {len(only_in_reqs)} 个包在 requirements.txt 有、pyproject 缺：")
        for p in sorted(only_in_reqs):
            print(f"  - {reqs[p]}")
    return False


def main() -> int:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    imports = collect_imports(RUNTIME_DIRS)
    declared_raw = read_declared()

    # 声明侧：规范化包名 → 原始声明串
    declared: dict[str, str] = {}
    for spec in declared_raw:
        # 剥离版本约束，只留包名部分
        pkg = spec.split(">=")[0].split("==")[0].split("<")[0].split("~=")[0].split(";")[0]
        declared[normalize(pkg.strip())] = spec

    # 使用侧：导入名 → 分发包名
    used: dict[str, list[str]] = {}
    for mod, locs in imports.items():
        used[normalize(IMPORT_TO_DIST.get(mod, mod))] = locs

    missing = {k: v for k, v in used.items() if k not in declared}
    unused = {
        k: v for k, v in declared.items()
        if k not in used and k not in {normalize(x) for x in IMPLICIT_DEPS}
    }

    print("=" * 68)
    print("依赖漂移检查 —— pyproject.toml [project].dependencies vs backend/ 实际 import")
    print("=" * 68)
    print(f"\n扫描目录：{', '.join(RUNTIME_DIRS)}")
    print(f"实际引用第三方包：{len(used)} 个   已声明依赖：{len(declared)} 个\n")

    if verbose:
        print("-" * 68)
        print("引用明细：")
        for pkg in sorted(used):
            locs = used[pkg]
            print(f"  {pkg:<22} {len(locs):>2} 处   {locs[0]}")
        for pkg, reason in IMPLICIT_DEPS.items():
            if normalize(pkg) in declared:
                print(f"  {pkg:<22} 隐式   {reason}")
        print("-" * 68 + "\n")

    ok = True

    if missing:
        ok = False
        print(f"[缺失] {len(missing)} 个包被 import 但未声明，生产环境会 ModuleNotFoundError：")
        for pkg in sorted(missing):
            print(f"  - {pkg}")
            for loc in missing[pkg][:3]:
                print(f"      {loc}")
        print()

    if unused:
        ok = False
        print(f"[冗余] {len(unused)} 个包已声明但全项目零引用，建议删除：")
        for pkg in sorted(unused):
            print(f"  - {declared[pkg]}")
        print()

    if ok:
        print("[通过] 依赖漂移为零：声明与 import 完全一致。")
        for pkg, reason in IMPLICIT_DEPS.items():
            if normalize(pkg) in declared:
                print(f"       （隐式依赖已登记：{pkg} —— {reason}）")

    if not check_requirements_sync(declared):
        ok = False

    if ok:
        return 0

    print("\n[失败] 存在依赖漂移，请修正后重跑。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
