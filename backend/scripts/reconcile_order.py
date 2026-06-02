#!/usr/bin/env python3
"""
在服务器上查支付宝订单并尝试履约（补单）。

用法（在 /opt/ai-lesson-planner/backend 下）:
  .venv/bin/python scripts/reconcile_order.py PROD_20260519220048772531
  .venv/bin/python scripts/reconcile_order.py --user root --limit 5
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_backend))

os.chdir(_backend)
os.environ.setdefault("APP_ENV", "prod")
os.environ.setdefault("ENV_FILE", ".env.prod")

import main  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import PayOrder, User  # noqa: E402


def reconcile_one(db, order_no: str) -> None:
    order = db.query(PayOrder).filter(PayOrder.order_no == order_no).first()
    if not order:
        print(f"[MISS] 订单不存在: {order_no}")
        return
    user = db.query(User).filter(User.id == order.user_id).first()
    print(f"\n=== {order_no} ===")
    print(f"  user_id={order.user_id} username={user.username if user else '?'}")
    print(f"  amount={order.amount} days={order.days} status={order.status}")
    if order.status == "SUCCESS":
        print(f"  已是 SUCCESS, paid_at={order.paid_at}, trade_no={order.trade_no}")
        if user:
            print(f"  vip_expiry={user.vip_expiry}")
        return
    if order.status == "FAILED":
        order.status = "PENDING"
        db.add(order)
        db.commit()
        print("  已将 FAILED 改回 PENDING 以便重试补单")
    info = main._sync_alipay_order(order, db)
    db.refresh(order)
    if user:
        db.refresh(user)
    print(f"  查单结果: {info}")
    print(f"  订单状态: {order.status}")
    if user:
        print(f"  vip_expiry={user.vip_expiry}")


def main_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("order_no", nargs="?", help="商户订单号")
    parser.add_argument("--user", default="root", help="按用户名补最近 PENDING 订单")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    main._load_env_file()
    print(f"[env] APP_ENV={main.APP_ENV} ALIPAY_APPID={(os.getenv('ALIPAY_APPID') or '')[-6:]}")

    db = SessionLocal()
    try:
        if args.order_no:
            reconcile_one(db, args.order_no)
            return
        user = db.query(User).filter(User.username == args.user).first()
        if not user:
            print(f"用户不存在: {args.user}")
            sys.exit(1)
        orders = (
            db.query(PayOrder)
            .filter(PayOrder.user_id == user.id, PayOrder.status == "PENDING")
            .order_by(PayOrder.id.desc())
            .limit(args.limit)
            .all()
        )
        if not orders:
            print("没有 PENDING 订单")
            return
        for o in orders:
            reconcile_one(db, o.order_no)
    finally:
        db.close()


if __name__ == "__main__":
    main_cli()
