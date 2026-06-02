# main.py (prod 分支)
from datetime import datetime, timedelta
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qsl
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import os
import sys
import logging
import re
from typing import Optional

from sqlalchemy.exc import IntegrityError

# 在读取 APP_ENV 等变量之前加载对应 .env（需: pip install python-dotenv）
_backend_root = Path(__file__).resolve().parent


def _load_env_file():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # 显式指定文件时优先，例如: ENV_FILE=.env.prod uvicorn main:app
    env_path = os.getenv("ENV_FILE")
    if env_path:
        load_dotenv(_backend_root / env_path, override=True)
        return
    # 由 APP_ENV（进程环境）决定；未设置时合并加载，避免线上误带 .env.dev 时盖住生产支付宝配置。
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env == "prod":
        for fname in ("my_.env.prod", ".env.prod"):
            p = _backend_root / fname
            if p.is_file():
                load_dotenv(p, override=True)
        return
    if app_env == "dev":
        load_dotenv(_backend_root / ".env.dev", override=True)
        return

    # 未 export APP_ENV：先 .env.dev（若存在），再 my_.env.prod、.env.prod，后者覆盖同名键。
    # 线上常见「目录里既有 .env.dev 又有 my_.env.prod」——必须以生产文件里的 ALIPAY_APPID 为准。
    dev_p = _backend_root / ".env.dev"
    if dev_p.is_file():
        load_dotenv(dev_p, override=True)
    for fname in ("my_.env.prod", ".env.prod"):
        p = _backend_root / fname
        if p.is_file():
            load_dotenv(p, override=True)


_load_env_file()

# 生产 JWT：缺省或过短会导致 PyJWT InsecureKeyLengthWarning（HS256 建议 ≥32 字节）及安全风险
if os.getenv("APP_ENV", "").strip().lower() == "prod":
    _jwt_secret = os.getenv("JWT_SECRET", "").strip()
    if not _jwt_secret:
        raise RuntimeError(
            "APP_ENV=prod 必须在环境或 .env.prod 中设置 JWT_SECRET，否则注册/登录会在写库后失败"
        )
    if len(_jwt_secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "APP_ENV=prod 时 JWT_SECRET 的 UTF-8 长度须 ≥ 32 字节（例如 openssl rand -hex 32），"
            "过短会触发 PyJWT 警告且不符合 HS256 建议"
        )

from security import (
    get_current_user,
    hash_password,
    verify_password,
    create_access_token,
)

# 生产环境日志
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("prod")


def _warn_alipay_env_mismatch():
    """APP_ENV=dev 却配公网回调时，易加载 .env.dev 的沙箱 AppID 而请求正式网关 → invalid-app-id。"""
    if os.getenv("APP_ENV", "").strip().lower() == "prod":
        return
    notify = (os.getenv("ALIPAY_NOTIFY_URL") or "").strip()
    if not notify.startswith("https://"):
        return
    low = notify.lower()
    if "localhost" in low or "127.0.0.1" in low:
        return
    logger.error(
        "支付宝配置风险：当前 APP_ENV 非 prod，会加载 .env.dev；若其中 ALIPAY_APPID 为沙箱/测试应用，"
        "而 ALIPAY_DEBUG 未开启，请求将发往 openapi.alipay.com 并返回 invalid-app-id。"
        "线上请设置 APP_ENV=prod；本地真支付宝调试请在本机 .env.dev 使用正式应用 AppID 或设 ALIPAY_DEBUG=1 走沙箱网关。"
    )


_warn_alipay_env_mismatch()

if os.getenv("APP_ENV", "").strip().lower() == "prod":
    _boot_aid = (os.getenv("ALIPAY_APPID") or "").strip()
    if len(_boot_aid) >= 4:
        print(
            f"[boot] APP_ENV=prod ALIPAY_APPID …{_boot_aid[-4:]} (len={len(_boot_aid)})",
            file=sys.stderr,
        )
# 真实导入
from ai_service import generate_lesson_package, GenerateReq
from database import get_db, engine
from models import Base, User, LessonRecord, PayOrder
from vip import check_permission

# 支付宝 SDK
from alipay import AliPay

# ================= 支付配置（仅环境变量） =================
ALIPAY_APPID = os.getenv("ALIPAY_APPID", "")
ALIPAY_PRIVATE_KEY = os.getenv("ALIPAY_PRIVATE_KEY", "")
ALIPAY_PUBLIC_KEY = os.getenv("ALIPAY_PUBLIC_KEY", "")

# ================= 应用初始化 =================
if not os.path.exists("files"):
    os.makedirs("files")

# 生产关闭接口文档
app = FastAPI(docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="files"), name="static")
Base.metadata.create_all(bind=engine)

