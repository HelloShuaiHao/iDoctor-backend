"""API Key Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class APIKeyCreate(BaseModel):
    """创建 API Key"""
    name: str = Field(..., min_length=1, max_length=100)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API Key 响应"""
    id: UUID
    key_prefix: str
    name: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyWithSecret(APIKeyResponse):
    """带完整密钥的响应（仅创建时返回一次）"""
    key: str
