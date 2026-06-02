import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User

security = HTTPBearer(auto_error=False)

JWT_ALG = "HS256"
JWT_EXPIRE_DAYS = 7


def _jwt_secret() -> str:
    s = os.getenv("JWT_SECRET", "").strip()
    if not s:
        if os.getenv("APP_ENV", "dev").lower() == "prod":
            raise RuntimeError("生产环境必须在环境变量中设置 JWT_SECRET")
        return "dev-only-secret-not-for-production"
    return s


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": exp, "iat": now}
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALG)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALG])
        uid = int(payload.get("sub", 0))
        if uid <= 0:
            raise ValueError("invalid sub")
        return uid
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="未登录或缺少令牌")
    uid = decode_token(creds.credentials)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
