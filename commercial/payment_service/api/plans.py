"""订阅计划 API"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from commercial.shared.database import get_db
from commercial.shared.exceptions import ResourceNotFoundError
from commercial.auth_service.core.dependencies import get_current_superuser
from commercial.auth_service.models.user import User
from ..models.plan import SubscriptionPlan
from ..schemas.plan import SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate

router = APIRouter()


@router.get("/", response_model=List[SubscriptionPlanResponse])
async def list_plans(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """列出所有订阅计划（公开接口）"""
    stmt = select(SubscriptionPlan)
    if active_only:
        stmt = stmt.where(SubscriptionPlan.is_active == True)
    stmt = stmt.order_by(SubscriptionPlan.price)

    result = await db.execute(stmt)
    plans = result.scalars().all()
    return plans


@router.get("/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取订阅计划详情"""
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if not plan:
        raise ResourceNotFoundError("订阅计划不存在")

    return plan


@router.post("/", response_model=SubscriptionPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser)  # 仅管理员
):
    """创建订阅计划（仅管理员）"""
    plan = SubscriptionPlan(**plan_data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.put("/{plan_id}", response_model=SubscriptionPlanResponse)
async def update_plan(
    plan_id: UUID,
    plan_update: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser)
):
    """更新订阅计划（仅管理员）"""
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if not plan:
        raise ResourceNotFoundError("订阅计划不存在")

    # 更新字段
    update_data = plan_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser)
):
    """删除订阅计划（仅管理员）"""
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if not plan:
        raise ResourceNotFoundError("订阅计划不存在")

    # 软删除（设为不活跃）
    plan.is_active = False
    await db.commit()
