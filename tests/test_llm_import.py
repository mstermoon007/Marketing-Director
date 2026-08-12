import importlib
import sys


def test_llm_module_imports_without_openai_dependency():
    sys.modules.pop("backend.services.llm", None)

    module = importlib.import_module("backend.services.llm")

    assert hasattr(module, "get_llm_provider")
    assert hasattr(module, "LLMProvider")
