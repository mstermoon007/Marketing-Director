"""
应用配置管理
参考开发思路文档：第5.1节技术选型
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Prompt 模板目录
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# 数据库路径
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{PROJECT_ROOT}/data/app.db"
)

# 数据库目录
DATA_DIR = PROJECT_ROOT / "data"
os.makedirs(DATA_DIR, exist_ok=True)


@dataclass
class LLMConfig:
    """LLM 配置 —— 参考文档 5.1 技术选型"""
    # 主力模型：DeepSeek V3（中文强，成本低）
    text_model: str = os.getenv("LLM_TEXT_MODEL", "deepseek-chat")
    text_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    text_api_base: str = os.getenv(
        "DEEPSEEK_API_BASE",
        "https://api.deepseek.com"
    )

    # 多模态模型：用于截图解析
    vision_model: str = os.getenv("LLM_VISION_MODEL", "gpt-4o")
    vision_api_key: str = os.getenv("OPENAI_API_KEY", "")
    vision_api_base: str = os.getenv(
        "OPENAI_API_BASE",
        "https://api.openai.com/v1"
    )

    # 通用参数
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    request_timeout: int = int(os.getenv("LLM_TIMEOUT", "120"))


@dataclass
class AppConfig:
    """应用全局配置"""
    app_name: str = "AI营销战略执行智能体"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 文件上传限制（MB）
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    # 支持的文件格式
    allowed_image_types: list = field(default_factory=lambda: [
        "image/png", "image/jpeg", "image/jpg", "image/webp"
    ])
    allowed_doc_types: list = field(default_factory=lambda: [
        "text/csv"
    ])

    # 执行引擎约束（参考文档 4.2 执行引擎）
    max_tasks_per_day: int = 5
    max_minutes_per_day: int = 120


llm_config = LLMConfig()
app_config = AppConfig()
