"""配额管理"""
from datetime import datetime
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from commercial.shared.exceptions import QuotaExceededError, ResourceNotFoundError
from ..models.subscription import UserSubscription
from ..models.usage_log import UsageLog


async def get_active_subscription(
    db: AsyncSession,
    user_id: UUID
) -> Optional[UserSubscription]:
    """获取用户当前有效订阅"""
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == user_id,
        UserSubscription.status == "active",
        UserSubscription.current_period_end > datetime.utcnow()
    ).order_by(UserSubscription.current_period_start.desc())

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_quota(
    db: AsyncSession,
    user_id: UUID,
    resource_type: str,
    cost: int = 1
) -> UserSubscription:
    """检查配额是否充足（不扣减）

    Args:
        db: 数据库会话
        user_id: 用户ID
        resource_type: 资源类型
        cost: 消耗配额数

    Returns:
        UserSubscription: 有效订阅

    Raises:
        ResourceNotFoundError: 没有有效订阅
        QuotaExceededError: 配额不足
    """
    subscription = await get_active_subscription(db, user_id)

    if not subscription:
        raise ResourceNotFoundError("您还没有订阅，请先购买订阅计划")

    # 检查配额
    if subscription.quota_used + cost > subscription.quota_limit:
        raise QuotaExceededError(
            f"配额不足。已用: {subscription.quota_used}/{subscription.quota_limit}"
        )

    return subscription


async def consume_quota(
    db: AsyncSession,
    user_id: UUID,
    resource_type: str,
    cost: int = 1,
    resource_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> UsageLog:
    """消耗配额并记录日志

    Args:
        db: 数据库会话
        user_id: 用户ID
        resource_type: 资源类型（例如: "dicom_processing"）
        cost: 消耗配额数
        resource_id: 资源ID（例如: 任务ID）
        metadata: 额外元数据

    Returns:
        UsageLog: 使用记录

    Raises:
        ResourceNotFoundError: 没有有效订阅
        QuotaExceededError: 配额不足
    """
    # 检查并获取订阅
    subscription = await check_quota(db, user_id, resource_type, cost)

    # 扣减配额
    subscription.quota_used += cost

    # 记录使用日志
    usage_log = UsageLog(
        user_id=user_id,
        subscription_id=subscription.id,
        resource_type=resource_type,
        resource_id=resource_id,
        quota_cost=cost,
        metadata=metadata
    )

    db.add(usage_log)
    await db.commit()
    await db.refresh(usage_log)

    return usage_log


async def get_quota_status(
    db: AsyncSession,
    user_id: UUID
) -> dict:
    """获取配额状态

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        dict: 配额状态信息
    """
    subscription = await get_active_subscription(db, user_id)

    if not subscription:
        return {
            "has_subscription": False,
            "quota_used": 0,
            "quota_limit": 0,
            "quota_remaining": 0,
            "usage_percentage": 0
        }

    quota_remaining = subscription.quota_limit - subscription.quota_used
    usage_percentage = (subscription.quota_used / subscription.quota_limit * 100) if subscription.quota_limit > 0 else 0

    return {
        "has_subscription": True,
        "subscription_id": str(subscription.id),
        "plan_id": str(subscription.plan_id),
        "status": subscription.status,
        "quota_used": subscription.quota_used,
        "quota_limit": subscription.quota_limit,
        "quota_remaining": quota_remaining,
        "usage_percentage": round(usage_percentage, 2),
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end
    }
