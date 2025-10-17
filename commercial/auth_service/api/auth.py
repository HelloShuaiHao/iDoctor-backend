"""认证 API：注册、登录、刷新token"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from commercial.shared.database import get_db
from commercial.shared.exceptions import AuthenticationError, ValidationError
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, UserResponse
from ..schemas.token import Token
from ..core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查邮箱是否已存在
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValidationError("邮箱已被注册")

    # 检查用户名是否已存在
    stmt = select(User).where(User.username == user_data.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValidationError("用户名已被使用")

    # 创建用户
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password)
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    # 查询用户（支持邮箱或用户名登录）
    stmt = select(User).where(
        or_(
            User.email == login_data.username_or_email,
            User.username == login_data.username_or_email
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise AuthenticationError("用户名或密码错误")

    if not user.is_active:
        raise AuthenticationError("账号已被禁用")

    # 生成 token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """刷新访问令牌"""
    payload = verify_token(refresh_token, token_type="refresh")

    if not payload:
        raise AuthenticationError("无效的刷新令牌")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("无效的令牌数据")

    # 验证用户是否存在且活跃
    from uuid import UUID
    stmt = select(User).where(User.id == UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError("用户不存在或已被禁用")

    # 生成新的 token
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout():
    """登出（客户端需删除本地token）"""
    # 在无状态JWT系统中，登出主要在客户端进行
    # 如果需要服务端撤销，可以使用Redis维护黑名单
    return {"message": "登出成功"}
