"""JWT 认证中间件 + token 颁发工具。

使用方式：
- `require_auth` 作为 FastAPI 依赖项保护路由
- `create_access_token(user_id)` 颁发 token
- 关闭鉴权：在 .env 中设置 AUTH_ENABLED=false
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...config import get_settings

_bearer = HTTPBearer(auto_error=False)


def create_access_token(user_id: str, extra_claims: dict | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


def require_auth(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    settings = get_settings()
    if not settings.auth_enabled:
        return {"sub": "anonymous", "auth_disabled": True}
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    return decode_token(creds.credentials)
