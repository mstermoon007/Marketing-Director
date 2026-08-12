"""
API 端点清单提取脚本 —— 从 FastAPI app 中提取所有已注册路由。

用法：
    python scripts/extract_routes.py             # 打印表格
    python scripts/extract_routes.py --json       # 输出 JSON
    python scripts/extract_routes.py --save-openapi /path/to/openapi.json  # 保存 OpenAPI 文档
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.api.main import app


def extract_routes():
    """提取所有路由，返回 (path, method, summary, tags) 列表。"""
    # 触发 openapi() 强制 FastAPI 解析所有 include_router 注册的路由
    openapi_spec = app.openapi()
    paths = openapi_spec.get("paths", {})

    routes = []
    for path, methods in paths.items():
        for method, detail in methods.items():
            if method.upper() in ("HEAD", "OPTIONS"):
                continue
            summary = detail.get("summary", "")
            tags = detail.get("tags", [])
            routes.append({
                "path": path,
                "method": method.upper(),
                "summary": summary,
                "tags": tags,
            })
    # 按 path 排序
    routes.sort(key=lambda r: (r["path"], r["method"]))
    return routes, openapi_spec


def print_table(routes):
    """格式化打印端点表格。"""
    print(f"\n{'=' * 80}")
    print(f"  API 端点清单（共 {len(routes)} 个接口）")
    print(f"{'=' * 80}")
    print(f"{'方法':<8} {'路径':<45} {'说明':<30} {'标签'}")
    print("-" * 80)
    for r in routes:
        tags_str = ", ".join(r["tags"]) if r["tags"] else "-"
        print(f"{r['method']:<8} {r['path']:<45} {r['summary'][:28]:<30} {tags_str}")
    print("-" * 80)
    print(f"  共计 {len(routes)} 个接口")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="API 端点清单提取")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--save-openapi", type=str, help="保存 OpenAPI JSON 到指定路径")
    args = parser.parse_args()

    if args.save_openapi:
        openapi_spec = app.openapi()
        output_path = Path(args.save_openapi)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(openapi_spec, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OpenAPI 文档已保存至: {output_path}")
        return

    routes, openapi_spec = extract_routes()
    if args.json:
        print(json.dumps(routes, ensure_ascii=False, indent=2))
    else:
        print_table(routes)


if __name__ == "__main__":
    main()
