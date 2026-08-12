"""
数据库 ORM 模型（SQLite + SQLAlchemy，全异步）

全程使用 aiosqlite 异步驱动 + 真实异步引擎（create_async_engine），
配合 FastAPI 异步路由。所有 DB 操作（含启动建表）均走 AsyncSessionLocal，
不再创建任何同步引擎，避免 asyncio 事件循环中的阻塞调用。
"""

import asyncio
import concurrent.futures
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    inspect,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from backend.config.settings import DATABASE_URL


Base = declarative_base()


def _utcnow() -> datetime:
    """UTC 当前时间（替代已弃用的 datetime.utcnow）。"""
    return datetime.now(timezone.utc)


def gen_id() -> str:
    """生成唯一ID"""
    return uuid.uuid4().hex[:12]


# ── 企业信息表 ──
class BusinessRecord(Base):
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, nullable=True, index=True)  # 归属用户（JWT user_id）
    business_name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    city = Column(String, nullable=False)
    product_desc = Column(Text)
    price_range = Column(String)
    target_customers = Column(Text)
    competitors = Column(Text)
    current_channels = Column(Text)
    monthly_revenue = Column(String)
    team_size = Column(String)
    biggest_pain = Column(Text)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


# ── 诊断报告表 ──
class DiagnosisRecord(Base):
    __tablename__ = "diagnoses"

    id = Column(String, primary_key=True, default=gen_id)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    overall_score = Column(Integer, default=0)
    score_summary = Column(Text)
    score_breakdown = Column(JSON)  # {"定位":80, "产品":65, ...}
    top3_problems = Column(JSON)    # [{"severity":"critical",...}, ...]
    strategy_summary = Column(Text)
    this_week_focus = Column(Text)
    created_at = Column(DateTime, default=_utcnow)


# ── 7天执行计划表 ──
class ExecutionPlanRecord(Base):
    __tablename__ = "execution_plans"

    id = Column(String, primary_key=True, default=gen_id)
    diagnosis_id = Column(String, ForeignKey("diagnoses.id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    start_date = Column(Date, default=date.today)
    theme = Column(String)
    goals = Column(JSON)          # ["目标1", "目标2"]
    key_metrics = Column(JSON)    # {"新增客户":0, "咨询量":0}
    days = Column(JSON)           # [DayPlan, ...] 完整7天数据
    status = Column(String, default="draft")  # draft | confirmed
    confirmed_at = Column(DateTime, nullable=True)
    week_number = Column(Integer, nullable=True)  # 第几周（1-12）
    created_at = Column(DateTime, default=_utcnow)


# ── 复盘报告表 ──
class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=gen_id)
    plan_id = Column(String, ForeignKey("execution_plans.id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    week_number = Column(Integer, nullable=True)  # 第几周复盘
    summary = Column(Text)
    numbers = Column(JSON)        # {"新增客户":12, "咨询量":45}
    vs_target = Column(JSON)      # [{"metric_name":"新增客户","target":10,"actual":12,"achieved":true}]
    what_worked = Column(JSON)    # ["做得好的1", ...]
    what_didnt = Column(JSON)     # ["需要改进的1", ...]
    suggestions = Column(JSON)    # ["下周建议1", ...]
    created_at = Column(DateTime, default=_utcnow)


# ── 排期任务表（闭环：计划确认后落库，可被打卡/复盘读取）──
class TodoRecord(Base):
    __tablename__ = "todos"

    id = Column(String, primary_key=True, default=gen_id)
    business_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    plan_id = Column(String, nullable=True)
    day_index = Column(Integer, default=1)
    date = Column(String, nullable=True)
    title = Column(String, nullable=False)
    time_slot = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending | doing | done
    how_to = Column(Text, nullable=True)
    checklist = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    images = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


# ── 用户反馈表（闭环：持续学习）──
class FeedbackRecord(Base):
    __tablename__ = "feedbacks"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, nullable=False, index=True)
    business_id = Column(String, nullable=True)
    target_type = Column(String, nullable=False)  # diagnosis|plan|schedule|review|card|suggestion
    target_id = Column(String, nullable=True)
    rating = Column(Integer, default=0)  # +1 赞 / -1 踩
    comment = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)  # 可含 card_ids / tags / 修改摘要
    created_at = Column(DateTime, default=_utcnow)


# ── 指标记录表（闭环：上传解析 → 看板刷新）──
class MetricRecord(Base):
    __tablename__ = "metrics"

    id = Column(String, primary_key=True, default=gen_id)
    business_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True)
    source = Column(String, nullable=True)  # upload | review
    numbers = Column(JSON, nullable=False)  # {"新增客户":12, ...}
    created_at = Column(DateTime, default=_utcnow)


# ── 策略有效性评分表（闭环：越用越懂你）──
class StrategyScoreRecord(Base):
    __tablename__ = "strategy_scores"

    id = Column(String, primary_key=True, default=gen_id)
    card_id = Column(String, nullable=False, index=True)
    card_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    positive = Column(Integer, default=0)
    negative = Column(Integer, default=0)
    score = Column(Integer, default=0)  # 有效性评分（正减负，可加权）
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


# ──────────────────────────────────────────────
# 引擎初始化（全程异步）
# ──────────────────────────────────────────────

def _run_migrations(conn) -> None:
    """为已存在的表补齐新增列（SQLite 的 create_all 不会 ALTER 已有表）。

    以**同步**函数形式经 AsyncConnection.run_sync 在异步连接上执行
    （run_sync 会把底层同步连接传给本函数并直接调用，因此必须同步）。
    """
    inspector = inspect(conn)
    existing = set(inspector.get_table_names())

    _ALTERS = {
        "businesses": [("user_id", "VARCHAR")],
        "execution_plans": [
            ("status", "VARCHAR"),
            ("confirmed_at", "DATETIME"),
            ("week_number", "INTEGER"),
        ],
        "reviews": [("week_number", "INTEGER")],
    }
    for table, cols in _ALTERS.items():
        if table not in existing:
            continue
        present = {c["name"] for c in inspector.get_columns(table)}
        for col_name, col_type in cols:
            if col_name not in present:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))


async def _init_db_async() -> None:
    """异步建表 + 迁移，全程使用真实异步引擎（aiosqlite 驱动）。"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_migrations)


def init_db() -> None:
    """初始化数据库，创建所有表（同步入口，导入/启动/测试中调用）。

    内部通过 asyncio 驱动真实异步引擎完成 DDL，不再创建任何同步引擎，
    从源头消除 asyncio 事件循环中的阻塞 DB 调用。

    若调用方已处于事件循环中（如异步测试内 import app），则在独立线程
    中驱动建表，避免 ``asyncio.run() cannot be called from a running
    event loop`` 报错。
    """

    def _run() -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_init_db_async())
        finally:
            loop.close()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        _run()  # 无运行中事件循环：直接驱动
    else:
        # 已在事件循环中：用独立线程 + 独立 loop 跑，避免与现有 loop 冲突
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_run).result()


# ── 异步引擎 & 会话工厂（运行时 + 启动统一使用）──
# DATABASE_URL 在配置层已保证为异步驱动（sqlite+aiosqlite:///...），
# 直接使用，不做任何字符串替换——避免把异步驱动误剥离成同步引擎。
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取异步数据库会话。

    使用方式::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
