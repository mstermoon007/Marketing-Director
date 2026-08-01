"""
数据库 ORM 模型（SQLite + SQLAlchemy）
参考开发思路文档：第5.1节 — SQLite，零配置，MVP够用

使用 aiosqlite 异步驱动，配合 FastAPI 异步路由。
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config.settings import DATABASE_URL


Base = declarative_base()


def gen_id() -> str:
    """生成唯一ID"""
    return uuid.uuid4().hex[:12]


# ── 企业信息表 ──
class BusinessRecord(Base):
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=gen_id)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)


# ── 复盘报告表 ──
class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=gen_id)
    plan_id = Column(String, ForeignKey("execution_plans.id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)
    summary = Column(Text)
    numbers = Column(JSON)        # {"新增客户":12, "咨询量":45}
    vs_target = Column(JSON)      # [{"metric_name":"新增客户","target":10,"actual":12,"achieved":true}]
    what_worked = Column(JSON)    # ["做得好的1", ...]
    what_didnt = Column(JSON)     # ["需要改进的1", ...]
    suggestions = Column(JSON)    # ["下周建议1", ...]
    created_at = Column(DateTime, default=datetime.utcnow)


# ── 数据库初始化 ──
def init_db(db_url: str = DATABASE_URL):
    """初始化数据库，创建所有表"""
    # aiosqlite 的 URL 转换
    sync_url = db_url.replace("+aiosqlite://", "://")
    engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


# 同步 Session（用于简单操作）
SyncSession = sessionmaker(bind=init_db())
