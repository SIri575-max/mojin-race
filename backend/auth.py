import hashlib
import hmac
import os
import time
import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db, User

SECRET_KEY = os.environ.get("SECRET_KEY", "mojin-race-dev-secret")
ALGORITHM = "HS256"
TOKEN_TTL = 7 * 24 * 3600  # 7 天


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def create_token(user_id: int) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + TOKEN_TTL}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")
    user = db.get(User, payload["uid"])
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_admin_key(x_admin_key: str = Header(default="")):
    """恢复密钥认证：用 SECRET_KEY 作为管理密钥，不依赖数据库用户表。

    用于部署后（容器重建、用户表被清空）恢复数据，以及数据导出/备份等
    管理操作。密钥通过请求头 X-Admin-Key 传入，与部署时注入的 SECRET_KEY 一致。
    """
    if not x_admin_key or not hmac.compare_digest(x_admin_key, SECRET_KEY):
        raise HTTPException(status_code=403, detail="无效的管理密钥")
    return True
