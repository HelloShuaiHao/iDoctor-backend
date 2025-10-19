"""共享配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """通用配置"""

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/idoctor_commercial"

    # JWT
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 支付宝
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY_PATH: str = "./keys/alipay_private_key.pem"
    ALIPAY_PUBLIC_KEY_PATH: str = "./keys/alipay_public_key.pem"
    ALIPAY_GATEWAY: str = "https://openapi.alipaydev.com/gateway.do"
    ALIPAY_RETURN_URL: str = ""
    ALIPAY_NOTIFY_URL: str = ""

    # 微信支付
    WECHAT_APP_ID: str = ""
    WECHAT_MCH_ID: str = ""
    WECHAT_API_KEY: str = ""
    WECHAT_CERT_PATH: str = "./keys/apiclient_cert.pem"
    WECHAT_KEY_PATH: str = "./keys/apiclient_key.pem"
    WECHAT_NOTIFY_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USE_SSL: bool = False  # QQ邮箱使用465端口时需要设置为True
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "iDoctor"
    EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES: int = 10

    # 服务端口
    AUTH_SERVICE_PORT: int = 9001
    PAYMENT_SERVICE_PORT: int = 9002
    GATEWAY_PORT: int = 9000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:7500",
        "http://localhost:4200",
        "http://ai.bygpu.com:55303",
        "http://ai.bygpu.com:55304",  # 主前端（端口7500）
        "http://ai.bygpu.com:55305",  # commercial前端（端口3000）
        "https://ai.bygpu.com:55304",
        "https://ai.bygpu.com:55305"
    ]

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    # 环境
    ENVIRONMENT: str = "development"

    # 开关
    ENABLE_AUTH: bool = False
    ENABLE_QUOTA: bool = False

    model_config = SettingsConfigDict(
        # 从 commercial/.env 文件读取配置
        env_file="../.env",
        case_sensitive=True,
        env_parse_none_str='null',
        extra='ignore'  # 忽略 .env 中未定义的额外字段
    )


settings = Settings()
