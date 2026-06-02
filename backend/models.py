from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    # 与 DDL 列名 password 一致，存 bcrypt 哈希
    password = Column("password", String(100), nullable=False)
    nickname = Column(String(50), default="")
    email = Column(String(100), default="")
    vip_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )


class LessonRecord(Base):
    __tablename__ = "lesson_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=1)
    grade = Column(String(20))
    subject = Column(String(20))
    topic = Column(String(100))
    files_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.now)


class PayOrder(Base):
    __tablename__ = "pay_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, index=True, nullable=False)
    trade_no = Column(String(64), nullable=True)
    user_id = Column(Integer, index=True, nullable=False)
    provider = Column(String(20), default="alipay")
    channel = Column(String(20), default="app")
    days = Column(Integer, nullable=False)
    amount = Column(String(20), nullable=False)
    status = Column(String(20), default="PENDING")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
    )
