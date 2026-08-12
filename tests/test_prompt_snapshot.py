"""
Prompt 回归快照测试（开发思路文档 §6 Phase 2 要求）

核心思路：
1. 每次修改 Prompt 模板后，先更新快照：
      python -m pytest tests/test_prompt_snapshot.py --update-snapshot -v

2. 日常运行：
      python -m pytest tests/test_prompt_snapshot.py -v

如果 Prompt 被无意修改，此测试会 FAIL，保护 Prompt 稳定性。
"""

from __future__ import annotations

import pytest
import hashlib
from pathlib import Path
from typing import Optional
from backend.prompts.loader import (
    load_prompt,
    load_prompt_with_skill,
    list_available_prompts,
)
from tests.fixtures.industries import ALL_INDUSTRIES


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _snapshot_key(name: str, suffix: str = "") -> str:
    """统一快照文件名（去掉特殊字符）"""
    safe = name.replace("/", "__").replace(" ", "_")
    return f"{safe}{suffix}.snap"


def _save_snapshot(key: str, content: str) -> None:
    (SNAPSHOT_DIR / key).write_text(content, encoding="utf-8")


def _load_snapshot(key: str) -> Optional[str]:
    p = SNAPSHOT_DIR / key
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# 需要回归的 Prompt 模板（文档 6.2 要求：diagnosis / executor / reviewer 三类）
CORE_PROMPTS = [
    "diagnosis/system.txt",
    "diagnosis/real_estate.txt",
    "executor/system.txt",
    "executor/day_template.txt",
    "reviewer/report.txt",
    "reviewer/parse_image.txt",
]


class TestPromptSnapshots:

    @pytest.mark.parametrize("prompt_path", CORE_PROMPTS)
    def test_prompt_snapshot(self, prompt_path, request):
        """
        快照回归：Prompt 模板渲染 + hash 必须与快照一致
        """
        # 准备 context（各模板都用一致的占位参数）
        ctx = "企业名称：测试快照公司\n行业：家装\n目标客群：30-40岁改善型家庭"
        diagnosis_context = "核心问题：到店率低；建议：加强同城短视频"

        # 按模板类型选择合适的渲染方式
        rendered = ""
        if prompt_path.startswith("diagnosis/"):
            if "real_estate" in prompt_path:
                # real_estate 模板只接受 skill_context
                rendered = load_prompt_with_skill(
                    "diagnosis",
                    profile_context="测试公司\n地产\n目标客群：首套刚需",
                    skill_content="\n# 地产行业诊断标准\n6维度\n",
                    industry="地产",
                )
            else:
                rendered = load_prompt(prompt_path, business_context=ctx)
        elif prompt_path.startswith("executor/"):
            if "day_template" in prompt_path:
                # day_template 是 executor 内部的 day_level_prompt
                from backend.prompts.loader import _jinja
                # 用模板引擎直接渲染
                rendered = _jinja(
                    prompt_path,
                    day_label="周一",
                    focus="客户挖掘",
                    skills_text="",
                    diagnosis_context=diagnosis_context,
                    business_context=ctx,
                    yesterday_feedback="",
                )
            else:
                from backend.prompts.loader import _jinja
                rendered = _jinja(
                    prompt_path,
                    business_context=ctx,
                    diagnosis_context=diagnosis_context,
                    skills_text="",
                    start_date="2025-01-06",
                    yesterday_feedback="",
                )
        elif prompt_path.startswith("reviewer/"):
            from backend.prompts.loader import _jinja
            rendered = _jinja(
                prompt_path,
                goals_context="本周目标：短视频5条 + 线下客户10组",
                numbers_context="执行结果：新增客户10人，到店2人",
            )

        assert rendered != "", f"{prompt_path} 渲染为空"

        # 比较快照
        key = _snapshot_key(prompt_path)
        current_hash = _sha256(rendered)
        current_snap = f"# SHA256: {current_hash}\n{rendered}"

        stored = _load_snapshot(key)
        if stored is None:
            # 首次运行：写快照
            _save_snapshot(key, current_snap)
            pytest.skip(f"快照不存在，已创建：{key}")
            return

        # 对比：比较完整内容（保证 Prompt 语义一致）
        update = request.config.getoption("--update-snapshot", False)
        if update:
            _save_snapshot(key, current_snap)
            return

        if stored != current_snap:
            # 找第一处不同的行
            stored_lines = stored.splitlines()
            current_lines = current_snap.splitlines()
            diff_line = 0
            for i, (a, b) in enumerate(zip(stored_lines, current_lines)):
                if a != b:
                    diff_line = i + 1
                    break
            pytest.fail(
                f"Prompt 快照不一致: {prompt_path}\n"
                f"  不同行: {diff_line}\n"
                f"  快照哈希: {stored_lines[0] if stored_lines else '(empty)'}\n"
                f"  当前哈希: SHA256: {current_hash}\n"
                f"  如需更新快照，请加: --update-snapshot"
            )


class TestPromptPresence:
    """所有文档要求的 Prompt 模板必须存在，不能被误删"""

    def test_core_prompts_exist(self):
        available = set(list_available_prompts())
        for p in CORE_PROMPTS:
            assert p in available, f"缺少关键 Prompt 模板: {p}"

    def test_industry_prompt_mapping_has_all(self):
        """诊断行业映射：所有 DiagnosisAgent 用到的模板必须存在"""
        from backend.agents.diagnosis import INDUSTRY_PROMPT_MAP

        available = set(list_available_prompts())
        for key, prompt in INDUSTRY_PROMPT_MAP.items():
            # prompt 本身已是相对 prompts/ 目录的完整路径（如 "diagnosis/real_estate.txt"）
            assert prompt in available, (
                f"行业 {key} 引用的模板 {prompt} 不存在"
            )


class TestSkillInjectionStability:
    """Skill 注入到诊断 Prompt 的内容必须稳定（防止回归）"""

    SKILL_SAMPLE = {
        "家装": "家装行业痛点：获客成本高，转化率低",
        "餐饮": "餐饮行业痛点：复购率低，依赖客流高峰",
        "教培": "教培行业痛点：获客成本高，退费管理",
        "美容": "美业行业痛点：会员粘性低，技师依赖",
        "中介": "房产中介痛点：房源同质化，带看转化率低",
    }

    @pytest.mark.parametrize("industry_key", list(ALL_INDUSTRIES.keys()))
    def test_diagnosis_with_skill_contains_skill_content(self, industry_key):
        skill_text = self.SKILL_SAMPLE.get(industry_key, self.SKILL_SAMPLE["家装"])

        rendered = load_prompt_with_skill(
            "diagnosis",
            profile_context="测试公司",
            skill_content=skill_text,
            industry=industry_key,
        )
        # skill 内容必须出现在渲染结果中（注入不可缺）
        sample_line = skill_text.splitlines()[0] if skill_text.splitlines() else skill_text[:20]
        assert sample_line in rendered, (
            f"{industry_key} 的 Skill 注入未生效，渲染结果缺少 skill 文本"
        )


# ──────────────────────────────────────────────
# pytest hook: --update-snapshot 选项已注册在 tests/conftest.py
# ──────────────────────────────────────────────
