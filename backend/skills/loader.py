"""
行业技能加载器 v2
参考开发思路文档：技能模块 — 按行业分类存储营销知识和方法论

功能：
- 根据行业名称匹配对应的技能（支持单文件和目录两种组织方式）
- 目录模式下按子文件分类加载（诊断标准、渠道、指标、客户画像、案例）
- 将技能内容注入到 Prompt 中，提升诊断质量
- 支持行业别名映射和地产子类细分

技能存储结构：
1. 单文件模式：industry_skills/{skill_name}.md（旧格式，兼容保留）
2. 目录模式：skills/{industry_dir}/ 下多个 .md 文件（新格式，更结构化）
"""

import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)

# 两个技能目录：旧的 industry_skills/ 和新的 skills/
INDUSTRY_SKILLS_DIR = Path(__file__).resolve().parent / "industry_skills"
SKILLS_DIR = Path(__file__).resolve().parent

# 行业别名映射：将用户填写的行业名称映射到技能目录名
# value 格式: "dir:dirname" 表示目录模式, "file:filename" 表示单文件模式
INDUSTRY_ALIASES = {
    # ── 地产（核心，目录模式）──
    "地产": ("dir", "real_estate"),
    "房地产": ("dir", "real_estate"),
    "房产": ("dir", "real_estate"),
    "房产中介": ("dir", "real_estate"),
    "房产经纪": ("dir", "real_estate"),
    "中介": ("dir", "real_estate"),
    "二手房中介": ("dir", "real_estate"),
    "新房代理": ("dir", "real_estate"),
    "商铺租赁": ("dir", "real_estate"),
    "地产经纪": ("dir", "real_estate"),
    "置业顾问": ("dir", "real_estate"),
    # ── 家装（单文件）──
    "家装": ("file", "renovation"),
    "装修": ("file", "renovation"),
    "装饰": ("file", "renovation"),
    "装潢": ("file", "renovation"),
    "室内设计": ("file", "renovation"),
    # ── 餐饮（单文件）──
    "餐饮": ("file", "restaurant"),
    "餐厅": ("file", "restaurant"),
    "饭店": ("file", "restaurant"),
    "美食": ("file", "restaurant"),
    # 餐饮细分 / 饮品（统一映射到 restaurant 技能）
    "咖啡": ("file", "restaurant"),
    "咖啡馆": ("file", "restaurant"),
    "咖啡店": ("file", "restaurant"),
    "茶饮": ("file", "restaurant"),
    "奶茶": ("file", "restaurant"),
    "饮品": ("file", "restaurant"),
    "小吃": ("file", "restaurant"),
    "快餐": ("file", "restaurant"),
    "火锅": ("file", "restaurant"),
    "烧烤": ("file", "restaurant"),
    "面馆": ("file", "restaurant"),
    "饭馆": ("file", "restaurant"),
    "餐吧": ("file", "restaurant"),
    "烘焙": ("file", "restaurant"),
    "面包": ("file", "restaurant"),
    "甜品": ("file", "restaurant"),
    "烘焙坊": ("file", "restaurant"),
    # ── 教培（单文件）──
    "教培": ("file", "education"),
    "培训": ("file", "education"),
    "教育": ("file", "education"),
    # ── 美业（单文件）──
    "美容": ("file", "beauty"),
    "美发": ("file", "beauty"),
    "美业": ("file", "beauty"),
    "美容院": ("file", "beauty"),
    # ── 通用（单文件）──
    "其他": ("file", "generic"),
    "其它": ("file", "generic"),
    # ── 知识库专属行业标签（无独立技能文件，回退到最接近技能或通用）──
    "房产中介": ("dir", "real_estate"),
    "零售便利店": ("file", "generic"),
    "母婴店": ("file", "generic"),
    "健身房": ("file", "generic"),
    "宠物店": ("file", "generic"),
    "花店": ("file", "generic"),
    "服装店": ("file", "generic"),
    "摄影馆": ("file", "generic"),
}

