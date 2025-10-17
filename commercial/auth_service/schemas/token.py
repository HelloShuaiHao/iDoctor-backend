"""Token Pydantic 模型"""
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload"""
    sub: Optional[UUID] = None  # subject (user_id)
    exp: Optional[int] = None  # expiration time
    type: Optional[str] = None  # access or refresh
