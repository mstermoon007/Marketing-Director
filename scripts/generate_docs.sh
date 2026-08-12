#!/usr/bin/env bash
# =============================================================================
# generate_docs.sh —— 文档自动生成脚本
#
# 从代码源自动刷新 README 中的以下章节：
#   - 📘 API 文档：从 FastAPI OpenAPI 自动生成端点分组表
#   - 📱 小程序页面清单：从 frontend/app.json 自动提取
#
# 用法：
#   bash scripts/generate_docs.sh          # 刷新 README
#   bash scripts/generate_docs.sh --dry-run # 仅打印即将写入的内容，不修改文件
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false

if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
    echo "[generate_docs] DRY-RUN 模式，不会修改文件"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

README="$PROJECT_ROOT/README.md"
APP_JSON="$PROJECT_ROOT/frontend/app.json"

# 自动检测可用的 Python3（只需 stdlib json，任意版本均可）
_find_python3() {
    for py in \
        "$PROJECT_ROOT/.venv/bin/python3" \
        "$PROJECT_ROOT/.venv/bin/python" \
        "/Library/Frameworks/Python.framework/Versions/3.15/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
        "/usr/local/bin/python3" \
        "/usr/bin/python3" \
        "$(which python3 2>/dev/null || true)"; do
        if [ -x "$py" ]; then
            echo "$py"
            return 0
        fi
    done
    echo "python3"
}
PYTHON3=$(_find_python3)

# ------ 1. 读取已有 OpenAPI 文档（由 extract_routes.py 手动更新）------
echo "[generate_docs] 读取 data/openapi.json ..."
OPENAPI_JSON="$PROJECT_ROOT/data/openapi.json"

if [ ! -f "$OPENAPI_JSON" ]; then
    echo -e "  ${RED}✗${NC} data/openapi.json 不存在，请先运行: python scripts/extract_routes.py --save-openapi data/openapi.json"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} data/openapi.json 已就绪"
echo ""

# ------ 2. 生成 API 端点分组表 ------
echo "[generate_docs] 生成 API 端点分组表..."

API_TABLE=$("$PYTHON3" -c "
import json, sys
from collections import Counter

# 读取 openapi.json
with open('$OPENAPI_JSON') as f:
    spec = json.load(f)

paths = spec.get('paths', {})

# 按标签聚合
tag_counter = Counter()
tag_descriptions = {}
for path, methods in paths.items():
    for method, detail in methods.items():
        if method.upper() in ('HEAD', 'OPTIONS'):
            continue
        for tag in detail.get('tags', ['未分类']):
            tag_counter[tag] += 1
        # 用第一个 summary 作为 tag 的描述
        if tag_counter:
            primary_tag = detail.get('tags', ['未分类'])[0]
            if primary_tag not in tag_descriptions:
                tag_descriptions[primary_tag] = detail.get('summary', '')

# 标签排序
tag_order = [
    'Agent 对话', '认证', '企业信息', '诊断', '执行计划',
    '路线图', '周计划', '任务', '工作台', '复盘', '闭环业务', '系统'
]
ordered_tags = [t for t in tag_order if t in tag_counter]
# 追加未分类的
for t in sorted(tag_counter):
    if t not in ordered_tags:
        ordered_tags.append(t)

total = sum(tag_counter.values())

# 输出 markdown 表格
print('| 标签 | 接口数 | 说明 |')
print('| :--- | :--- | :--- |')
for tag in ordered_tags:
    count = tag_counter[tag]
    desc_map = {
        'Agent 对话': '对话、流式、历史',
        '认证': '登录、Token 验证',
        '企业信息': '创建、查询',
        '诊断': '启动诊断、查询结果',
        '执行计划': '生成计划、查询计划',
        '路线图': '当前路线图',
        '周计划': '周计划查询',
        '任务': '任务详情、打卡、上传',
        '工作台': '看板数据汇总',
        '复盘': '上传材料、生成报告、查询',
        '闭环业务': '确认/编辑/重新生成计划、日程打卡/同步、文件/指标上传、复盘触发/采纳、反馈',
        '系统': '根路径、健康检查',
    }
    desc = desc_map.get(tag, '-')
    print(f'| {tag} | {count} | {desc} |')
print()
print(f'> **接口总数：{total} 个**（含 2 个公开端点 + {total-2} 个 JWT 鉴权端点）')
")

echo "  API 端点分组表已生成"
echo ""

# ------ 3. 生成小程序页面清单 ------
echo "[generate_docs] 生成小程序页面清单..."

PAGE_TABLE=$("$PYTHON3" -c "
import json

with open('$APP_JSON') as f:
    data = json.load(f)

lines = []
# 主包页面
for p in data.get('pages', []):
    lines.append(f'| 主包 | {p} | - |')

# 分包页面
for sub in data.get('subpackages', []):
    root = sub.get('root', '')
    for p in sub.get('pages', []):
        full_path = f'{root}/{p}'
        lines.append(f'| 分包 | {full_path} | - |')

for line in lines:
    print(line)
")

echo "  页面清单已生成"
echo ""

# ------ 4. 更新 README.md 中的 AUTO-GEN 标记位 ------
if [ "$DRY_RUN" = true ]; then
    echo "[generate_docs] DRY-RUN: 以下为将写入 README.md 的内容"
    echo ""
    echo "--- API 端点分组表 ---"
    echo "$API_TABLE"
    echo ""
    echo "--- 页面清单 ---"
    echo "$PAGE_TABLE"
    exit 0
fi

# 用 python 做标记位替换（sed 处理多行内容不够可靠）
"$PYTHON3" -c "
import re

readme_path = '$README'
with open(readme_path, 'r') as f:
    content = f.read()

# 替换 API 块
api_table = '''$API_TABLE'''
api_pattern = r'(<!-- AUTO-GEN-API-START -->)(.*?)(<!-- AUTO-GEN-API-END -->)'
content = re.sub(api_pattern, r'\1\n' + api_table + r'\n\3', content, flags=re.DOTALL)

# 替换页面块
page_table = '''$PAGE_TABLE'''
page_pattern = r'(<!-- AUTO-GEN-PAGES-START -->)(.*?)(<!-- AUTO-GEN-PAGES-END -->)'
content = re.sub(page_pattern, r'\1\n' + page_table + r'\n\3', content, flags=re.DOTALL)

with open(readme_path, 'w') as f:
    f.write(content)
"

echo -e "  ${GREEN}✓${NC} README.md 已更新（API 端点 + 页面清单）"
echo ""

echo "============================================================"
echo -e "  ${GREEN}✓ 文档自动生成完成${NC}"
echo "============================================================"