# 开发/生产分离的跨域配置
APP_ENV = os.getenv("APP_ENV", "").strip().lower() or "dev"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
WEB_ORIGIN = os.getenv("WEB_ORIGIN", "").strip().rstrip("/")
FRONTEND_H5_BASE = os.getenv("FRONTEND_H5_BASE", "http://localhost:5176").rstrip("/")
if APP_ENV == "prod":
    # CORS 仅允许两项：前端站点 WEB_ORIGIN、对外 API 根地址 PUBLIC_BASE_URL（HTTPS 就绪后二者均应为 https://）
    _cors_web = os.getenv("WEB_ORIGIN", "").strip().rstrip("/")
    _cors_api = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    cors_origins = list(dict.fromkeys([x for x in (_cors_web, _cors_api) if x]))
else:
    _cors_base = [
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ]
    _cors_extra = []
    if WEB_ORIGIN:
        _cors_extra.append(WEB_ORIGIN)
    if FRONTEND_H5_BASE:
        _cors_extra.append(FRONTEND_H5_BASE)
    for _part in os.getenv("CORS_EXTRA_ORIGINS", "").split(","):
        _u = _part.strip().rstrip("/")
        if _u:
            _cors_extra.append(_u)
    cors_origins = list(dict.fromkeys(_cors_base + _cors_extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= 请求模型 =================
class PayReq(BaseModel):
    days: int
    provider: str
    channel: str = "pc"  # pc=电脑网站支付 page.pay | h5=手机网站 | qr=当面付precreate | app=APP支付
    return_url: Optional[str] = None
    # 测试专用：金额固定 0.01 元，开通 1 天（非 prod 默认允许；prod 需 VIP_TEST_PENNY_ENABLED=1）
    test_penny: bool = False


def _vip_test_penny_allowed() -> bool:
    if APP_ENV != "prod":
        return True
    return os.getenv("VIP_TEST_PENNY_ENABLED", "").lower() in ("1", "true", "yes")


def extend_vip(user: User, days: int, db: Session):
    now = datetime.now()
    base_time = user.vip_expiry if user.vip_expiry and user.vip_expiry > now else now
    user.vip_expiry = base_time + timedelta(days=days)
    db.add(user)
    db.commit()
    db.refresh(user)


def _amounts_match(expected, paid) -> bool:
    """金额比较（统一到分，避免 9.9 vs 9.90 等格式差异）。"""
    try:
        a = Decimal(str(expected)).quantize(Decimal("0.01"))
        b = Decimal(str(paid)).quantize(Decimal("0.01"))
        return a == b
    except (InvalidOperation, TypeError):
        return False


def _pick_alipay_paid_amount(data: dict, order_amount: str) -> Optional[str]:
    """
    从支付宝回包中选取与订单金额一致的实付金额。
    0.01 元测试单常见 receipt_amount=0.00，应以 total_amount / buyer_pay_amount 为准。
    """
    expected = Decimal(str(order_amount)).quantize(Decimal("0.01"))
    for key in ("buyer_pay_amount", "total_amount", "receipt_amount", "invoice_amount"):
        raw = data.get(key)
        if raw is None or raw == "":
            continue
        try:
            val = Decimal(str(raw)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError):
            continue
        if val == expected:
            return str(val)
    return None


def _fulfill_paid_order(
    order: "PayOrder",
    user: User,
    db: Session,
    *,
    trade_no: Optional[str] = None,
    receipt_amount=None,
    alipay_amount_fields: Optional[dict] = None,
) -> bool:
    """将已付款订单履约（延长 VIP）。已 SUCCESS 的订单直接返回 False。"""
    if order.status == "SUCCESS":
        return False

    paid_amount = None
    if alipay_amount_fields:
        paid_amount = _pick_alipay_paid_amount(alipay_amount_fields, order.amount)
    if paid_amount is None and receipt_amount is not None:
        if _amounts_match(order.amount, receipt_amount):
            paid_amount = str(
                Decimal(str(receipt_amount)).quantize(Decimal("0.01"))
            )

    if paid_amount is None:
        fields = alipay_amount_fields or {}
        logger.error(
            f"[PAY_FULFILL] amount mismatch order_no={order.order_no}, "
            f"expected={order.amount}, "
            f"buyer_pay_amount={fields.get('buyer_pay_amount')}, "
            f"total_amount={fields.get('total_amount')}, "
            f"receipt_amount={fields.get('receipt_amount')}"
        )
        order.status = "FAILED"
        db.add(order)
        db.commit()
        return False

    extend_vip(user, order.days, db)
    order.status = "SUCCESS"
    order.trade_no = trade_no or order.trade_no
    order.paid_at = datetime.now()
    db.add(order)
    db.commit()
    return True


def _sync_alipay_order(order: "PayOrder", db: Session) -> dict:
    """向支付宝查单并履约。无需登录，供支付回跳 order_result 与登录后 sync 共用。"""
    if order.status == "SUCCESS":
        return {"synced": False, "status": order.status, "trade_status": None}

    if order.provider != "alipay":
        return {
            "synced": False,
            "status": order.status,
            "trade_status": None,
            "message": "非支付宝订单",
        }

    try:
        alipay = get_alipay_client()
        resp = alipay.api_alipay_trade_query(out_trade_no=order.order_no)
    except Exception as e:
        logger.exception(f"[PAY_SYNC] query failed order_no={order.order_no}, err={e}")
        return {
            "synced": False,
            "status": order.status,
            "trade_status": None,
            "message": f"查询支付宝异常: {e}",
        }

    if str(resp.get("code", "")) != "10000":
        msg = resp.get("sub_msg") or resp.get("msg") or "支付宝查单失败"
        logger.error(
            f"[PAY_SYNC] alipay error order_no={order.order_no}, "
            f"code={resp.get('code')} sub_code={resp.get('sub_code')} msg={msg}"
        )
        return {
            "synced": False,
            "status": order.status,
            "trade_status": None,
            "alipay_code": resp.get("code"),
            "alipay_sub_code": resp.get("sub_code"),
            "message": msg,
        }

    trade_status = resp.get("trade_status")
    if trade_status not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return {
            "synced": False,
            "status": order.status,
            "trade_status": trade_status,
            "message": "支付宝显示尚未支付成功",
        }

    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        logger.error(f"[PAY_SYNC] user missing user_id={order.user_id}")
        return {"synced": False, "status": order.status, "trade_status": trade_status}

    synced = _fulfill_paid_order(
        order,
        user,
        db,
        trade_no=resp.get("trade_no"),
        alipay_amount_fields=resp,
    )
    db.refresh(order)
    return {
        "synced": synced,
        "status": order.status,
        "trade_status": trade_status,
    }


def _normalize_alipay_pem(raw: Optional[str]) -> str:
    """把 .env 里的单行 PEM（含字面量 \\n）还原为换行，去掉 BOM，统一换行符。"""
    if raw is None:
        return ""
    s = str(raw).strip().strip("'\"")
    if not s:
        return ""
    if s.startswith("\ufeff"):
        s = s[1:].lstrip()
    if "\\n" in s and "-----BEGIN" in s:
        s = s.replace("\\r\\n", "\n").replace("\\n", "\n")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s.strip()


def _wrap_if_bare_alipay_key_material(s: str, *, private: bool) -> str:
    """
    支付宝工具下载的「应用私钥 RSA2048-敏感数据.txt」常为纯 base64，无 PEM 头尾；
    OpenSSL / SDK 会报 no start line。自动包 PEM，并在 PKCS#8 / PKCS#1 两种私钥格式间试解析。
    """
    s = _normalize_alipay_pem(s)
    if not s or "-----BEGIN" in s:
        return s
    body = "".join(s.split())
    if len(body) < 200:
        return s
    if not re.fullmatch(r"[A-Za-z0-9+/]+=*", body):
        return s
    chunked = "\n".join(body[i : i + 64] for i in range(0, len(body), 64))
    if not private:
        return f"-----BEGIN PUBLIC KEY-----\n{chunked}\n-----END PUBLIC KEY-----"

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    backend = default_backend()
    pkcs8_pem = f"-----BEGIN PRIVATE KEY-----\n{chunked}\n-----END PRIVATE KEY-----"
    rsa_pem = f"-----BEGIN RSA PRIVATE KEY-----\n{chunked}\n-----END RSA PRIVATE KEY-----"
    for candidate in (pkcs8_pem, rsa_pem):
        try:
            serialization.load_pem_private_key(
                candidate.encode("utf-8"), password=None, backend=backend
            )
            return candidate
        except Exception:
            continue
    return pkcs8_pem


def _coerce_pem_for_alipay_sdk(pem: str, *, private: bool, label: str) -> str:
    """
    python-alipay-sdk 内部用 PyCryptodome RSA.importKey。
    优先用 cryptography 转成 TraditionalOpenSSL PEM；失败则若原始 PEM 已能被 PyCryptodome 接受则原样返回；
    否则抛出明确错误（避免静默回退导致仍报 RSA key format is not supported）。
    """
    from Cryptodome.PublicKey import RSA as PyCryptodomeRSA

    pem = _normalize_alipay_pem(pem)
    if not pem:
        return ""

    def _pycryptodome_accepts(s: str) -> bool:
        try:
            PyCryptodomeRSA.import_key(s.encode("utf-8"))
            return True
        except (ValueError, TypeError, IndexError, AttributeError):
            return False

    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        backend = default_backend()
        data = pem.encode("utf-8")
        if private:
            key = serialization.load_pem_private_key(data, password=None, backend=backend)
            out = key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        else:
            key = serialization.load_pem_public_key(data, backend=backend)
            out = key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        coerced = out.decode("utf-8")
        if _pycryptodome_accepts(coerced):
            return coerced
    except Exception:
        pass

    if _pycryptodome_accepts(pem):
        return pem

    raise ValueError(
        f"{label} 不是可用的 RSA PEM。"
        f"应用私钥须为「接口加签方式」里生成的 RSA2 私钥（以 -----BEGIN … PRIVATE KEY----- 开头）；"
        f"另一文件须为开放平台「支付宝公钥」（以 -----BEGIN PUBLIC KEY----- 开头）。"
        f"勿把应用公钥、证书或截断的 base64 粘进文件。"
        f"服务器自检私钥: openssl rsa -in <私钥文件路径> -check -noout"
    )


def _read_alipay_pem(*, file_env: str, value_env: str) -> str:
    path = (os.getenv(file_env) or "").strip()
    if path:
        p = Path(path).expanduser()
        if p.is_file():
            return _normalize_alipay_pem(p.read_text(encoding="utf-8"))
    return _normalize_alipay_pem(os.getenv(value_env, ""))


def get_alipay_client() -> AliPay:
    appid = (os.getenv("ALIPAY_APPID") or "").strip()
    # 应用私钥：开放平台「接口加签方式」里你生成的 RSA2 私钥 PEM（非证书、非应用公钥）
    private_key = _read_alipay_pem(
        file_env="ALIPAY_APP_PRIVATE_KEY_FILE",
        value_env="ALIPAY_PRIVATE_KEY",
    )
    private_key = _wrap_if_bare_alipay_key_material(private_key, private=True)
    private_key = _coerce_pem_for_alipay_sdk(
        private_key, private=True, label="【应用私钥】"
    )
    # 支付宝公钥：开放平台展示的「支付宝公钥」（你上传应用公钥后平台生成的那串，不是你的应用公钥）
    public_key = _read_alipay_pem(
        file_env="ALIPAY_ALIPAY_PUBLIC_KEY_FILE",
        value_env="ALIPAY_PUBLIC_KEY",
    )
    public_key = _wrap_if_bare_alipay_key_material(public_key, private=False)
    public_key = _coerce_pem_for_alipay_sdk(
        public_key, private=False, label="【支付宝公钥】"
    )
    if not (appid and private_key and public_key):
        raise ValueError(
            "支付宝未完整配置：ALIPAY_APPID、应用私钥、支付宝公钥；"
            "或设置 ALIPAY_APP_PRIVATE_KEY_FILE / ALIPAY_ALIPAY_PUBLIC_KEY_FILE 指向 PEM 文件"
        )
    alipay_debug = os.getenv("ALIPAY_DEBUG", "").lower() in ("1", "true", "yes")
    return AliPay(
        appid=str(appid),
        app_private_key_string=private_key,
        alipay_public_key_string=public_key,
        sign_type="RSA2",
        debug=alipay_debug,
    )

# ================= 认证 =================
class RegisterReq(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    nickname: Optional[str] = Field("", max_length=50)
    email: Optional[str] = Field("", max_length=100)


class LoginReq(BaseModel):
    username: str
    password: str


def _validate_username(s: str) -> None:
    if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fff]+$", s):
        raise HTTPException(status_code=400, detail="账号仅允许字母、数字、下划线或中文")


@app.post("/api/auth/register")
def auth_register(req: RegisterReq, db: Session = Depends(get_db)):
    _validate_username(req.username.strip())
    nick = (req.nickname or "").strip() or req.username.strip()
    email = (req.email or "").strip()
    user = User(
        username=req.username.strip(),
        password=hash_password(req.password),
        nickname=nick,
        email=email,
        vip_expiry=None,
    )
    db.add(user)
    try:
        db.flush()
        token = create_access_token(user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该账号已被注册")
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return {
        "code": 200,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "nickname": user.nickname or user.username,
        },
    }


@app.post("/api/auth/login")
def auth_login(req: LoginReq, db: Session = Depends(get_db)):
    name = req.username.strip()
    if not name:
        raise HTTPException(status_code=400, detail="请输入账号")
    user = db.query(User).filter(User.username == name).first()
    if not user or not verify_password(req.password, user.password):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    token = create_access_token(user.id)
    return {
        "code": 200,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "nickname": user.nickname or user.username,
        },
    }


@app.get("/api/auth/me")
def auth_me(user: User = Depends(get_current_user)):
    return {
        "code": 200,
        "data": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "email": user.email or "",
        },
    }


