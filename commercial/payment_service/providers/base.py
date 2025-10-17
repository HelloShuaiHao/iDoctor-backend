"""支付提供商抽象基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel


class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class RefundResult(BaseModel):
    """退款结果"""
    success: bool
    refund_id: Optional[str] = None
    message: str


class PaymentProvider(ABC):
    """支付提供商抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "CNY",
        subject: str = "订阅付款",
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建支付订单

        Args:
            order_id: 订单ID
            amount: 金额
            currency: 货币
            subject: 订单标题
            return_url: 回调URL
            **kwargs: 其他参数

        Returns:
            Dict包含payment_url或qr_code等
        """
        pass

    @abstractmethod
    async def verify_payment(self, transaction_id: str) -> PaymentStatus:
        """查询支付状态

        Args:
            transaction_id: 交易ID

        Returns:
            PaymentStatus
        """
        pass

    @abstractmethod
    async def verify_webhook(self, request_data: Dict[str, Any]) -> bool:
        """验证Webhook签名

        Args:
            request_data: 请求数据

        Returns:
            bool: 验证是否通过
        """
        pass

    @abstractmethod
    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理支付回调

        Args:
            request_data: 请求数据

        Returns:
            Dict包含order_id, status等信息
        """
        pass

    @abstractmethod
    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
        reason: str = "用户申请退款"
    ) -> RefundResult:
        """退款

        Args:
            transaction_id: 交易ID
            amount: 退款金额
            reason: 退款原因

        Returns:
            RefundResult
        """
        pass
