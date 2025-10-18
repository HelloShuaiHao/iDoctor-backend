"""邮箱验证 Pydantic 模型"""
from pydantic import BaseModel, EmailStr, Field


class SendVerificationCodeRequest(BaseModel):
    """发送验证码请求"""
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    """验证邮箱请求"""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="6位数字验证码")


class VerificationResponse(BaseModel):
    """验证响应"""
    message: str
    success: bool
