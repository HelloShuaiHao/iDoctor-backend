"""自定义异常"""
from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """认证失败"""
    def __init__(self, detail: str = "认证失败"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionDeniedError(HTTPException):
    """权限不足"""
    def __init__(self, detail: str = "权限不足"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ResourceNotFoundError(HTTPException):
    """资源不存在"""
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class QuotaExceededError(HTTPException):
    """配额超限"""
    def __init__(self, detail: str = "配额已用完，请升级订阅"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


class PaymentError(HTTPException):
    """支付错误"""
    def __init__(self, detail: str = "支付失败"):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail
        )


class ValidationError(HTTPException):
    """参数验证错误"""
    def __init__(self, detail: str = "参数验证失败"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class NotFoundError(HTTPException):
    """资源未找到"""
    def __init__(self, detail: str = "资源未找到"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
