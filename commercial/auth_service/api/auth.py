"""认证 API：注册、登录、刷新token"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, text
from commercial.shared.database import get_db
from commercial.shared.exceptions import AuthenticationError, ValidationError
from commercial.shared.config import settings
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, UserResponse
from ..schemas.token import Token
from ..schemas.verification import SendVerificationCodeRequest, VerifyEmailRequest, VerificationResponse
from ..core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from ..core.email import (
    send_verification_email,
    generate_verification_code,
    verification_store
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def assign_default_quotas(db: AsyncSession, user_id):
    """为新用户分配默认配额"""
    # 获取所有激活的配额类型
    query = text("""
        SELECT id, type_key, default_limit 
        FROM quota_types 
        WHERE is_active = true
    """)
    result = await db.execute(query)
    quota_types = result.fetchall()
    
    # 为每个配额类型创建配额限制
    for quota_type_id, type_key, default_limit in quota_types:
        insert_query = text("""
            INSERT INTO quota_limits (user_id, quota_type_id, limit_amount, used_amount)
            VALUES (:user_id, :quota_type_id, :limit_amount, 0)
            ON CONFLICT (user_id, quota_type_id) DO NOTHING
        """)
        await db.execute(
            insert_query,
            {
                "user_id": str(user_id),
                "quota_type_id": quota_type_id,
                "limit_amount": default_limit
            }
        )
    
    await db.commit()
    logger.info(f"为用户 {user_id} 分配了 {len(quota_types)} 种配额")


@router.post("/send-verification-code", response_model=VerificationResponse)
async def send_verification_code(
    request: SendVerificationCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """发送邮箱验证码"""
    # 检查邮箱是否已被注册
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValidationError("该邮箱已被注册")

    # 生成验证码
    code = generate_verification_code()

    # 存储验证码
    verification_store.set(
        request.email,
        code,
        settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES
    )

    # 发送邮件
    success = await send_verification_email(request.email, code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证码失败，请稍后重试"
        )

    return VerificationResponse(
        message=f"验证码已发送至 {request.email}，有效期 {settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} 分钟",
        success=True
    )


@router.post("/verify-email", response_model=VerificationResponse)
async def verify_email_code(request: VerifyEmailRequest):
    """验证邮箱验证码（可选，注册时也会验证）"""
    is_valid = verification_store.verify(request.email, request.code)

    if not is_valid:
        raise ValidationError("验证码无效或已过期")

    # 验证成功后重新存储，以便注册时使用（延长有效期）
    verification_store.set(
        request.email,
        request.code,
        settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES
    )

    return VerificationResponse(
        message="邮箱验证成功",
        success=True
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 1. 验证邮箱验证码
    is_valid = verification_store.verify(user_data.email, user_data.verification_code)
    if not is_valid:
        raise ValidationError("邮箱验证码无效或已过期，请重新获取")

    # 2. 检查邮箱是否已存在
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValidationError("邮箱已被注册")

    # 3. 检查用户名是否已存在
    stmt = select(User).where(User.username == user_data.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ValidationError("用户名已被使用")

    # 4. 创建用户
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password)
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 自动为新用户分配默认配额
    try:
        await assign_default_quotas(db, user.id)
        logger.info(f"✅ 为用户 {user.email} 分配了默认配额")
    except Exception as e:
        logger.error(f"⚠️  为用户 {user.email} 分配配额失败: {e}")

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
