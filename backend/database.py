from datetime import datetime
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# 数据库连接：
# - 云端（云托管）通过环境变量 DATABASE_URL 注入 PostgreSQL 内网连接串，
#   格式 postgresql://<user>:<password>@<host>:<port>/<dbname>；
# - 本地开发默认使用 SQLite（backend/mojin.db），避免因启动目录不同导致数据分裂。
# SQLite 数据库文件路径（仅本地/云托管 SQLite 模式使用；PostgreSQL 模式下无意义）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mojin.db")
DATABASE_URL = os.environ.get("DATABASE_URL") or ("sqlite:///" + DB_PATH.replace("\\", "/"))
IS_POSTGRES = DATABASE_URL.startswith("postgres")

if IS_POSTGRES:
    # 复用连接池，避免 serverless 每次请求新建连接；pool_pre_ping 处理断连重连
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False, default="")  # 选手无需密码，空字符串；管理员保留密码
    nickname = Column(String(64), nullable=False)
    qq = Column(String(32), index=True)               # QQ号（登录账号，应用层唯一）
    game_id = Column(String(64), default="")           # 第五人格游戏ID
    game_username = Column(String(64), default="")     # 第五人格游戏用户名
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
    _clean_image_paths()


def _table_columns(conn, table: str) -> set:
    """返回指定表已有的列名集合（兼容 SQLite 与 PostgreSQL）。"""
    if IS_POSTGRES:
        rows = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
            {"t": table},
        ).fetchall()
        return {r[0] for r in rows}
    return {r[1] for r in conn.execute(text(f"PRAGMA table_info({table})"))}


def _migrate():
    """轻量迁移：为已存在的 results / users 表补充新增列（DDL 在 SQLite 与 PostgreSQL 下通用）"""
    with engine.begin() as conn:
        cols = _table_columns(conn, "results")
        add = {
            "submit_type": "VARCHAR(16) DEFAULT 'total'",
            "time_start": "TIMESTAMP",
            "time_end": "TIMESTAMP",
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

        ucols = _table_columns(conn, "users")
        uadd = {
            "qq": "VARCHAR(32)",
            "game_id": "VARCHAR(64) DEFAULT ''",
            "game_username": "VARCHAR(64) DEFAULT ''",
        }
        for name, ddl in uadd.items():
            if name not in ucols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))


def _clean_image_paths():
    """清洗历史脏数据：image_path 若为本地绝对路径（含路径分隔符），规范化为纯文件名；
    对应文件不存在则丢弃。纯文件名数据原样保留（不因文件暂时丢失而清空）。"""
    up_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads"))
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, image_path FROM results WHERE image_path IS NOT NULL AND image_path != ''")
        ).fetchall()
        for rid, ip in rows:
            parts = [s.strip() for s in str(ip).split(",") if s.strip()]
            kept = []
            for p in parts:
                if "/" in p or "\\" in p:
                    # 历史绝对路径脏数据 → 提取文件名；文件不存在则丢弃
                    name = p.replace("\\", "/").rsplit("/", 1)[-1]
                    if os.path.isfile(os.path.join(up_dir, name)):
                        kept.append(name)
                else:
                    kept.append(p)
            new_val = ",".join(kept)
            if new_val != str(ip):
                conn.execute(text("UPDATE results SET image_path = :v WHERE id = :i"), {"v": new_val, "i": rid})


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