# 行业标准化映射：用户说法（含细分）-> 知识库行业标签。
# 知识库卡片的 industry 元数据使用这些标签（餐饮 / 烘焙坊 / 家装 / 教培 / 美业 /
# 房产中介 / 零售便利店 / 母婴店 / 健身房 / 宠物店 / 花店 / 服装店 / 美容院 /
# 摄影馆 / 通用）。detect_industry 返回此标签，确保 RAG 按行业过滤能精确命中。
INDUSTRY_CANONICAL: dict[str, str] = {
    # 餐饮 / 饮品 -> 餐饮
    "餐饮": "餐饮", "餐厅": "餐饮", "饭店": "餐饮", "美食": "餐饮",
    "饭馆": "餐饮", "餐吧": "餐饮",
    "咖啡": "餐饮", "咖啡馆": "餐饮", "咖啡店": "餐饮",
    "茶饮": "餐饮", "奶茶": "餐饮", "饮品": "餐饮",
    "小吃": "餐饮", "快餐": "餐饮", "火锅": "餐饮", "烧烤": "餐饮", "面馆": "餐饮",
    # 烘焙 -> 烘焙坊（知识库独立标签）
    "烘焙": "烘焙坊", "面包": "烘焙坊", "甜品": "烘焙坊", "烘焙坊": "烘焙坊",
    # 家装
    "家装": "家装", "装修": "家装", "装饰": "家装", "装潢": "家装", "室内设计": "家装",
    # 教培
    "教培": "教培", "培训": "教培", "教育": "教培",
    # 美业
    "美业": "美业", "美容": "美业", "美发": "美业", "美容院": "美容院",
    # 地产 -> 房产中介
    "地产": "房产中介", "房地产": "房产中介", "房产": "房产中介", "中介": "房产中介",
    "二手房中介": "房产中介", "新房代理": "房产中介", "商铺租赁": "房产中介",
    "地产经纪": "房产中介", "置业顾问": "房产中介", "房产中介": "房产中介",
    # 零售
    "零售": "零售便利店", "便利店": "零售便利店", "超市": "零售便利店",
    # 母婴
    "母婴": "母婴店", "孕婴": "母婴店",
    # 健身
    "健身": "健身房", "瑜伽": "健身房",
    # 宠物
    "宠物": "宠物店",
    # 花店
    "花店": "花店",
    # 服装
    "服装": "服装店", "服饰": "服装店", "女装": "服装店", "男装": "服装店",
    # 摄影
    "摄影": "摄影馆", "写真": "摄影馆",
    # 通用
    "其他": "通用", "其它": "通用",
}

# 地产行业子类映射（用于前端选择更精细的定位）
REAL_ESTATE_SUBCATEGORIES = {
    "二手房中介": "real_estate",
    "新房代理": "real_estate",
    "商铺租赁": "real_estate",
    "综合地产": "real_estate",
}

# 目录模式下各子文件的用途分类
# 文件名 -> 在诊断中的角色
SKILL_FILE_ROLES = {
    "diagnosis_criteria.md": "criteria",       # 诊断标准（评分维度）
    "channels.md": "channels",                 # 获客渠道策略
    "metrics.md": "metrics",                   # 行业指标基准
    "customer_profiles.md": "profiles",        # 客户画像与心理
    "case_studies.md": "cases",                # 诊断案例库
}


def match_industry_skill(industry: str) -> Optional[str]:
    """
    根据行业名称匹配对应的技能（兼容旧接口，返回完整文本）

    Args:
        industry: 用户填写的行业名称

    Returns:
        合并后的技能文本，未匹配返回 None
    """
    if not industry:
        return None

    skill_type, skill_name = _resolve_industry(industry)

    if skill_type == "dir":
        return _load_directory_skill(skill_name)
    else:
        return _load_file_skill(skill_name)


