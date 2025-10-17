"""支付宝支付提供商"""
from decimal import Decimal
from typing import Dict, Any, Optional
import json
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest
from .base import PaymentProvider, PaymentStatus, RefundResult


class AlipayProvider(PaymentProvider):
    """支付宝支付提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 读取私钥文件（如果提供的是文件路径）
        if config.get("private_key_path") and config.get("public_key_path"):
            # 使用文件路径
            try:
                with open(config["private_key_path"], "r") as f:
                    app_private_key = f.read()
                with open(config["public_key_path"], "r") as f:
                    alipay_public_key = f.read()
            except FileNotFoundError:
                # 文件不存在，使用模拟值
                app_private_key = "fake_private_key_for_development"
                alipay_public_key = "fake_public_key_for_development"
        else:
            # 直接使用字符串
            app_private_key = config.get("private_key", "fake_private_key_for_development")
            alipay_public_key = config.get("public_key", "fake_public_key_for_development")

        # 配置客户端
        alipay_config = AlipayClientConfig()
        alipay_config.server_url = config.get("gateway", "https://openapi.alipaydev.com/gateway.do")
        alipay_config.app_id = config["app_id"]
        alipay_config.app_private_key = app_private_key
        alipay_config.alipay_public_key = alipay_public_key

        self.client = DefaultAlipayClient(alipay_client_config=alipay_config)

    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "CNY",
        subject: str = "订阅付款",
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建支付宝支付（PC网站支付）"""
        model = AlipayTradePagePayModel()
        model.out_trade_no = order_id
        model.total_amount = str(amount)
        model.subject = subject
        model.product_code = "FAST_INSTANT_TRADE_PAY"

        request = AlipayTradePagePayRequest(biz_model=model)
        request.notify_url = self.config.get("notify_url")
        if return_url:
            request.return_url = return_url

        # 获取支付链接
        response = self.client.page_execute(request, http_method="GET")

        return {
            "payment_url": response,
            "order_id": order_id
        }

    async def verify_payment(self, transaction_id: str) -> PaymentStatus:
        """查询支付状态"""
        request = AlipayTradeQueryRequest()
        request.biz_content = json.dumps({"out_trade_no": transaction_id})

        response = self.client.execute(request)
        response_dict = json.loads(response)

        alipay_response = response_dict.get("alipay_trade_query_response", {})
        trade_status = alipay_response.get("trade_status")

        if trade_status == "TRADE_SUCCESS":
            return PaymentStatus.COMPLETED
        elif trade_status == "TRADE_CLOSED":
            return PaymentStatus.FAILED
        else:
            return PaymentStatus.PENDING

    async def verify_webhook(self, request_data: Dict[str, Any]) -> bool:
        """验证支付宝回调签名"""
        sign = request_data.get("sign")
        if not sign:
            return False

        # 移除sign和sign_type参数
        params = {k: v for k, v in request_data.items() if k not in ["sign", "sign_type"]}

        # 支付宝SDK会自动验证
        return self.client.verify(params, sign)

    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理支付宝回调"""
        return {
            "order_id": request_data.get("out_trade_no"),
            "transaction_id": request_data.get("trade_no"),
            "status": "completed" if request_data.get("trade_status") == "TRADE_SUCCESS" else "failed",
            "amount": request_data.get("total_amount")
        }

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
        reason: str = "用户申请退款"
    ) -> RefundResult:
        """支付宝退款"""
        request = AlipayTradeRefundRequest()
        request.biz_content = json.dumps({
            "out_trade_no": transaction_id,
            "refund_amount": str(amount),
            "refund_reason": reason
        })

        response = self.client.execute(request)
        response_dict = json.loads(response)

        alipay_response = response_dict.get("alipay_trade_refund_response", {})

        if alipay_response.get("code") == "10000":
            return RefundResult(
                success=True,
                refund_id=alipay_response.get("trade_no"),
                message="退款成功"
            )
        else:
            return RefundResult(
                success=False,
                message=alipay_response.get("sub_msg", "退款失败")
            )
