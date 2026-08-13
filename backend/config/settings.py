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

# 运行环境：development / staging / production。
# 生产部署必须显式设置 APP_ENV=production；staging 作为独立预发环境落到各自的物理库文件，
# 三者互不复用，避免开发数据污染客户数据、预发数据污染生产数据。
APP_ENV = os.getenv("APP_ENV", "development").lower()


# 数据库路径
def _resolve_database_url() -> str:
    """解析数据库连接串。

    优先级：
      1. 显式环境变量 ``DATABASE_URL``（部署时强制指定，覆盖一切）；
      2. 未设置时按 ``APP_ENV`` 落到不同物理库文件，隔离各环境数据：
         - ``production`` -> ``data/app_prod.db``
         - ``staging``    -> ``data/app_staging.db``
         - 其它(development) -> ``data/app_dev.db``

    说明：``tests/conftest.py`` 会在导入后端模块前设置 ``DATABASE_URL``，
    因此单测始终使用独立临时库，不受此处默认行为影响。
    """
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    env_db_file = {
        "production": "app_prod.db",
        "staging": "app_staging.db",
    }.get(APP_ENV, "app_dev.db")
    return f"sqlite+aiosqlite:///{PROJECT_ROOT}/data/{env_db_file}"


DATABASE_URL = _resolve_database_url()

# 数据库目录
DATA_DIR = PROJECT_ROOT / "data"
os.makedirs(DATA_DIR, exist_ok=True)


def _guard_prod_env_isolation() -> None:
    """运行时数据隔离护栏（最后一道闸）。

    防止「以服务形态运行」的实例误用开发库 data/app_dev.db（会污染开发数据、
    且客户/预发数据落错库）：

      - 信号：``PORT`` 由 CloudRun / 云托管在拉起容器时注入，本地 ``uvicorn`` 与
        ``docker run`` 不会设置。因此 ``PORT`` 已设置 = 正在以生产/预发服务形态运行。
      - 判定：服务形态下，若解析出的库仍是 ``data/app_dev.db``（即未通过 ``APP_ENV``
        落到独立库、也未通过 ``DATABASE_URL`` 指定独立库），直接拒绝启动并抛出 ``RuntimeError``。

    各环境契约（与前端 md:dev:/md:staging:/md:prod: 缓存隔离、后端按 APP_ENV 分库一致）：
      以服务形态部署时，必须设置 ``APP_ENV=production`` / ``APP_ENV=staging``（分别落到
      app_prod.db / app_staging.db）或显式 ``DATABASE_URL``。核心是不允许写回 app_dev.db。
    """
    is_prod_serving = bool(os.getenv("PORT"))
    if not is_prod_serving:
        return
    if DATABASE_URL.rstrip().endswith("app_dev.db"):
        raise RuntimeError(
            "PROD_ENV_MISCONFIG: 检测到服务形态运行（PORT 已设置）但数据库解析为 data/app_dev.db。"
            "为避免开发库被生产/预发流量写入、数据落错库，已拒绝启动。"
            "请设置 APP_ENV=production/staging（落到 app_prod.db/app_staging.db）"
            "或通过 DATABASE_URL 指定独立库。"
        )


_guard_prod_env_isolation()


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
    app_version: str = "1.0.0"
    # 运行环境（development / production），与模块级 APP_ENV 保持一致
    app_env: str = APP_ENV
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # CORS 白名单（逗号分隔域名，留空则使用默认开发域名）
    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "")

    # JWT 签名密钥（必须通过环境变量设置，禁止硬编码）
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_days: int = int(os.getenv("JWT_EXPIRE_DAYS", "30"))

    # 微信小程序配置
    wechat_appid: str = os.getenv("WECHAT_APPID", "")
    wechat_secret: str = os.getenv("WECHAT_SECRET", "")

    # 生产环境后端公开基址（登录成功后下发给小程序，避免前端硬编码/加密敏感配置）
    # 留空表示完全依赖登录返回；部署时建议填入公开生产域名（如 https://api.example.com/api）
    public_api_base_url: str = os.getenv("PUBLIC_API_BASE_URL", "")

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
