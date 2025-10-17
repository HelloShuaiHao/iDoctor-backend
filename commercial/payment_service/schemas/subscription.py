"""用户订阅 Pydantic 模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class SubscriptionCreateRequest(BaseModel):
    """创建订阅请求"""
    plan_id: UUID
    payment_method: str  # alipay/wechat


class UserSubscriptionResponse(BaseModel):
    """用户订阅响应"""
    id: UUID
    user_id: UUID
    plan_id: UUID
    status: str
    current_period_start: datetime
    current_period_end: datetime
    quota_used: int
    quota_limit: int
    auto_renew: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionWithPlan(UserSubscriptionResponse):
    """带计划信息的订阅"""
    plan_name: str
    plan_price: float
    plan_currency: str