def _resolve_industry(industry: str) -> tuple:
    """
    解析行业名称，返回 (type, name)

    Returns:
        ("dir", "real_estate") 或 ("file", "renovation")
    """
    # 精确匹配
    if industry in INDUSTRY_ALIASES:
        return INDUSTRY_ALIASES[industry]

    # 模糊匹配
    for alias, result in INDUSTRY_ALIASES.items():
        if alias in industry or industry in alias:
            logger.info("行业模糊匹配: '%s' → '%s' → %s", industry, alias, result[1])
            return result

    # 未匹配，返回通用
    logger.info("行业 '%s' 未匹配到专用技能，使用通用技能", industry)
    return ("file", "generic")


def _load_file_skill(file_name: str) -> Optional[str]:
    """加载单文件技能"""
    skill_path = INDUSTRY_SKILLS_DIR / f"{file_name}.md"
    if not skill_path.exists():
        logger.warning("单文件技能不存在: %s", skill_path)
        return None

    content = skill_path.read_text(encoding="utf-8")
    logger.info("加载单文件技能: %s (%d字符)", skill_path.name, len(content))
    return content


def _load_directory_skill(dir_name: str) -> Optional[str]:
    """
    加载目录模式的技能（合并所有子文件）

    目录下的 .md 文件按文件名排序合并。
    合并时添加文件分隔符，保持结构化。
    """
    dir_path = SKILLS_DIR / dir_name
    if not dir_path.is_dir():
        logger.warning("目录技能不存在: %s", dir_path)
        return None

    md_files = sorted(dir_path.glob("*.md"))
    if not md_files:
        logger.warning("目录技能为空: %s", dir_path)
        return None

    parts = []
    for f in md_files:
        content = f.read_text(encoding="utf-8").strip()
        if content:
            file_name = f.stem
            role = SKILL_FILE_ROLES.get(f.name, "reference")
            parts.append(f"### [{file_name}] ({role})\n{content}")
            logger.info("  加载子文件: %s (%d字符)", f.name, len(content))

    merged = "\n\n".join(parts)
    logger.info("加载目录技能: %s (%d子文件, %d字符)", dir_name, len(md_files), len(merged))
    return merged


def load_skill_separated(industry: str) -> dict:
    """
    按用途分类加载目录技能（用于精细化注入）

    Returns:
        {"criteria": "...", "channels": "...", "metrics": "...", ...}
        如果是单文件模式或未匹配，返回 {"full_content": "..."}
    """
    if not industry:
        return {}

    skill_type, skill_name = _resolve_industry(industry)

    if skill_type != "dir":
        content = _load_file_skill(skill_name)
        return {"full_content": content} if content else {}

    dir_path = SKILLS_DIR / skill_name
    if not dir_path.is_dir():
        return {}

    result = {}
    for f in dir_path.glob("*.md"):
        role = SKILL_FILE_ROLES.get(f.name, "reference")
        result[role] = f.read_text(encoding="utf-8").strip()

    return result


def get_skill_injection(industry: str) -> str:
    """
    获取注入到 Prompt 中的行业技能文本

    格式化为 system prompt 可直接拼接的形式。
    对地产行业（目录模式），额外注入诊断框架指引。

    Args:
        industry: 行业名称

    Returns:
        格式化的技能文本
    """
    if not industry:
        return ""

    skill_type, skill_name = _resolve_industry(industry)

    if skill_type == "dir":
        return _get_dir_skill_injection(skill_name, industry)
    else:
        return _get_file_skill_injection(skill_name)


