from datetime import datetime
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# 固定使用 backend/mojin.db（绝对路径），避免因启动目录不同导致数据分裂
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mojin.db")
DATABASE_URL = "sqlite:///" + _DB_PATH.replace("\\", "/")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    nickname = Column(String(64), nullable=False)
    role = Column(String(16), default="player")  # player / admin
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("Result", back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512), default="")
    status = Column(String(16), default="open")  # open / closed
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("Result", back_populates="event")


class Result(Base):
    """一条成绩提交记录：
    - submit_type=total：总价值榜（战绩列表截图求和），explore_value 为时间段内探索价值总和
    - submit_type=best：单场最高榜（单场结算图），takeout_value/kills 为该场数值
    双人场次每人一条记录，共享 match_id（组队码）。
    """
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    match_id = Column(String(64), index=True)          # 场次/组队标识，双人同队共享
    is_duo = Column(Boolean, default=False)            # 是否双人
    submit_type = Column(String(16), default="total")  # total=总价值列表求和 / best=单场最高
    time_start = Column(DateTime, nullable=True)       # 列表求和的时间段起点
    time_end = Column(DateTime, nullable=True)         # 列表求和的时间段终点
    explore_value = Column(Float, default=0)           # total: 时间段内探索价值总和；best: 单场探索价值
    takeout_value = Column(Float, default=0)           # 带出价值（best 模式为主）
    kills = Column(Integer, default=0)                 # 击败异象总个数（Σ各图标数量）
    kills_score = Column(Float, default=0)             # 击败异象总分值（Σ 图标分值×数量，新规则）
    kills_detail = Column(String(2048), default="")    # 异象图标明细 JSON: [{"name","count","score","sub"}]
    calc_explore = Column(Float, nullable=True)        # 选手自算探索价值（校对用）
    calc_takeout = Column(Float, nullable=True)        # 选手自算带出价值（校对用）
    calc_kills = Column(Integer, nullable=True)        # 选手自算击败异象总个数（校对用）
    calc_kills_score = Column(Float, nullable=True)    # 选手自算击败异象总分（校对用）
    image_path = Column(String(256), default="")       # 战绩图原图
    ocr_text = Column(String(2048), default="")        # OCR 原始文本
    confirmed = Column(Boolean, default=False)         # 是否已确认提交
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="results")
    event = relationship("Event", back_populates="results")


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """SQLite 轻量迁移：为已存在的 results 表补充新增列"""
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(results)"))}
        add = {
            "submit_type": "VARCHAR(16) DEFAULT 'total'",
            "time_start": "DATETIME",
            "time_end": "DATETIME",
            "calc_explore": "FLOAT",
            "calc_takeout": "FLOAT",
            "calc_kills": "INTEGER",
            "kills_score": "FLOAT DEFAULT 0",
            "kills_detail": "VARCHAR(2048) DEFAULT ''",
            "calc_kills_score": "FLOAT",
        }
        for name, ddl in add.items():
            if name not in cols:
                conn.execute(text(f"ALTER TABLE results ADD COLUMN {name} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
