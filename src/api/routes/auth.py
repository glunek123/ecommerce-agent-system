"""认证接口：颁发 token。

注意：示例实现，未集成真实用户体系。生产环境应对接 OAuth2/OIDC 或 DB 用户表。
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..middleware import create_access_token

router = APIRouter()


class TokenRequest(BaseModel):
    user_id: str = Field(description="用户 ID")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def issue_token(request: TokenRequest):
    """开发用：根据 user_id 直接颁发 JWT。生产环境必须先校验用户身份。"""
    return TokenResponse(access_token=create_access_token(request.user_id))
