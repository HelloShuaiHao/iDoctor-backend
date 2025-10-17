"""用户管理 API"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from commercial.shared.database import get_db
from commercial.shared.exceptions import ResourceNotFoundError, ValidationError
from ..models.user import User
from ..schemas.user import UserResponse, UserUpdate
from ..core.dependencies import get_current_active_user, get_current_superuser
from ..core.security import get_password_hash

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户信息"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户信息"""
    # 检查邮箱是否已被其他用户使用
    if user_update.email and user_update.email != current_user.email:
        stmt = select(User).where(User.email == user_update.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError("邮箱已被使用")
        current_user.email = user_update.email

    # 检查用户名是否已被其他用户使用
    if user_update.username and user_update.username != current_user.username:
        stmt = select(User).where(User.username == user_update.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError("用户名已被使用")
        current_user.username = user_update.username

    # 更新密码
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser)  # 只有管理员可以查看其他用户
):
    """根据ID获取用户信息（仅管理员）"""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError("用户不存在")

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """删除用户（仅管理员）"""
    if user_id == current_user.id:
        raise ValidationError("不能删除自己的账号")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError("用户不存在")

    await db.delete(user)
    await db.commit()
