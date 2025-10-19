"""FastAPI JWT认证中间件

集成到主应用后，自动验证所有请求的JWT token
"""
import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from auth_service.core.jwt import decode_access_token
from shared.config import settings

logger = logging.getLogger(__name__)

# 无需认证的路径白名单
EXEMPT_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    # 认证服务本身的路径（如果在同一应用）
    "/auth/register",
    "/auth/login",
    "/auth/refresh"
}

# 支持路径前缀匹配
EXEMPT_PREFIX = [
    "/docs",
    "/redoc",
    "/auth/"
]


async def auth_middleware(request: Request, call_next):
    """JWT认证中间件

    功能:
    1. 检查请求路径是否需要认证
    2. 提取并验证JWT token
    3. 将用户信息注入request.state供后续使用
    4. 返回401错误（未认证）或继续处理请求
    """
    path = request.url.path
    method = request.method
    logger.debug(f"Auth middleware: path={path}, method={method}")

    # 跳过CORS预检请求 (OPTIONS)
    if method == "OPTIONS":
        return await call_next(request)

    # 跳过白名单路径
    if path in EXEMPT_PATHS:
        return await call_next(request)

    # 跳过匹配前缀的路径
    for prefix in EXEMPT_PREFIX:
        if path.startswith(prefix):
            return await call_next(request)

    # 提取 Authorization header 或 URL 参数中的 token
    auth_header = request.headers.get("Authorization")

    # 如果没有 Authorization header，尝试从 URL 参数获取 token（用于图片等无法设置 header 的请求）
    if not auth_header:
        token_param = request.query_params.get("token")
        if token_param:
            auth_header = f"Bearer {token_param}"

    if not auth_header:
        logger.warning(f"Unauthorized request to {path}: No Authorization header")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "未提供认证凭证",
                "message": "请在Header中提供 Authorization: Bearer <token>"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not auth_header.startswith("Bearer "):
        logger.warning(f"Unauthorized request to {path}: Invalid Authorization header format")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "认证凭证格式错误",
                "message": "Authorization header必须以 'Bearer ' 开头"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header.split(" ", 1)[1]

    try:
        # 验证 JWT token
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        user_email = payload.get("email")

        if not user_id:
            raise ValueError("Token中缺少user_id (sub)")

        # 将用户信息注入request.state（供后续处理使用）
        request.state.user_id = user_id
        request.state.user_email = user_email
        request.state.is_superuser = payload.get("is_superuser", False)

        logger.info(f"Authenticated user {user_email} ({user_id}) accessing {path}")
        logger.debug(f"Set request.state.user_id = {user_id}")

    except ValueError as e:
        logger.warning(f"Invalid token for {path}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "无效的认证令牌",
                "message": str(e)
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Authentication error for {path}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "认证失败",
                "message": "Token验证失败，请重新登录"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 继续处理请求
    response = await call_next(request)
    return response


def add_exempt_path(path: str):
    """动态添加免认证路径"""
    EXEMPT_PATHS.add(path)


def add_exempt_prefix(prefix: str):
    """动态添加免认证路径前缀"""
    EXEMPT_PREFIX.append(prefix)
