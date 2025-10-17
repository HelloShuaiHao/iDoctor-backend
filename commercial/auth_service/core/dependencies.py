"""FastAPI 依赖注入"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from commercial.shared.database import get_db
from commercial.shared.exceptions import AuthenticationError, PermissionDeniedError
from ..models.user import User
from ..models.api_key import APIKey
from .security import verify_token, verify_password

# HTTP Bearer token 认证
security = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """从 JWT Token 获取当前用户"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token, token_type="access")

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    # 查询用户
    stmt = select(User).where(User.id == UUID(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return None

    return user


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """从 API Key 获取当前用户"""
    if not x_api_key:
        return None

    # 查询 API Key（通过前缀快速定位）
    key_prefix = x_api_key[:15] + "..." if len(x_api_key) > 15 else x_api_key
    stmt = select(APIKey).where(APIKey.key_prefix == key_prefix, APIKey.is_active == True)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        # 尝试通过哈希匹配（性能较差，作为后备）
        stmt = select(APIKey).where(APIKey.is_active == True)
        result = await db.execute(stmt)
        all_keys = result.scalars().all()

        for key in all_keys:
            if verify_password(x_api_key, key.key_hash):
                api_key = key
                break

    if not api_key:
        return None

    # 检查过期
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        return None

    # 更新最后使用时间
    from datetime import datetime
    api_key.last_used_at = datetime.utcnow()
    await db.commit()

    # 查询用户
    stmt = select(User).where(User.id == api_key.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    user_from_token: Optional[User] = Depends(get_current_user_from_token),
    user_from_api_key: Optional[User] = Depends(get_current_user_from_api_key)
) -> User:
    """获取当前用户（支持 Token 和 API Key 两种方式）"""
    user = user_from_token or user_from_api_key

    if not user:
        raise AuthenticationError("未提供有效的认证凭据")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise AuthenticationError("用户账号已禁用")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前超级管理员"""
    if not current_user.is_superuser:
        raise PermissionDeniedError("需要管理员权限")
    return current_user
