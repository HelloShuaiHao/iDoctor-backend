"""微信支付提供商"""
from decimal import Decimal
from typing import Dict, Any, Optional
import time
import logging
from wechatpy.pay import WeChatPay
from wechatpy.exceptions import WeChatPayException
from .base import PaymentProvider, PaymentStatus, RefundResult

logger = logging.getLogger(__name__)


class WechatProvider(PaymentProvider):
    """微信支付提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 保存sandbox标志
        self.is_sandbox = config.get("sandbox", True)

        if not self.is_sandbox:
            # 生产环境：初始化真实客户端
            self.client = WeChatPay(
                appid=config.get("app_id", ""),
                mch_id=config.get("mch_id", ""),
                api_key=config.get("api_key", ""),
                mch_cert=config.get("cert_path"),
                mch_key=config.get("key_path")
            )
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
        """创建微信支付（Native扫码支付）

        Args:
            order_id: 订单ID
            amount: 支付金额（元）
            currency: 货币类型
            subject: 订单标题
            return_url: 支付完成后跳转地址（微信Native支付不使用此参数）
            **kwargs: 额外参数
                - client_ip: 用户IP地址
                - detail: 商品详情
                - attach: 附加数据，在查询API和支付通知中原样返回
                - goods_tag: 商品标记，优惠功能参数
        """
        if self.is_sandbox:
            # 开发环境：返回模拟二维码数据
            logger.info(f"沙箱模式：创建微信支付订单 {order_id}, 金额 {amount}")
            return {
                "qr_code": f"weixin://wxpay/bizpayurl?order_id={order_id}&amount={amount}",
                "provider_order_id": f"wechat_mock_{order_id}",
                "order_id": order_id,
                "payment_type": "native"
            }

        # 生产环境：使用真实 API
        try:
            # 金额转换为分（微信支付金额单位是分）
            total_fee = int(amount * 100)

            logger.info(f"创建微信Native扫码支付订单: {order_id}, 金额: {total_fee}分")

            # 构建统一下单参数
            order_params = {
                "trade_type": "NATIVE",  # Native扫码支付
                "body": subject[:128],   # 商品描述，最多128字节
                "out_trade_no": order_id,
                "total_fee": total_fee,
                "notify_url": self.config.get("notify_url"),
                "spbill_create_ip": kwargs.get("client_ip", "127.0.0.1"),
            }

            # 可选参数
            if kwargs.get("detail"):
                order_params["detail"] = kwargs["detail"]
            if kwargs.get("attach"):
                order_params["attach"] = kwargs["attach"]
            if kwargs.get("goods_tag"):
                order_params["goods_tag"] = kwargs["goods_tag"]

            # 创建统一下单
            result = self.client.order.create(**order_params)

            logger.info(f"微信Native扫码支付创建成功: {order_id}, prepay_id: {result.get('prepay_id')}")

            return {
                "qr_code": result["code_url"],  # 二维码链接（用于生成二维码图片）
                "provider_order_id": result.get("prepay_id", order_id),
                "order_id": order_id,
                "payment_type": "native"
            }

        except WeChatPayException as e:
            logger.error(f"微信支付API错误: {str(e)}", exc_info=True)
            raise Exception(f"微信支付创建失败: {e.errmsg if hasattr(e, 'errmsg') else str(e)}")
        except Exception as e:
            logger.error(f"创建微信支付失败: {str(e)}", exc_info=True)
            raise

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