def _get_dir_skill_injection(dir_name: str, industry: str) -> str:
    """目录模式的技能注入（地产专用）"""
    separated = load_skill_separated(industry)

    parts = ["## 行业专属知识（诊断时请参考以下行业信息）\n"]

    # 诊断标准（最优先）
    if "criteria" in separated:
        parts.append(f"""
<diagnosis_framework>
以下是{industry}行业的专属诊断标准和评分维度，请严格按照此框架进行诊断：

{separated['criteria']}
</diagnosis_framework>

请严格按照上述诊断框架，从每个维度逐一评估企业现状，给出具体分数和问题分析。
""")

    # 获客渠道
    if "channels" in separated:
        parts.append(f"""
<industry_channels>
{separated['channels']}
</industry_channels>
""")

    # 指标基准
    if "metrics" in separated:
        parts.append(f"""
<industry_metrics>
{separated['metrics']}
</industry_metrics>

诊断时请将企业现状与以上行业基准进行对比，找出差距并给出具体提升路径。
""")

    # 客户画像
    if "profiles" in separated:
        parts.append(f"""
<customer_profiles>
{separated['profiles']}
</customer_profiles>
""")

    # 案例参考
    if "cases" in separated:
        parts.append(f"""
<reference_cases>
{separated['cases']}
</reference_cases>

如果企业情况与某个案例类似，请参考案例中的改进策略。
""")

    return "\n".join(parts)


def _get_file_skill_injection(file_name: str) -> str:
    """单文件模式的技能注入（兼容旧格式）"""
    content = _load_file_skill(file_name)
    if not content:
        return ""

    return f"""
## 行业专属知识（诊断时请参考以下行业信息）

<industry_skill>
{content}
</industry_skill>

请结合以上行业知识，对该企业进行针对性诊断。
"""


def list_available_skills() -> list[dict]:
    """列出所有可用的行业技能"""
    skills = {}

    # 目录模式
    for dir_path in SKILLS_DIR.iterdir():
        if dir_path.is_dir() and (dir_path / "__init__.py").exists():
            md_files = list(dir_path.glob("*.md"))
            if md_files:
                skill_name = dir_path.name
                # 读取第一个 md 文件的标题
                display_name = skill_name
                for line in md_files[0].read_text(encoding="utf-8").split("\n"):
                    if line.startswith("# "):
                        display_name = line[2:].strip()
                        break

                aliases = [
                    alias
                    for alias, (_, name) in INDUSTRY_ALIASES.items()
                    if name == skill_name
                ]
                sub_files = [f.name for f in md_files]

                skills[skill_name] = {
                    "name": skill_name,
                    "display_name": display_name,
                    "type": "directory",
                    "files": sub_files,
                    "aliases": aliases,
                }

    # 单文件模式
    for f in INDUSTRY_SKILLS_DIR.glob("*.md"):
        skill_name = f.stem
        display_name = skill_name
        content = f.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.startswith("# "):
                display_name = line[2:].strip()
                break

        aliases = [alias for alias, (_, name) in INDUSTRY_ALIASES.items() if name == skill_name]

        skills[skill_name] = {
            "name": skill_name,
            "display_name": display_name,
            "type": "file",
            "file": f.name,
            "aliases": aliases,
        }

    return sorted(skills.values(), key=lambda s: s["display_name"])


def validate_skills_directory() -> bool:
    """验证技能目录结构完整性"""
    valid = True

    # 检查单文件模式
    required_files = ["renovation.md", "restaurant.md", "education.md", "beauty.md", "generic.md"]
    for f in required_files:
        if not (INDUSTRY_SKILLS_DIR / f).exists():
            logger.warning("缺失单文件技能: %s", f)
            valid = False

    # 检查目录模式（地产核心）
    real_estate_dir = SKILLS_DIR / "real_estate"
    if real_estate_dir.is_dir():
        required_subfiles = ["diagnosis_criteria.md", "channels.md", "metrics.md"]
        for f in required_subfiles:
            if not (real_estate_dir / f).exists():
                logger.warning("地产技能目录缺失子文件: %s", f)
                valid = False
    else:
        logger.warning("缺失地产技能目录: %s", real_estate_dir)
        valid = False

    return valid


def get_real_estate_subcategories() -> list[str]:
    """获取地产行业的所有子类"""
    return list(REAL_ESTATE_SUBCATEGORIES.keys())
