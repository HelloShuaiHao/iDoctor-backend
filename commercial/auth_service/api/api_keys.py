"""API 密钥管理 API"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from commercial.shared.database import get_db
from commercial.shared.exceptions import ResourceNotFoundError
from ..models.user import User
from ..models.api_key import APIKey
from ..schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyWithSecret
from ..core.dependencies import get_current_active_user
from ..core.security import generate_api_key, get_key_prefix

router = APIRouter()


@router.post("/", response_model=APIKeyWithSecret, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """创建 API 密钥（完整密钥只返回一次）"""
    # 生成密钥
    full_key, key_hash = generate_api_key()
    key_prefix = get_key_prefix(full_key)

    # 创建记录
    api_key = APIKey(
        user_id=current_user.id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=api_key_data.name,
        expires_at=api_key_data.expires_at
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # 返回带完整密钥的响应（仅此一次）
    return APIKeyWithSecret(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        key=full_key  # 完整密钥
    )


@router.get("/", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """列出当前用户的所有 API 密钥"""
    stmt = select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
    result = await db.execute(stmt)
    api_keys = result.scalars().all()
    return api_keys


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """删除 API 密钥"""
    stmt = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise ResourceNotFoundError("API 密钥不存在")

    await db.delete(api_key)
    await db.commit()


@router.patch("/{key_id}/deactivate", response_model=APIKeyResponse)
async def deactivate_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """停用 API 密钥"""
    stmt = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise ResourceNotFoundError("API 密钥不存在")

    api_key.is_active = False
    await db.commit()
    await db.refresh(api_key)
    return api_key