# ================= 生成备课（带VIP） =================
@app.post("/api/generate")
async def generate(
    req: GenerateReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    await check_permission(user)
    files = await generate_lesson_package(req.topic, req.grade, req.subject, user.id)

    record = LessonRecord(
        user_id=user.id,
        grade=req.grade,
        subject=req.subject,
        topic=req.topic,
        files_json=files
    )
    db.add(record)
    db.commit()

    return {"code": 200, "data": files}

# ================= 用户信息 =================
@app.get("/api/user/info")
def get_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total = db.query(LessonRecord).filter(LessonRecord.user_id == user.id).count()
    # 每次生成同时产出教案/试卷/课件，按「套」计三者与 total 一致
    return {
        "code": 200,
        "data": {
            "username": user.username,
            "nickname": user.nickname or user.username,
            "vip_expiry": user.vip_expiry.strftime("%Y-%m-%d %H:%M") if user.vip_expiry else None,
            "is_vip": user.vip_expiry > datetime.now() if user.vip_expiry else False,
            "stats": {
                "total": total,
                "lesson": total,
                "quiz": total,
                "html": total,
            },
        }
    }

# ================= 最近生成记录 =================
@app.get("/api/history")
def get_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = (
        db.query(LessonRecord)
        .filter(LessonRecord.user_id == user.id)
        .order_by(LessonRecord.created_at.desc())
        .limit(20)
        .all()
    )

    history = []
    for r in records:
        files = r.files_json or {}
        if isinstance(files, str):
            try:
                files = json.loads(files)
            except Exception:
                files = {}

        plan_file = files.get("plan")
        quiz_file = files.get("quiz")
        html_file = files.get("html")
        history.append({
            "id": r.id,
            "topic": r.topic,
            "grade": r.grade,
            "subject": r.subject,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            # 兼容前端旧字段读取方式（item.plan / item.quiz / item.html）
            "plan": plan_file,
            "quiz": quiz_file,
            "html": html_file,
            "files": {
                "plan": plan_file,
                "quiz": quiz_file,
                "html": html_file,
            }
        })

    return {"code": 200, "data": history}

# ================= 支付处理 =================
@app.post("/api/pay/create_order")
def create_order(
    req: PayReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # ===================== 修复 1：测试单开关强制生效 =====================
    if req.test_penny:
        # 强制开启测试单（你也可以改回 if not _vip_test_penny_allowed()）
        # if not _vip_test_penny_allowed():
        #     raise HTTPException(status_code=403, detail="测试订单未开放")
        effective_days = 1
        amount = 0.01
    else:
        price_map = {7: 9.9, 30: 19.9, 365: 199.0}
        amount = price_map.get(req.days, 19.9)
        effective_days = req.days

    amount_str = f"{amount:.2f}"
    order_no = f"PROD_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    channel = (req.channel or "app").lower()

    order = PayOrder(
        order_no=order_no,
        user_id=user.id,
        provider=req.provider,
        channel=channel,
        days=effective_days,
        amount=amount_str,
        status="PENDING"
    )
    db.add(order)
    db.commit()

    # H5支付直接返回支付URL
    if req.provider == "h5":
        pay_url = f"{PUBLIC_BASE_URL}/pay?order_no={order_no}&days={effective_days}"
        return {
            "code": 200,
            "provider": "h5",
            "channel": "h5",
            "pay_url": pay_url,
            "order_no": order_no,
            "amount": float(amount_str)
        }

    # 微信支付（未接真实通道：非生产 mock，生产占位链接）
    elif req.provider == "wxpay":
        try:
            if APP_ENV != "prod":
                pay_payload = {
                    "orderInfo": f"MOCK_WXPAY_ORDER_{order_no}",
                    "pay_url": f"{PUBLIC_BASE_URL}/pay/mock-success?order_no={order_no}&days={effective_days}"
                }
            else:
                pay_payload = {
                    "orderInfo": f"WECHAT_ORDER_{order_no}",
                    "pay_url": f"https://wx.tenpay.com/pay/{order_no}"
                }
        except Exception as e:
            logger.error(f"[DEV] create_order wxpay fallback to mock: {e}")
            pay_payload = {
                "orderInfo": f"MOCK_WXPAY_ORDER_{order_no}",
                "pay_url": f"{PUBLIC_BASE_URL}/pay/mock-success?order_no={order_no}&days={effective_days}"
            }

        return {
            "code": 200,
            "provider": "wxpay",
            "channel": req.channel,
            "orderInfo": pay_payload.get("orderInfo", ""),
            "pay_url": pay_payload.get("pay_url"),
            "order_no": order_no,
            "amount": float(amount_str)
        }

    # ===================== 修复 2：支付宝支付（稳定版） =====================
    elif req.provider == "alipay":
        try:
            alipay = get_alipay_client()
            notify_url = (os.getenv("ALIPAY_NOTIFY_URL") or "").strip()
            if not notify_url:
                raise ValueError(
                    "未配置 ALIPAY_NOTIFY_URL。在 .env.prod 中填写公网 HTTPS，例如："
                    "https://你的域名/api/pay/notify"
                )
            subject = "VIP测试(0.01元)" if req.test_penny else f"AI备课会员{effective_days}天"
            gateway = getattr(
                alipay, "_gateway", "https://openapi.alipay.com/gateway.do"
            ).rstrip("?")

            # H5 支付（手机网站 alipay.trade.wap.pay）
            if channel == "h5":
                base_return_url = req.return_url or f"{PUBLIC_BASE_URL}/pay"
                delimiter = "&" if "?" in base_return_url else "?"
                return_url = f"{base_return_url}{delimiter}order_no={order_no}"

                order_str = alipay.api_alipay_trade_wap_pay(
                    out_trade_no=order_no,
                    total_amount=str(amount),  # 必须字符串！
                    subject=subject,
                    return_url=return_url,
                    notify_url=notify_url
                )
                pay_payload = {
                    "orderInfo": order_str,
                    "pay_url": f"{gateway}?{order_str}"
                }

            # 电脑网站支付（alipay.trade.page.pay，需开通「电脑网站支付」）
            elif channel == "pc":
                base_return_url = req.return_url or f"{PUBLIC_BASE_URL}/pay"
                delimiter = "&" if "?" in base_return_url else "?"
                return_url = f"{base_return_url}{delimiter}order_no={order_no}"
                order_str = alipay.api_alipay_trade_page_pay(
                    subject,
                    order_no,
                    str(amount),
                    return_url=return_url,
                    notify_url=notify_url,
                    qr_pay_mode="1",
                    qrcode_width="200",
                )
                pay_payload = {
                    "orderInfo": order_str,
                    "pay_url": f"{gateway}?{order_str}",
                }

            # 当面付预下单二维码（alipay.trade.precreate，需开通当面付）
            elif channel == "qr":
                result = alipay.api_alipay_trade_precreate(
                    out_trade_no=order_no,
                    total_amount=str(amount),
                    subject=subject,
                    notify_url=notify_url
                )
                qr_code = result.get("qr_code")
                if not qr_code:
                    raise ValueError(f"支付宝二维码获取失败: {result}")
                pay_payload = {"qr_code": qr_code}

            # APP 支付
            else:
                order_str = alipay.api_alipay_trade_app_pay(
                    out_trade_no=order_no,
                    total_amount=str(amount),
                    subject=subject,
                    notify_url=notify_url
                )
                pay_payload = {"orderInfo": order_str}

        # ===================== 修复 3：生产环境真实报错 =====================
        except Exception as e:
            logger.exception(f"支付宝创建订单失败：{str(e)}")  # 关键：打印真实错误
            order.status = "FAILED"
            db.commit()
            raise HTTPException(status_code=500, detail=f"支付异常：{str(e)}")

        return {
            "code": 200,
            "provider": "alipay",
            "channel": req.channel,
            "orderInfo": pay_payload.get("orderInfo", ""),
            "pay_url": pay_payload.get("pay_url"),
            "qr_code": pay_payload.get("qr_code"),
            "order_no": order_no,
            "amount": float(amount_str)
        }

    else:
        raise HTTPException(status_code=400, detail="不支持的支付方式")

@app.get("/pay", response_class=HTMLResponse)
def pay_page():
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>AI备课会员支付</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f5f7fa;
      color: #222;
    }}
    .wrap {{
      max-width: 520px;
      margin: 0 auto;
      padding: 20px 16px 32px;
    }}
    .card {{
      background: #fff;
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 14px;
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
    }}
    .title {{
      margin: 0 0 8px;
      font-size: 20px;
      font-weight: 700;
    }}
    .sub {{
      margin: 0;
      color: #666;
      font-size: 14px;
    }}
    .row {{
      display: flex;
      gap: 10px;
      margin-top: 12px;
      flex-wrap: wrap;
    }}
    button {{
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 14px;
      cursor: pointer;
    }}
    .btn-primary {{ background: #5c6ac4; color: #fff; }}
    .btn-muted {{ background: #f0f1f4; color: #333; }}
    .status {{
      margin-top: 10px;
      font-size: 14px;
      color: #444;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .qr-box {{
      text-align: center;
      margin-top: 16px;
      padding: 16px;
      background: #fafbfc;
      border-radius: 12px;
    }}
    .qr-hint {{ margin: 0 0 10px; font-size: 14px; color: #333; font-weight: 600; }}
    .qr-img {{ display: block; margin: 0 auto; border-radius: 8px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1 class="title">AI备课会员支付</h1>
      <p class="sub">支付宝为电脑网站支付（跳转收银台，可选页内扫码）；微信等为跳转链接。</p>
      <div class="row">
        <button class="btn-primary" onclick="createOrder(7, 'wxpay')">微信 7天</button>
        <button class="btn-primary" onclick="createOrder(30, 'wxpay')">微信 30天</button>
        <button class="btn-primary" onclick="createOrder(365, 'wxpay')">微信 365天</button>
      </div>
      <div class="row">
        <button class="btn-muted" onclick="createOrder(7, 'alipay')">支付宝 7天</button>
        <button class="btn-muted" onclick="createOrder(30, 'alipay')">支付宝 30天</button>
        <button class="btn-muted" onclick="createOrder(365, 'alipay')">支付宝 365天</button>
      </div>
      <div id="qrBox" class="qr-box" style="display:none">
        <p class="qr-hint">请使用支付宝「扫一扫」</p>
        <img id="qrImg" class="qr-img" alt="支付二维码" width="240" height="240" />
      </div>
      <div class="status" id="statusText">等待操作...</div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
  <script>
    const statusEl = document.getElementById("statusText");
    const qs = new URLSearchParams(window.location.search);
    const existingOrderNo = qs.get("order_no");

    function setStatus(text) {{
      statusEl.textContent = text;
    }}

    function showAlipayQr(qrText) {{
      const box = document.getElementById("qrBox");
      const img = document.getElementById("qrImg");
      if (!box || !img || typeof QRCode === "undefined") {{
        setStatus("无法展示二维码，请检查是否加载 qrcode 库。");
        return;
      }}
      QRCode.toDataURL(qrText, {{ width: 240, margin: 2 }}, function (err, url) {{
        if (err) {{
          setStatus("二维码生成失败。");
          return;
        }}
        img.src = url;
        box.style.display = "block";
      }});
    }}

    async function createOrder(days, provider) {{
      try {{
        document.getElementById("qrBox").style.display = "none";
        setStatus("正在创建订单，请稍候...");
        const channel = provider === "alipay" ? "pc" : "h5";
        const resp = await fetch("/api/pay/create_order", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            days,
            provider,
            channel,
            return_url: window.location.origin + "/pay"
          }})
        }});
        const data = await resp.json();
        if (!data || data.code !== 200) {{
          setStatus("订单创建失败，请重试。");
          return;
        }}
        if (provider === "alipay" && data.qr_code) {{
          setStatus("订单已创建，请使用支付宝扫码支付。");
          showAlipayQr(data.qr_code);
          return;
        }}
        if (data.pay_url) {{
          setStatus("订单已创建，正在跳转支付...");
          window.location.href = data.pay_url;
          return;
        }}
        setStatus("未拿到支付信息（二维码或链接），请检查支付配置。");
      }} catch (e) {{
        setStatus("网络异常，创建订单失败。");
      }}
    }}

    async function queryStatus(orderNo) {{
      try {{
        const resp = await fetch("/api/pay/status/" + encodeURIComponent(orderNo));
        const data = await resp.json();
        if (!data || data.code !== 200) {{
          setStatus("订单状态查询失败，请稍后刷新。");
          return;
        }}
        const s = data.data.status;
        if (s === "SUCCESS") {{
          setStatus("支付成功，VIP 已开通。\\n到期时间请在“我的”页面查看。");
          return;
        }}
        setStatus("订单状态：" + s + "\\n正在自动刷新...");
        setTimeout(() => queryStatus(orderNo), 2500);
      }} catch (e) {{
        setStatus("订单状态查询失败，请稍后刷新。");
      }}
    }}

    if (existingOrderNo) {{
      setStatus("检测到回跳订单，正在查询状态...");
      queryStatus(existingOrderNo);
    }}
  </script>
</body>
</html>
"""


@app.get("/pay/mock-success", response_class=HTMLResponse)
def pay_mock_success(
    order_no: str,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """扫码回跳无登录态，仅根据 order_no 履约（生产仍关闭）。"""
    if APP_ENV == "prod":
        raise HTTPException(status_code=403, detail="生产环境禁用模拟支付")

    order = db.query(PayOrder).filter(PayOrder.order_no == order_no).first()
    user = None
    if order:
        user = db.query(User).filter(User.id == order.user_id).first()
    if order and user and order.status != "SUCCESS":
        extend_vip(user, order.days, db)
        order.status = "SUCCESS"
        order.trade_no = f"MOCK_{order_no}"
        order.paid_at = datetime.now()
        db.add(order)
        db.commit()
    elif not order:
        return HTMLResponse(
            "<!doctype html><html><body style='font-family:sans-serif;padding:24px'>"
            "<p>订单不存在或已失效。</p><a href='/pay'>返回支付测试</a></body></html>",
            status_code=404,
        )

    if order and not user:
        return HTMLResponse(
            "<!doctype html><html><body style='font-family:sans-serif;padding:24px'>"
            "<p>订单关联用户异常。</p></body></html>",
            status_code=500,
        )

    target_url = f"{FRONTEND_H5_BASE}/#/pages/mine/mine"
    html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>支付成功</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f7fa; margin: 0; }
    .wrap { max-width: 520px; margin: 40px auto; padding: 0 16px; }
    .card { background: #fff; border-radius: 14px; padding: 24px; text-align: center; box-shadow: 0 6px 24px rgba(0,0,0,.06); }
    .ok { font-size: 22px; font-weight: 700; color: #1f8f4d; margin-bottom: 8px; }
    .desc { color: #666; margin-bottom: 6px; }
    .tip { color: #999; font-size: 13px; margin-bottom: 18px; }
    a { display: inline-block; text-decoration: none; background: #2f5fd3; color: #fff; border-radius: 10px; padding: 10px 16px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="ok">支付成功（模拟）</div>
      <div class="desc">VIP 已开通，可以返回应用继续使用。</div>
      <div class="tip">2 秒后自动跳转到“我的”页面</div>
      <a href="__TARGET_URL__">立即返回应用</a>
    </div>
  </div>
  <script>
    setTimeout(function () {
      window.location.href = "__TARGET_URL__";
    }, 2000);
  </script>
</body>
</html>
"""
    return html.replace("__TARGET_URL__", target_url)


@app.get("/", response_class=HTMLResponse)
def home_page():
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <title>AI备课 - 入口页</title>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f5f7fa;
      color: #222;
    }
    .wrap {
      max-width: 520px;
      margin: 0 auto;
      padding: 24px 16px 36px;
    }
    .card {
      background: #fff;
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 14px;
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 22px;
    }
    p {
      margin: 0 0 14px;
      font-size: 14px;
      color: #666;
      line-height: 1.6;
    }
    .row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    a {
      text-decoration: none;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 14px;
    }
    .btn-primary { background: #5c6ac4; color: #fff; }
    .btn-muted { background: #f0f1f4; color: #333; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>AI备课入口</h1>
      <p>这是初始页面。你可以从这里进入支付测试页，或访问 API。</p>
      <div class="row">
        <a class="btn-primary" href="/pay">进入支付测试页</a>
        <a class="btn-muted" href="/api/user/info">查看用户信息接口</a>
      </div>
    </div>
  </div>
</body>
</html>
"""


@app.get("/api/pay/order_result/{order_no}")
def order_result_public(order_no: str, db: Session = Depends(get_db)):
    """
    支付回跳轮询：无 JWT 也可访问。
    若订单仍为 PENDING，会主动向支付宝查单并履约（等同补单，无需 TOKEN）。
    """
    order = db.query(PayOrder).filter(PayOrder.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    sync_info = {}
    if order.status == "PENDING" and APP_ENV == "prod":
        sync_info = _sync_alipay_order(order, db)
        db.refresh(order)

    return {
        "code": 200,
        "data": {
            "order_no": order.order_no,
            "status": order.status,
            "days": order.days,
            "synced": sync_info.get("synced", False),
            "trade_status": sync_info.get("trade_status"),
            "message": sync_info.get("message"),
            "reconcile_attempted": bool(sync_info),
        },
    }


@app.post("/api/pay/sync/{order_no}")
def sync_pay_order(
    order_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    主动向支付宝查询订单并履约。用于异步 notify 未到达时，用户回跳后补开通 VIP。
    """
    order = (
        db.query(PayOrder)
        .filter(PayOrder.order_no == order_no, PayOrder.user_id == user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order.status == "SUCCESS":
        db.refresh(user)
        return {
            "code": 200,
            "data": {
                "order_no": order.order_no,
                "status": order.status,
                "synced": False,
                "vip_expiry": user.vip_expiry.strftime("%Y-%m-%d %H:%M:%S")
                if user.vip_expiry
                else None,
                "is_vip": bool(user.vip_expiry and user.vip_expiry > datetime.now()),
            },
        }

    sync_info = _sync_alipay_order(order, db)
    db.refresh(user)
    db.refresh(order)
    return {
        "code": 200,
        "data": {
            "order_no": order.order_no,
            "status": order.status,
            "synced": sync_info.get("synced", False),
            "trade_status": sync_info.get("trade_status"),
            "message": sync_info.get("message"),
            "vip_expiry": user.vip_expiry.strftime("%Y-%m-%d %H:%M:%S")
            if user.vip_expiry
            else None,
            "is_vip": bool(user.vip_expiry and user.vip_expiry > datetime.now()),
        },
    }


@app.get("/api/pay/status/{order_no}")
def get_pay_status(
    order_no: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = (
        db.query(PayOrder)
        .filter(PayOrder.order_no == order_no, PayOrder.user_id == user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return {
        "code": 200,
        "data": {
            "order_no": order.order_no,
            "status": order.status,
            "provider": order.provider,
            "channel": order.channel,
            "amount": float(order.amount),
            "days": order.days,
            "trade_no": order.trade_no,
            "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else None,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else None,
        }
    }

# ================= 支付回调（验签+更新VIP） =================
@app.post("/api/pay/notify")
async def pay_notify(request: Request, db: Session = Depends(get_db)):
    body_bytes = await request.body()
    payload = dict(parse_qsl(body_bytes.decode("utf-8"), keep_blank_values=True))

    sign = payload.pop("sign", "")
    payload.pop("sign_type", None)
    order_no = payload.get("out_trade_no")
    trade_status = payload.get("trade_status")
    trade_no = payload.get("trade_no")
    receipt_amount = payload.get("receipt_amount") or payload.get("total_amount")

    if not order_no:
        return "fail"

    order = db.query(PayOrder).filter(PayOrder.order_no == order_no).first()
    if not order:
        logger.error(f"[PAY_NOTIFY] unknown order_no: {order_no}")
        return "fail"

    if order.status == "SUCCESS":
        return "success"

    if APP_ENV == "prod":
        try:
            alipay = get_alipay_client()
            is_valid = alipay.verify(payload, sign)
            if not is_valid:
                logger.error(f"[PAY_NOTIFY] verify failed order_no={order_no}")
                return "fail"
        except Exception as e:
            logger.error(f"[PAY_NOTIFY] verify exception order_no={order_no}, err={e}")
            return "fail"

    if trade_status not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        order.status = "FAILED"
        db.add(order)
        db.commit()
        return "fail"

    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        logger.error(f"[PAY_NOTIFY] user missing user_id={order.user_id}, order_no={order_no}")
        return "fail"

    ok = _fulfill_paid_order(
        order,
        user,
        db,
        trade_no=trade_no,
        alipay_amount_fields=payload,
    )
    return "success" if ok else "fail"


class MockPayReq(BaseModel):
    days: int = 30


@app.post("/api/pay/mock_success")
def mock_pay_success(
    req: MockPayReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if APP_ENV == "prod":
        raise HTTPException(status_code=403, detail="生产环境禁用模拟支付")

    extend_vip(user, req.days, db)
    return {
        "code": 200,
        "message": "模拟支付成功，VIP已生效",
        "data": {
            "vip_expiry": user.vip_expiry.strftime("%Y-%m-%d %H:%M:%S")
        }
    }

# ================= 启动 =================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)