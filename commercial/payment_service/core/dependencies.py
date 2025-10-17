"""支付服务依赖注入"""
from functools import wraps
from typing import Callable, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from commercial.shared.database import get_db
from commercial.shared.config import settings
from .quota import consume_quota as _consume_quota

# JWT认证
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """从JWT token获取当前用户ID"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_current_superuser_id(
    user_id: str = Depends(get_current_user_id)
) -> str:
    """获取超级用户ID，通过调用认证服务验证权限"""
    import httpx
    
    try:
        # 调用认证服务获取用户信息
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://idoctor_auth_service:9001/users/{user_id}",
                headers={"Authorization": f"Bearer {jwt.encode({'sub': user_id}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get("is_superuser", False):
                    return user_id
                else:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="仅管理员可以访问此接口"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无法验证用户身份"
                )
    except httpx.RequestError:
        # 如果调用认证服务失败，在开发环境中允许通过
        if settings.ENVIRONMENT == "development":
            return user_id
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务不可用"
            )


async def get_optional_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[str]:
    """可选的用户认证"""
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None


def require_quota(resource_type: str, cost: int = 1):
    """配额检查装饰器

    使用示例:
    ```python
    @app.post("/process")
    @require_quota(resource_type="dicom_processing", cost=1)
    async def process(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # 如果到这里，说明配额检查已通过
        pass
    ```

    Args:
        resource_type: 资源类型
        cost: 消耗配额数
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取user_id和db
            user_id: str = kwargs.get("user_id") or kwargs.get("current_user_id")
            db: AsyncSession = kwargs.get("db")

            if not user_id:
                raise ValueError("require_quota装饰器需要user_id参数")
            if not db:
                raise ValueError("require_quota装饰器需要db参数（使用Depends(get_db)）")

            # 消耗配额
            await _consume_quota(
                db=db,
                user_id=user_id,
                resource_type=resource_type,
                cost=cost
            )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator
