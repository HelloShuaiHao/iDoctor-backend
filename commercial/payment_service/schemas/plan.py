"""订阅计划 Pydantic 模型"""
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field
from uuid import UUID


class SubscriptionPlanBase(BaseModel):
    """订阅计划基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    currency: str = Field(default="CNY", pattern="^(CNY|USD)$")
    billing_cycle: str = Field(..., pattern="^(monthly|yearly|lifetime)$")
    quota_type: str = Field(..., min_length=1, max_length=50)
    quota_limit: int = Field(..., ge=0)
    features: Optional[Dict[str, Any]] = None


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """创建订阅计划"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """更新订阅计划"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    quota_limit: Optional[int] = Field(None, ge=0)
    features: Optional[Dict[str, Any]] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    """订阅计划响应"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
