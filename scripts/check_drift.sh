#!/usr/bin/env bash
# =============================================================================
# check_drift.sh —— 项目漂移检查（提交前自动执行）
#
# 检查 5 个维度：
#   1. pyproject.toml 依赖 vs 实际 import（复用 check_dependency_drift.py）
#   2. app.json 页面声明 vs .wxml 文件数
#   3. TypeScript @deprecated 残留
#   4. 硬编码密钥模式（ghp_ / sk- / 等）
#   5. .env.example vs 代码中 os.getenv() 引用
#
# 返回非零时阻塞提交，输出具体漂移项。
# 用法：bash scripts/check_drift.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 自动检测可用的 Python3（任意版本均可，依赖/页面/废弃/密钥检查只需 stdlib）
_find_python3() {
    for py in \
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

EXIT_CODE=0
IS_PRECHOMMIT=false

# 检测是否从 git hook 调用（pre-commit 环境变量）
if [ "${PRE_COMMIT_DRIFT_CHECK:-}" = "1" ]; then
    IS_PRECHOMMIT=true
fi

# 非 pre-commit 模式也强制设置，确保子脚本能感知
export PRE_COMMIT_DRIFT_CHECK=1

echo "============================================================"
echo "  项目漂移检查 · check_drift.sh"
echo "============================================================"
echo ""

# ------ 检查 1：依赖漂移 ------
echo "  [1/5] 依赖漂移：pyproject.toml vs 实际 import ..."
if $PYTHON3 "$SCRIPT_DIR/check_dependency_drift.py"; then
    echo -e "  ${GREEN}✓ 通过${NC}"
else
    echo -e "  ${RED}✗ 失败${NC}"
    EXIT_CODE=1
fi
echo ""

# ------ 检查 2：页面声明 vs .wxml ------
echo "  [2/5] 页面漂移：app.json 声明 vs .wxml 文件 ..."

APP_JSON="$PROJECT_ROOT/frontend/app.json"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

if [ ! -f "$APP_JSON" ]; then
    echo -e "  ${RED}✗ 失败：frontend/app.json 不存在${NC}"
    EXIT_CODE=1
else
    # 提取 app.json 声明的页面（主包 + 分包）
    # 用 python3 做 JSON 解析
    DECLARED_PAGES=$($PYTHON3 -c "
import json, sys
with open('$APP_JSON') as f:
    data = json.load(f)
pages = list(data.get('pages', []))
for sub in data.get('subpackages', []):
    root = sub.get('root', '')
    for p in sub.get('pages', []):
        pages.append(f'{root}/{p}')
print(len(pages))
for p in sorted(pages):
    print(p)
")
    DECLARED_COUNT=$(echo "$DECLARED_PAGES" | head -1)

    # 统计 pages/ 下所有 .wxml 文件（排除 components/）
    WXML_FILES=$(find "$FRONTEND_DIR/pages" -name "*.wxml" -type f | sort)
    WXML_COUNT=$(echo "$WXML_FILES" | wc -l | tr -d ' ')

    # 每个声明页面应有对应的 .wxml
    MISSING_WXML=0
    DECLARED_PAGE_LIST=$(echo "$DECLARED_PAGES" | tail -n +2)
    while IFS= read -r page; do
        [ -z "$page" ] && continue
        wxml_path="$FRONTEND_DIR/$page.wxml"
        if [ ! -f "$wxml_path" ]; then
            echo -e "  ${RED}✗ app.json 声明了 '$page' 但对应 .wxml 不存在${NC}"
            MISSING_WXML=$((MISSING_WXML + 1))
        fi
    done <<< "$DECLARED_PAGE_LIST"

    if [ "$MISSING_WXML" -eq 0 ] && [ "$DECLARED_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✓ 通过（${DECLARED_COUNT} 个页面声明，${WXML_COUNT} 个 .wxml 文件）${NC}"
    else
        EXIT_CODE=1
    fi
fi
echo ""

# ------ 检查 3：@deprecated 残留 ------
echo "  [3/5] 类型漂移：@deprecated 残留 ..."
DEPRECATED=$(grep -rn '@deprecated' "$PROJECT_ROOT/frontend/types" 2>/dev/null || true)
if [ -z "$DEPRECATED" ]; then
    echo -e "  ${GREEN}✓ 通过（零 @deprecated 残留）${NC}"
else
    echo -e "  ${RED}✗ 发现 @deprecated 残留：${NC}"
    echo "$DEPRECATED" | while IFS= read -r line; do
        echo -e "  ${YELLOW}$line${NC}"
    done
    EXIT_CODE=1
fi
echo ""

# ------ 检查 4：硬编码密钥 ------
echo "  [4/5] 安全漂移：硬编码密钥模式 ..."
# 排除 .env.example, node_modules, __pycache__, data, .git, .workbuddy
KEY_PATTERNS=(
    'ghp_[A-Za-z0-9_]{36,}'        # GitHub PAT
    'sk-[A-Za-z0-9]{32,}'          # OpenAI / common API key
    'sk-or-[A-Za-z0-9]{32,}'       # OpenRouter
    'sk-ant-[A-Za-z0-9]{32,}'      # Anthropic
    'AIza[0-9A-Za-z_-]{35}'        # Google API
    'dckr_pat_[A-Za-z0-9_-]{27,}'  # Docker Hub PAT
    'glpat-[A-Za-z0-9_-]{20,}'     # GitLab PAT
)
KEY_HITS=""
for pat in "${KEY_PATTERNS[@]}"; do
    hits=$(grep -rn --include="*.py" --include="*.ts" --include="*.js" \
        --include="*.json" --include="*.yaml" --include="*.yml" --include="*.toml" \
        --include="*.sh" --include="*.md" \
        --exclude-dir=node_modules --exclude-dir=__pycache__ \
        --exclude-dir=data --exclude-dir=.git --exclude-dir=.workbuddy \
        --exclude-dir=.venv --exclude-dir=dist \
        "$pat" "$PROJECT_ROOT" 2>/dev/null || true)
    # 排除 .env.example
    hits=$(echo "$hits" | grep -v '.env.example' || true)
    if [ -n "$hits" ]; then
        KEY_HITS="$KEY_HITS$hits"$'\n'
    fi
done
KEY_HITS=$(echo "$KEY_HITS" | sort -u | grep -v '^$' || true)

if [ -z "$KEY_HITS" ]; then
    echo -e "  ${GREEN}✓ 通过（零硬编码密钥）${NC}"
else
    echo -e "  ${RED}✗ 发现疑似硬编码密钥：${NC}"
    echo "$KEY_HITS" | while IFS= read -r line; do
        [ -z "$line" ] && continue
        echo -e "  ${YELLOW}  $line${NC}"
    done
    EXIT_CODE=1
fi
echo ""

# ------ 检查 5：环境变量覆盖 ------
echo "  [5/5] 配置漂移：.env.example vs 代码引用 ..."
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
if [ ! -f "$ENV_EXAMPLE" ]; then
    echo -e "  ${RED}✗ 失败：.env.example 不存在${NC}"
    EXIT_CODE=1
else
    # 提取 .env.example 中声明的变量名
    DECLARED_ENV=$(grep -oE '^[A-Z][A-Z0-9_]+' "$ENV_EXAMPLE" | sort -u)

    # 提取代码中所有 os.getenv / os.environ.get 引用的环境变量名
    # 用 python3 做 AST 级提取，同时捕获单行和多行 os.getenv() 调用
    CODE_ENV=$($PYTHON3 -c "
import ast, os, sys
vars_found = set()
for root, dirs, files in os.walk('$PROJECT_ROOT/backend'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv')]
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        try:
            tree = ast.parse(open(path).read(), filename=path)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                obj = node.func.value if hasattr(node.func, 'value') else None
                # os.getenv(...) or os.environ.get(...)
                if isinstance(obj, ast.Attribute) and obj.attr == 'environ' and isinstance(obj.value, ast.Name) and obj.value.id == 'os' and node.func.attr == 'get':
                    pass  # os.environ.get
                elif isinstance(obj, ast.Name) and obj.id == 'os' and node.func.attr == 'getenv':
                    pass  # os.getenv
                else:
                    continue
                if node.args and isinstance(node.args[0], ast.Constant):
                    var = node.args[0].value
                    if isinstance(var, str) and var.isupper():
                        vars_found.add(var)
for v in sorted(vars_found):
    print(v)
")

    # 代码引用但 .env.example 缺失的
    MISSING_IN_EXAMPLE=0
    while IFS= read -r var; do
        [ -z "$var" ] && continue
        if ! echo "$DECLARED_ENV" | grep -qxF "$var"; then
            echo -e "  ${RED}✗ 代码引用了 '$var' 但 .env.example 未声明${NC}"
            MISSING_IN_EXAMPLE=$((MISSING_IN_EXAMPLE + 1))
        fi
    done <<< "$CODE_ENV"

    # .env.example 声明但代码未引用的（仅告警，不阻断）
    ORPHAN_IN_ENV=0
    while IFS= read -r var; do
        [ -z "$var" ] && continue
        if ! echo "$CODE_ENV" | grep -qxF "$var"; then
            echo -e "  ${YELLOW}⚠ .env.example 声明了 '$var' 但代码中未引用（可能为预备变量）${NC}"
            ORPHAN_IN_ENV=$((ORPHAN_IN_ENV + 1))
        fi
    done <<< "$DECLARED_ENV"

    if [ "$MISSING_IN_EXAMPLE" -eq 0 ]; then
        echo -e "  ${GREEN}✓ 通过（.env.example 覆盖所有代码引用）${NC}"
    else
        EXIT_CODE=1
    fi
    if [ "$ORPHAN_IN_ENV" -gt 0 ]; then
        echo -e "  ${YELLOW}  （${ORPHAN_IN_ENV} 个预备变量未在代码中引用，不阻断）${NC}"
    fi
fi
echo ""

# ------ 汇总 ------
echo "============================================================"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "  ${GREEN}✓ 全部 5 项检查通过，零漂移${NC}"
else
    echo -e "  ${RED}✗ 存在漂移项，请修复后重试${NC}"
fi
echo "============================================================"

exit $EXIT_CODE
