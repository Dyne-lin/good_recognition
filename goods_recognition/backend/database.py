# database.py
# 数据库配置（升级版）

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import os

# =====================================================
# 数据库连接配置
# 优先读取环境变量，方便部署时切换；本地开发保留默认值
# =====================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:123123@localhost:3306/goods_recognition?charset=utf8mb4"
)

# =====================================================
# 创建引擎
# pool_pre_ping  — 每次从连接池取连接前先 ping，避免"MySQL gone away"
# pool_recycle   — 连接最多复用 1 小时，防止被服务器主动断开
# pool_size      — 连接池大小
# max_overflow   — 连接池满时最多额外创建的连接数
# echo           — 是否打印 SQL 语句（调试用，生产环境设为 False）
# =====================================================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# =====================================================
# 会话工厂
# =====================================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# =====================================================
# ORM 基类
# =====================================================
Base = declarative_base()


# =====================================================
# FastAPI 依赖注入用的 get_db
# 用法：def my_route(db: Session = Depends(get_db))
# =====================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# 健康检查：测试数据库是否可以连接
# 可在启动时调用，或挂到 /health 路由
# =====================================================
def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as e:
        print(f"[DB] 连接失败: {e}")
        return False