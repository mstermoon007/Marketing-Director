"""
Prompt 模板加载器
参考开发思路文档：第5.2节 — Prompt与代码分离，用jinja2模板管理

所有 Prompt 存储在 src/prompts/ 目录下的 .txt 文件中。
加载器负责读取模板文件并注入变量。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound


# 模板目录
TEMPLATES_DIR = Path(__file__).resolve().parent

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def load_prompt(
    template_path: str,
    **variables
) -> str:
    """
    加载 Prompt 模板并注入变量

    Args:
        template_path: 相对于 prompts/ 目录的路径，如 "diagnosis/system.txt"
        **variables: 模板变量

    Returns:
        渲染后的 Prompt 文本

    Raises:
        FileNotFoundError: 模板文件不存在
    """
    # 短名别名 → 实际模板路径（方便外部用"diagnosis"而不是完整路径）
    SHORTCUTS = {
        "diagnosis": "diagnosis/system.txt",
        "executor": "executor/system.txt",
        "reviewer": "reviewer/report.txt",
        "reviewer_parse_image": "reviewer/parse_image.txt",
    }
    path = SHORTCUTS.get(template_path, template_path)
    try:
        template = _env.get_template(path)
        return template.render(**variables)
    except TemplateNotFound as exc:
        raise FileNotFoundError(
            f"Prompt 模板不存在: prompts/{template_path}"
        ) from exc


# 内部别名：兼容测试对 _jinja 的引用
_jinja = load_prompt


def load_raw_prompt(template_path: str) -> str:
    """
    加载原始模板内容（不注入变量）

    Args:
        template_path: 相对于 prompts/ 目录的路径

    Returns:
        原始模板文本
    """
    file_path = TEMPLATES_DIR / template_path
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt 模板不存在: {file_path}")
    return file_path.read_text(encoding="utf-8")


def list_available_prompts() -> list[str]:
    """列出所有可用的 Prompt 模板"""
    prompts = []
    for f in TEMPLATES_DIR.rglob("*.txt"):
        prompts.append(str(f.relative_to(TEMPLATES_DIR)))
    return sorted(prompts)


def validate_template_structure() -> bool:
    """
    验证 Prompt 模板目录结构是否完整
    参考文档要求的模板：
    - diagnosis/system.txt
    - executor/system.txt
    - reviewer/report.txt
    - reviewer/parse_image.txt
    """
    required = [
        "diagnosis/system.txt",
        "executor/system.txt",
        "reviewer/report.txt",
        "reviewer/parse_image.txt",
    ]
    missing = []
    for path in required:
        if not (TEMPLATES_DIR / path).exists():
            missing.append(path)
    return len(missing) == 0


def load_prompt_with_skill(
    template_path: str,
    industry: str = "",
    **variables
) -> str:
    """
    加载 Prompt 模板并注入行业技能

    在加载 Prompt 模板的同时，根据行业自动加载对应的行业技能文件，
    将技能内容作为 {{ skill_context }} 变量注入到模板中。

    Args:
        template_path: Prompt 模板路径
        industry: 行业名称（如"家装"、"餐饮"）
        **variables: 其他模板变量

    Returns:
        渲染后的 Prompt 文本（含行业技能注入）
    """
    from src.skills import get_skill_injection

    # 优先使用显式传入的 skill_content（测试/注入场景），否则从磁盘加载行业技能
    if "skill_content" in variables and variables["skill_content"]:
        variables["skill_context"] = variables.pop("skill_content")
    else:
        skill_context = get_skill_injection(industry)
        variables["skill_context"] = skill_context

    return load_prompt(template_path, **variables)
