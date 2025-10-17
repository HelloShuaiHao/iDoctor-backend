"""订阅管理 API"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from commercial.shared.database import get_db
from commercial.shared.exceptions import ResourceNotFoundError, ValidationError
from commercial.auth_service.core.dependencies import get_current_user
from commercial.auth_service.models.user import User
from ..models.plan import SubscriptionPlan
from ..models.subscription import UserSubscription
from ..schemas.subscription import UserSubscriptionResponse, SubscriptionCreateRequest
from ..core.quota import get_quota_status

router = APIRouter()


@router.get("/current", response_model=UserSubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的订阅"""
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).order_by(UserSubscription.created_at.desc())

    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise ResourceNotFoundError("您还没有订阅")

    return subscription


@router.get("/history", response_model=List[UserSubscriptionResponse])
async def get_subscription_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取订阅历史"""
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == current_user.id
    ).order_by(UserSubscription.created_at.desc())

    result = await db.execute(stmt)
    subscriptions = result.scalars().all()
    return subscriptions


@router.post("/subscribe")
async def create_subscription(
    subscription_req: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建订阅（实际应在支付成功后调用）

    注意：这个接口通常在支付成功的webhook中调用，不应直接暴露给用户
    """
    # 检查计划是否存在
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == subscription_req.plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if not plan or not plan.is_active:
        raise ResourceNotFoundError("订阅计划不存在或已停用")

    # 检查是否已有活跃订阅
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active",
        UserSubscription.current_period_end > datetime.utcnow()
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise ValidationError("您已有活跃订阅，请先取消或等待过期")

    # 计算订阅周期
    period_start = datetime.utcnow()
    if plan.billing_cycle == "monthly":
        period_end = period_start + timedelta(days=30)
    elif plan.billing_cycle == "yearly":
        period_end = period_start + timedelta(days=365)
    else:  # lifetime
        period_end = period_start + timedelta(days=36500)  # 100年

    # 创建订阅
    subscription = UserSubscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status="active",
        current_period_start=period_start,
        current_period_end=period_end,
        quota_used=0,
        quota_limit=plan.quota_limit,
        auto_renew=True
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return {
        "message": "订阅创建成功",
        "subscription_id": str(subscription.id),
        "period_start": subscription.current_period_start,
        "period_end": subscription.current_period_end
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取消订阅（立即生效）"""
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).order_by(UserSubscription.created_at.desc())

    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise ResourceNotFoundError("没有找到活跃订阅")

    subscription.status = "cancelled"
    subscription.auto_renew = False

    await db.commit()

    return {"message": "订阅已取消"}


@router.get("/quota")
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取配额使用情况"""
    return await get_quota_status(db, current_user.id)
