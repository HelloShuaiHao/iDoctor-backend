"""支付 API"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from uuid import UUID, uuid4
from decimal import Decimal

from commercial.shared.database import get_db
from commercial.shared.exceptions import ValidationError, ResourceNotFoundError
from commercial.shared.config import settings
from ..models.transaction import PaymentTransaction
from ..models.subscription import UserSubscription
from ..models.plan import SubscriptionPlan
from ..schemas.payment import PaymentCreateRequest, PaymentResponse, PaymentHistoryItem
from ..providers.alipay import AlipayProvider
from ..providers.wechat import WechatProvider
from ..providers.base import PaymentProvider
from ..core.dependencies import get_optional_current_user_id, get_current_user_id

router = APIRouter()

# 支付提供商配置
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


def get_payment_provider(method: str) -> PaymentProvider:
    """获取支付提供商"""
    if method not in PAYMENT_PROVIDERS:
        raise ValidationError(f"不支持的支付方式: {method}")
    return PAYMENT_PROVIDERS[method]


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_request: PaymentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[str] = Depends(get_optional_current_user_id)
):
    """创建支付"""
    # 确定用户ID
    user_id = None
    
    # 如果提供了订阅ID，验证并获取用户ID
    if payment_request.subscription_id:
        stmt = select(UserSubscription).where(UserSubscription.id == payment_request.subscription_id)
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ResourceNotFoundError("订阅不存在")
        user_id = subscription.user_id
    elif current_user_id:
        # 如果没有订阅ID但有认证用户，使用认证用户ID
        try:
            user_id = UUID(current_user_id)
        except (ValueError, TypeError):
            user_id = None
    # 如果既没有订阅ID也没有认证，允许匿名支付（user_id = None）

    # 创建支付交易记录
    transaction = PaymentTransaction(
        id=uuid4(),
        user_id=user_id,
        subscription_id=payment_request.subscription_id,
        amount=payment_request.amount,
        currency=payment_request.currency,
        payment_method=payment_request.payment_method,
        status="pending",
        extra_data=payment_request.extra_data or {}
    )
    
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    # 获取支付提供商
    provider = get_payment_provider(payment_request.payment_method)
    
    try:
        # 创建支付订单
        payment_result = await provider.create_payment(
            order_id=str(transaction.id),
            amount=payment_request.amount,
            currency=payment_request.currency,
            subject=f"iDoctor 订阅支付 - {transaction.id}",
            return_url=payment_request.return_url
        )
        
        # 更新交易记录
        transaction.payment_provider_id = payment_result.get("provider_order_id")
        transaction.extra_data = {
            **transaction.extra_data,
            "payment_result": payment_result
        }
        await db.commit()
        
        # 返回支付响应
        return PaymentResponse(
            id=transaction.id,
            amount=transaction.amount,
            currency=transaction.currency,
            payment_method=transaction.payment_method,
            status=transaction.status,
            payment_url=payment_result.get("payment_url"),
            qr_code=payment_result.get("qr_code"),
            created_at=transaction.created_at
        )
        
    except Exception as e:
        # 支付创建失败，更新状态
        transaction.status = "failed"
        transaction.extra_data = {
            **transaction.extra_data,
            "error": str(e)
        }
        await db.commit()
        raise HTTPException(status_code=400, detail=f"支付创建失败: {str(e)}")


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    poll: bool = False
):
    """查询支付状态

    Args:
        payment_id: 支付交易ID
        poll: 是否主动查询支付平台最新状态（默认False，从数据库读取）
    """
    stmt = select(PaymentTransaction).where(PaymentTransaction.id == payment_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise ResourceNotFoundError("支付记录不存在")

    # 如果启用轮询，且支付仍在处理中，主动查询最新状态
    if poll and transaction.status == "pending" and transaction.payment_provider_id:
        provider = get_payment_provider(transaction.payment_method)
        try:
            # 查询支付平台的最新状态
            latest_status = await provider.verify_payment(str(transaction.id))

            # 状态有变化时更新数据库
            if latest_status.value != transaction.status:
                old_status = transaction.status
                transaction.status = latest_status.value
                transaction.extra_data = {
                    **transaction.extra_data,
                    "last_poll_time": str(transaction.created_at)
                }

                # 如果支付成功，激活订阅
                if latest_status.value == "completed" and transaction.subscription_id:
                    from ..api.webhooks import activate_subscription
                    await activate_subscription(transaction.subscription_id, db)

                await db.commit()

                # 记录状态变更
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Payment {payment_id} status updated via polling: {old_status} -> {latest_status.value}")
        except Exception as e:
            # 查询失败不影响返回现有状态
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to poll payment status for {payment_id}: {str(e)}")

    return PaymentResponse(
        id=transaction.id,
        amount=transaction.amount,
        currency=transaction.currency,
        payment_method=transaction.payment_method,
        status=transaction.status,
        payment_url=transaction.extra_data.get("payment_result", {}).get("payment_url"),
        qr_code=transaction.extra_data.get("payment_result", {}).get("qr_code"),
        created_at=transaction.created_at
    )


@router.get("/", response_model=List[PaymentHistoryItem])
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    current_user_id: Optional[str] = Depends(get_optional_current_user_id),
    status_filter: Optional[str] = None,
    limit: int = 50
):
    """查询支付历史

    Args:
        status_filter: 按状态筛选（可选：pending/completed/failed/refunded）
        limit: 返回记录数量限制（默认50条）

    Returns:
        支付历史记录列表
    """
    # 构建基础查询
    stmt = select(
        PaymentTransaction,
        UserSubscription,
        SubscriptionPlan
    ).outerjoin(
        UserSubscription, PaymentTransaction.subscription_id == UserSubscription.id
    ).outerjoin(
        SubscriptionPlan, UserSubscription.plan_id == SubscriptionPlan.id
    )

    # 如果有认证用户，只查询该用户的记录
    if current_user_id:
        try:
            user_uuid = UUID(current_user_id)
            stmt = stmt.where(PaymentTransaction.user_id == user_uuid)
        except (ValueError, TypeError):
            pass

    # 按状态筛选
    if status_filter:
        stmt = stmt.where(PaymentTransaction.status == status_filter)

    # 排序和限制
    stmt = stmt.order_by(desc(PaymentTransaction.created_at)).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    # 构建返回数据
    history_items = []
    for transaction, subscription, plan in rows:
        # 生成计划名称
        plan_name = None
        description = None

        if plan:
            # 将 billing_cycle 转换为中文
            cycle_map = {
                "monthly": "月付",
                "yearly": "年付",
                "lifetime": "终身"
            }
            cycle_text = cycle_map.get(plan.billing_cycle, plan.billing_cycle)
            plan_name = f"{plan.name} - {cycle_text}"
            description = f"订阅{plan.name}套餐"

            # 如果已退款，添加标记
            if transaction.status == "refunded":
                description += "（已退款）"
        else:
            description = "订阅支付"

        history_items.append(PaymentHistoryItem(
            id=transaction.id,
            order_id=str(transaction.id),
            amount=transaction.amount,
            currency=transaction.currency,
            payment_method=transaction.payment_method,
            status=transaction.status,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
            plan_name=plan_name,
            description=description
        ))

    return history_items


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: UUID,
    refund_amount: Decimal,
    reason: str = "用户申请退款",
    db: AsyncSession = Depends(get_db)
):
    """退款"""
    stmt = select(PaymentTransaction).where(PaymentTransaction.id == payment_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise ResourceNotFoundError("支付记录不存在")

    if transaction.status != "completed":
        raise ValidationError("只能对已完成的支付进行退款")

    if refund_amount > transaction.amount:
        raise ValidationError("退款金额不能超过支付金额")

    provider = get_payment_provider(transaction.payment_method)

    try:
        refund_result = await provider.refund(
            transaction_id=transaction.payment_provider_id,
            amount=refund_amount,
            reason=reason
        )

        if refund_result.success:
            transaction.status = "refunded"
            transaction.extra_data = {
                **transaction.extra_data,
                "refund": {
                    "refund_id": refund_result.refund_id,
                    "amount": str(refund_amount),
                    "reason": reason,
                    "message": refund_result.message
                }
            }
            await db.commit()

            return {"success": True, "message": "退款成功", "refund_id": refund_result.refund_id}
        else:
            return {"success": False, "message": refund_result.message}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"退款失败: {str(e)}")