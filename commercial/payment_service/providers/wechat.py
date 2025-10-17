"""微信支付提供商"""
from decimal import Decimal
from typing import Dict, Any, Optional
import time
from wechatpy.pay import WeChatPay
from wechatpy.exceptions import WeChatPayException
from .base import PaymentProvider, PaymentStatus, RefundResult


class WechatProvider(PaymentProvider):
    """微信支付提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 初始化微信支付客户端
        self.client = WeChatPay(
            appid=config["app_id"],
            mch_id=config["mch_id"],
            api_key=config["api_key"],
            mch_cert=config.get("cert_path"),
            mch_key=config.get("key_path")
        )

    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "CNY",
        subject: str = "订阅付款",
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建微信支付（Native扫码支付）"""
        # 金额转换为分
        total_fee = int(amount * 100)

        # 创建统一下单
        result = self.client.order.create(
            trade_type="NATIVE",  # 扫码支付
            body=subject,
            out_trade_no=order_id,
            total_fee=total_fee,
            notify_url=self.config.get("notify_url"),
            client_ip=kwargs.get("client_ip", "127.0.0.1")
        )

        return {
            "qr_code": result["code_url"],  # 二维码链接
            "order_id": order_id
        }

    async def verify_payment(self, transaction_id: str) -> PaymentStatus:
        """查询微信支付状态"""
        try:
            result = self.client.order.query(out_trade_no=transaction_id)
            trade_state = result.get("trade_state")

            if trade_state == "SUCCESS":
                return PaymentStatus.COMPLETED
            elif trade_state in ["CLOSED", "REVOKED", "PAYERROR"]:
                return PaymentStatus.FAILED
            else:
                return PaymentStatus.PENDING
        except WeChatPayException:
            return PaymentStatus.PENDING

    async def verify_webhook(self, request_data: Dict[str, Any]) -> bool:
        """验证微信支付回调签名"""
        try:
            return self.client.check_signature(request_data)
        except Exception:
            return False

    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理微信支付回调"""
        # 解析XML数据
        try:
            data = self.client.parse_payment_result(request_data)

            return {
                "order_id": data.get("out_trade_no"),
                "transaction_id": data.get("transaction_id"),
                "status": "completed" if data.get("result_code") == "SUCCESS" else "failed",
                "amount": str(Decimal(data.get("total_fee", 0)) / 100)  # 分转元
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
        reason: str = "用户申请退款"
    ) -> RefundResult:
        """微信退款"""
        # 金额转换为分
        refund_fee = int(amount * 100)

        try:
            result = self.client.refund.apply(
                out_trade_no=transaction_id,
                out_refund_no=f"refund_{transaction_id}_{int(time.time())}",
                total_fee=refund_fee,
                refund_fee=refund_fee,
                refund_desc=reason
            )

            if result.get("result_code") == "SUCCESS":
                return RefundResult(
                    success=True,
                    refund_id=result.get("refund_id"),
                    message="退款成功"
                )
            else:
                return RefundResult(
                    success=False,
                    message=result.get("err_code_des", "退款失败")
                )
        except Exception as e:
            return RefundResult(
                success=False,
                message=str(e)
            )
