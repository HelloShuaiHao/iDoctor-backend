"""支付服务依赖注入"""
from functools import wraps
from typing import Callable
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from commercial.shared.database import get_db
from commercial.auth_service.core.dependencies import get_current_user
from commercial.auth_service.models.user import User
from .quota import consume_quota as _consume_quota


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
            # 从kwargs中获取current_user和db
            current_user: User = kwargs.get("current_user")
            db: AsyncSession = kwargs.get("db")

            if not current_user:
                raise ValueError("require_quota装饰器需要current_user参数（使用Depends(get_current_user)）")
            if not db:
                raise ValueError("require_quota装饰器需要db参数（使用Depends(get_db)）")

            # 消耗配额
            await _consume_quota(
                db=db,
                user_id=current_user.id,
                resource_type=resource_type,
                cost=cost
            )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator
