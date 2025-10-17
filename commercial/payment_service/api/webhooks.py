"""支付回调处理 API"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from commercial.shared.database import get_db
from ..models.transaction import PaymentTransaction
from ..models.subscription import UserSubscription
from ..providers.alipay import AlipayProvider
from ..providers.wechat import WechatProvider
from ..providers.base import PaymentProvider
from commercial.shared.config import settings

router = APIRouter()

# 配置日志
logger = logging.getLogger(__name__)

# 支付提供商配置（与payments.py保持一致）
PAYMENT_PROVIDERS = {
    "alipay": AlipayProvider({
        "app_id": settings.ALIPAY_APP_ID,
        "private_key_path": settings.ALIPAY_PRIVATE_KEY_PATH,
        "public_key_path": settings.ALIPAY_PUBLIC_KEY_PATH,
        "gateway": settings.ALIPAY_GATEWAY,
        "notify_url": settings.ALIPAY_NOTIFY_URL,
        "sandbox": settings.ENVIRONMENT == "development"
    }),
    "wechat": WechatProvider({
        "app_id": settings.WECHAT_APP_ID,
        "mch_id": settings.WECHAT_MCH_ID,
        "api_key": settings.WECHAT_API_KEY,
        "cert_path": settings.WECHAT_CERT_PATH,
        "key_path": settings.WECHAT_KEY_PATH,
        "notify_url": settings.WECHAT_NOTIFY_URL,
        "sandbox": settings.ENVIRONMENT == "development"
    })
}


async def update_transaction_status(
    transaction_id: UUID,
    status: str,
    provider_data: Dict[str, Any],
    db: AsyncSession
) -> None:
    """更新交易状态"""
    stmt = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        logger.error(f"Transaction not found: {transaction_id}")
        return
    
    # 更新交易状态
    old_status = transaction.status
    transaction.status = status
    transaction.extra_data = {
        **transaction.extra_data,
        "webhook_data": provider_data
    }
    
    logger.info(f"Transaction {transaction_id} status updated: {old_status} -> {status}")
    
    # 如果支付成功，激活相关订阅
    if status == "completed" and transaction.subscription_id:
        await activate_subscription(transaction.subscription_id, db)
    
    await db.commit()


async def activate_subscription(subscription_id: UUID, db: AsyncSession) -> None:
    """激活订阅"""
    stmt = select(UserSubscription).where(UserSubscription.id == subscription_id)
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()
    
    if subscription and subscription.status != "active":
        subscription.status = "active"
        logger.info(f"Subscription {subscription_id} activated")
        await db.commit()


@router.post("/alipay")
async def handle_alipay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """处理支付宝回调"""
    try:
        # 获取请求数据
        if request.headers.get("content-type") == "application/json":
            request_data = await request.json()
        else:
            # 支付宝通常使用 form 数据
            form_data = await request.form()
            request_data = dict(form_data)
        
        logger.info(f"Received Alipay webhook: {request_data}")
        
        provider = PAYMENT_PROVIDERS["alipay"]
        
        # 验证签名
        if not await provider.verify_webhook(request_data):
            logger.warning("Alipay webhook signature verification failed")
            raise HTTPException(status_code=400, detail="签名验证失败")
        
        # 处理回调
        webhook_result = await provider.handle_webhook(request_data)
        
        # 更新交易状态
        if webhook_result and webhook_result.get("order_id"):
            try:
                transaction_id = UUID(webhook_result["order_id"])
                await update_transaction_status(
                    transaction_id,
                    webhook_result["status"],
                    request_data,
                    db
                )
            except ValueError:
                logger.error(f"Invalid transaction ID: {webhook_result['order_id']}")
        
        # 返回支付宝要求的响应格式
        return "success"
        
    except Exception as e:
        logger.error(f"Alipay webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="回调处理失败")


@router.post("/wechat")
async def handle_wechat_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """处理微信回调"""
    try:
        # 微信支付回调通常是 XML 格式
        body = await request.body()
        request_data = {"raw_body": body.decode("utf-8")}
        
        logger.info(f"Received WeChat webhook: {len(body)} bytes")
        
        provider = PAYMENT_PROVIDERS["wechat"]
        
        # 验证签名
        if not await provider.verify_webhook(request_data):
            logger.warning("WeChat webhook signature verification failed")
            return """<xml>
                <return_code><![CDATA[FAIL]]></return_code>
                <return_msg><![CDATA[签名验证失败]]></return_msg>
            </xml>"""
        
        # 处理回调
        webhook_result = await provider.handle_webhook(request_data)
        
        # 更新交易状态
        if webhook_result and webhook_result.get("order_id"):
            try:
                transaction_id = UUID(webhook_result["order_id"])
                await update_transaction_status(
                    transaction_id,
                    webhook_result["status"],
                    request_data,
                    db
                )
            except ValueError:
                logger.error(f"Invalid transaction ID: {webhook_result['order_id']}")
        
        # 返回微信要求的响应格式
        return """<xml>
            <return_code><![CDATA[SUCCESS]]></return_code>
            <return_msg><![CDATA[OK]]></return_msg>
        </xml>"""
        
    except Exception as e:
        logger.error(f"WeChat webhook processing error: {str(e)}")
        return """<xml>
            <return_code><![CDATA[FAIL]]></return_code>
            <return_msg><![CDATA[系统错误]]></return_msg>
        </xml>"""


@router.get("/test")
async def test_webhook():
    """测试回调接口连通性"""
    return {
        "message": "Webhook endpoints are working",
        "endpoints": {
            "alipay": "/webhooks/alipay",
            "wechat": "/webhooks/wechat"
        }
    }