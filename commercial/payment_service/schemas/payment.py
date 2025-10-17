"""支付 Pydantic 模型"""
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID


class PaymentCreateRequest(BaseModel):
    """创建支付请求"""
    subscription_id: Optional[UUID] = None
    amount: Decimal
    currency: str = "CNY"
    payment_method: str  # alipay/wechat
    return_url: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class PaymentResponse(BaseModel):
    """支付响应"""
    id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    payment_url: Optional[str] = None  # 支付链接（支付宝）或二维码链接（微信）
    qr_code: Optional[str] = None  # 微信支付二维码内容
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookEvent(BaseModel):
    """Webhook 事件"""
    event_type: str
    transaction_id: str
    status: str
    data: Dict[str, Any]
