"""
pytest 全局配置和 fixtures

核心：MockLLMProvider 替代真实 LLM 调用，让测试不依赖 API Key。
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch

# 确保项目根目录在 path 中
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 在所有 LLM 测试中，模拟 API Key 已配置 → LLM 路径会被走（实际调用被 Mock 替代）
import os as _os
_os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-dummy-for-pytest")

from src.models.business import BusinessProfile
from src.models.diagnosis import DiagnosisReport
from src.models.execution import SevenDayPlan
from src.models.review import ReviewReport

from tests.fixtures.industries import ALL_INDUSTRIES


# ──────────────────────────────────────────────
# Mock LLM Provider
# ──────────────────────────────────────────────

class MockLLMProvider:
    """
    Mock LLM Provider

    根据调用时的 system_prompt 内容判断是哪个 Agent 在调用，
    返回对应的预设 JSON 响应。
    """

    def __init__(self):
        self.calls = []  # 记录所有调用，用于断言
        self._diagnosis_response = None
        self._executor_response = None
        self._review_response = None
        self._vision_response = None
        self._executor_retry_responses = []  # 用于测试重试逻辑
        self._retry_count = 0

    def set_responses(self, diagnosis=None, executor=None, review=None, vision=None):
        """设置各 Agent 的 Mock 响应"""
        self._diagnosis_response = diagnosis
        self._executor_response = executor
        self._review_response = review
        self._vision_response = vision

    def set_executor_retry_sequence(self, responses):
        """设置执行引擎的重试响应序列（用于测试约束验证重试）"""
        self._executor_retry_responses = list(responses)
        self._retry_count = 0

    async def chat(self, system_prompt, user_message, json_mode=False, model=None, temperature=None):
        """Mock chat 方法"""
        self.calls.append({
            "method": "chat",
            "system_prompt": system_prompt,
            "user_message": user_message,
            "json_mode": json_mode,
        })

        # 按 Agent 特征关键词匹配 — 注意顺序：更具体的关键词优先，
        # 避免"诊断"误匹配 executor/reviewer prompt 中出现的"诊断结论"字样。
        if "执行教练" in system_prompt or "7天执行清单" in system_prompt:
            if self._executor_retry_responses:
                idx = min(self._retry_count, len(self._executor_retry_responses) - 1)
                resp = self._executor_retry_responses[idx]
                self._retry_count += 1
                if isinstance(resp, str):
                    return resp
                return json.dumps(resp, ensure_ascii=False)
            if self._executor_response is not None:
                if isinstance(self._executor_response, str):
                    return self._executor_response
                return json.dumps(self._executor_response, ensure_ascii=False)

        if "数据分析师" in system_prompt or "复盘报告" in system_prompt:
            if self._review_response is not None:
                if isinstance(self._review_response, str):
                    return self._review_response
                return json.dumps(self._review_response, ensure_ascii=False)

        if "营销顾问" in system_prompt or "营销诊断" in system_prompt:
            if self._diagnosis_response is not None:
                if isinstance(self._diagnosis_response, str):
                    return self._diagnosis_response
                return json.dumps(self._diagnosis_response, ensure_ascii=False)

        # 默认返回空 JSON
        return "{}"

    async def chat_with_images(self, system_prompt, image_paths, model=None):
        """Mock 多模态调用"""
        self.calls.append({
            "method": "chat_with_images",
            "system_prompt": system_prompt,
            "image_paths": image_paths,
        })

        if self._vision_response is not None:
            if isinstance(self._vision_response, str):
                return self._vision_response
            return json.dumps(self._vision_response, ensure_ascii=False)

        return '{"numbers": {}}'


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    """提供 MockLLMProvider 实例"""
    return MockLLMProvider()


@pytest.fixture
def patched_llm(mock_llm):
    """替换全局 LLMProvider 单例为 Mock"""
    with patch("src.services.llm._llm_provider", mock_llm):
        with patch("src.services.llm.get_llm_provider", return_value=mock_llm):
            with patch("src.agents.diagnosis.get_llm_provider", return_value=mock_llm):
                with patch("src.agents.executor.get_llm_provider", return_value=mock_llm):
                    with patch("src.agents.reviewer.get_llm_provider", return_value=mock_llm):
                        yield mock_llm


@pytest.fixture(params=list(ALL_INDUSTRIES.keys()))
def industry_case(request):
    """参数化 fixture：遍历5个行业测试用例"""
    return ALL_INDUSTRIES[request.param]


@pytest.fixture
def industry_name(request):
    """当前行业名称"""
    return request.param


# ──────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────

def make_profile(industry_key: str) -> BusinessProfile:
    """从行业测试数据创建 BusinessProfile"""
    data = ALL_INDUSTRIES[industry_key]["profile_data"]
    return BusinessProfile(
        id=f"test_{industry_key}",
        **data,
    )


def make_diagnosis(industry_key: str) -> DiagnosisReport:
    """从行业测试数据创建 DiagnosisReport"""
    data = ALL_INDUSTRIES[industry_key]["diagnosis_resp"]
    return DiagnosisReport.from_ai_response(
        business_id=f"test_{industry_key}",
        data=data,
    )


def make_plan(industry_key: str) -> SevenDayPlan:
    """从行业测试数据创建 SevenDayPlan"""
    from datetime import date
    data = ALL_INDUSTRIES[industry_key]["executor_resp"]
    return SevenDayPlan.from_ai_response(
        diagnosis_id=f"diag_{industry_key}",
        business_id=f"test_{industry_key}",
        start_date=date(2026, 7, 29),
        data=data,
    )


def make_review(industry_key: str) -> ReviewReport:
    """从行业测试数据创建 ReviewReport"""
    data = ALL_INDUSTRIES[industry_key]["review_resp"]
    return ReviewReport.from_ai_response(
        plan_id=f"plan_{industry_key}",
        business_id=f"test_{industry_key}",
        data=data,
    )


# ──────────────────────────────────────────────
# pytest hook: 注册 --update-snapshot 选项
# ──────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshot",
        action="store_true",
        default=False,
        help="更新 Prompt 快照基线",
    )
