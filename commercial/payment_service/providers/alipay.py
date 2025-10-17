"""支付宝支付提供商"""
from decimal import Decimal
from typing import Dict, Any, Optional
import json
import logging
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from alipay.aop.api.domain.AlipayTradeWapPayModel import AlipayTradeWapPayModel
from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
from alipay.aop.api.request.AlipayTradeWapPayRequest import AlipayTradeWapPayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest
from .base import PaymentProvider, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class AlipayProvider(PaymentProvider):
    """支付宝支付提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 在开发环境中使用模拟配置
        if config.get("sandbox", True):
            # 开发环境：使用模拟配置
            app_private_key = "DEV_PRIVATE_KEY_PLACEHOLDER"
            alipay_public_key = "DEV_PUBLIC_KEY_PLACEHOLDER"
        else:
            # 生产环境：读取真实密钥文件
            try:
                with open(config["private_key_path"], "r") as f:
                    app_private_key = f.read()
                with open(config["public_key_path"], "r") as f:
                    alipay_public_key = f.read()
            except (FileNotFoundError, KeyError):
                raise ValueError("生产环境必须配置正确的支付宝密钥文件")

        # 保存sandbox标志
        self.is_sandbox = config.get("sandbox", True)
        
        if not self.is_sandbox:
            # 生产环境：配置真实客户端
            alipay_config = AlipayClientConfig()
            alipay_config.server_url = config.get("gateway", "https://openapi.alipaydev.com/gateway.do")
            alipay_config.app_id = config.get("app_id", "")
            alipay_config.app_private_key = app_private_key
            alipay_config.alipay_public_key = alipay_public_key
            self.client = DefaultAlipayClient(alipay_client_config=alipay_config)
        else:
            # 开发环境：不初始化真实客户端
            self.client = None

    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "CNY",
        subject: str = "订阅付款",
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建支付宝支付（PC网站支付或手机H5支付）

        Args:
            order_id: 订单ID
            amount: 支付金额
            currency: 货币类型
            subject: 订单标题
            return_url: 支付完成后跳转地址
            **kwargs: 额外参数
                - payment_type: "page" (PC网站) 或 "wap" (手机H5)，默认 "page"
                - quit_url: H5支付用户点击返回的地址
        """
        if self.is_sandbox:
            # 开发环境：返回模拟数据
            logger.info(f"沙箱模式：创建支付宝支付订单 {order_id}, 金额 {amount}")
            return {
                "payment_url": f"https://sandbox-alipay.com/mock-payment?order_id={order_id}&amount={amount}",
                "provider_order_id": f"alipay_mock_{order_id}",
                "order_id": order_id
            }

        # 生产环境：使用真实 API
        payment_type = kwargs.get("payment_type", "page")  # 默认PC网站支付

        try:
            if payment_type == "wap":
                # 手机H5支付
                logger.info(f"创建支付宝H5支付订单: {order_id}, 金额: {amount}")
                return await self._create_wap_payment(order_id, amount, subject, return_url, **kwargs)
            else:
                # PC网站支付
                logger.info(f"创建支付宝PC网站支付订单: {order_id}, 金额: {amount}")
                return await self._create_page_payment(order_id, amount, subject, return_url, **kwargs)
        except Exception as e:
            logger.error(f"创建支付宝支付失败: {str(e)}", exc_info=True)
            raise

    async def _create_page_payment(
        self,
        order_id: str,
        amount: Decimal,
        subject: str,
        return_url: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """创建PC网站支付"""
        model = AlipayTradePagePayModel()
        model.out_trade_no = order_id
        model.total_amount = str(amount)
        model.subject = subject
        model.product_code = "FAST_INSTANT_TRADE_PAY"

        # 可选参数
        if kwargs.get("body"):
            model.body = kwargs["body"]
        if kwargs.get("timeout_express"):
            model.timeout_express = kwargs["timeout_express"]
        else:
            model.timeout_express = "30m"  # 默认30分钟超时

        request = AlipayTradePagePayRequest(biz_model=model)
        request.notify_url = self.config.get("notify_url")
        request.return_url = return_url or self.config.get("return_url")

        # 获取支付表单（HTML form）
        response = self.client.page_execute(request, http_method="GET")

        logger.info(f"支付宝PC网站支付创建成功: {order_id}")

        return {
            "payment_url": response,  # 这是一个完整的支付URL
            "provider_order_id": order_id,
            "order_id": order_id,
            "payment_type": "page"
        }

    async def _create_wap_payment(
        self,
        order_id: str,
        amount: Decimal,
        subject: str,
        return_url: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """创建手机H5支付"""
        model = AlipayTradeWapPayModel()
        model.out_trade_no = order_id
        model.total_amount = str(amount)
        model.subject = subject
        model.product_code = "QUICK_WAP_WAY"

        # 可选参数
        if kwargs.get("body"):
            model.body = kwargs["body"]
        if kwargs.get("timeout_express"):
            model.timeout_express = kwargs["timeout_express"]
        else:
            model.timeout_express = "30m"

        # H5特有参数
        quit_url = kwargs.get("quit_url", return_url)

        request = AlipayTradeWapPayRequest(biz_model=model)
        request.notify_url = self.config.get("notify_url")
        request.return_url = return_url or self.config.get("return_url")

        # 设置退出URL（用户点击返回按钮）
        if quit_url:
            request.quit_url = quit_url

        # 获取支付表单
        response = self.client.page_execute(request, http_method="GET")

        logger.info(f"支付宝H5支付创建成功: {order_id}")

        return {
            "payment_url": response,
            "provider_order_id": order_id,
            "order_id": order_id,
            "payment_type": "wap"
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
