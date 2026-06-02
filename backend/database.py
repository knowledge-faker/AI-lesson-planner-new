# 你需要安装: pip install sqlalchemy pymysql
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 与 Spring 的 datasource.url 一样：只从环境读，写在 .env / 服务器环境变量里
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL 未设置。在 backend/.env.dev 或 .env.prod 中配置，例如 "
        "mysql+pymysql://用户:密码@主机:3306/数据库名"
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()