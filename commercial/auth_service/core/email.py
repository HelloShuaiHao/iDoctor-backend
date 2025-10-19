"""邮件发送服务"""
import logging
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional
from commercial.shared.config import settings

logger = logging.getLogger(__name__)


class VerificationCodeStore:
    """验证码存储（内存实现，生产环境建议使用Redis）"""

    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def set(self, email: str, code: str, expire_minutes: int = 10):
        """存储验证码"""
        self._store[email] = {
            "code": code,
            "expires_at": datetime.utcnow() + timedelta(minutes=expire_minutes)
        }
        logger.info(f"验证码已存储: {email} -> {code} (有效期{expire_minutes}分钟)")

    def get(self, email: str) -> Optional[str]:
        """获取验证码"""
        data = self._store.get(email)
        if not data:
            return None

        # 检查是否过期
        if datetime.utcnow() > data["expires_at"]:
            self.delete(email)
            return None

        return data["code"]

    def delete(self, email: str):
        """删除验证码"""
        if email in self._store:
            del self._store[email]
            logger.info(f"验证码已删除: {email}")

    def verify(self, email: str, code: str) -> bool:
        """验证验证码"""
        stored_code = self.get(email)
        if not stored_code:
            logger.warning(f"验证失败: 验证码不存在或已过期 ({email})")
            return False

        if stored_code != code:
            logger.warning(f"验证失败: 验证码不匹配 ({email})")
            return False

        # 验证成功后删除验证码
        self.delete(email)
        logger.info(f"验证成功: {email}")
        return True


# 全局验证码存储实例
verification_store = VerificationCodeStore()


def generate_verification_code(length: int = 6) -> str:
    """生成随机验证码"""
    return ''.join(random.choices(string.digits, k=length))


async def send_verification_email(email: str, code: str) -> bool:
    """发送验证码邮件"""

    # 如果没有配置SMTP，则在开发环境下只打印验证码
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f"⚠️  SMTP未配置，开发模式下直接显示验证码")
        logger.info(f"📧 验证码邮件 -> {email}: {code}")
        print(f"\n{'='*60}")
        print(f"📧 邮箱验证码（开发模式）")
        print(f"收件人: {email}")
        print(f"验证码: {code}")
        print(f"有效期: {settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} 分钟")
        print(f"{'='*60}\n")
        return True

    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'{settings.SMTP_FROM_NAME} - 邮箱验证码'
        msg['From'] = f'{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>'
        msg['To'] = email

        # 邮件内容（纯文本版本）
        text_content = f"""
您好，

您的 {settings.SMTP_FROM_NAME} 邮箱验证码是：

{code}

此验证码将在 {settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} 分钟后过期。

如果您没有请求此验证码，请忽略此邮件。

---
{settings.SMTP_FROM_NAME} 团队
        """

        # 邮件内容（HTML版本）
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .code-box {{ background: white; border: 2px dashed #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
        .code {{ font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>邮箱验证</h1>
        </div>
        <div class="content">
            <p>您好，</p>
            <p>您正在注册 <strong>{settings.SMTP_FROM_NAME}</strong> 账户，请使用以下验证码完成注册：</p>
            <div class="code-box">
                <div class="code">{code}</div>
            </div>
            <p>此验证码将在 <strong>{settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} 分钟</strong>后过期。</p>
            <p>如果您没有请求此验证码，请忽略此邮件。</p>
        </div>
        <div class="footer">
            <p>© 2025 {settings.SMTP_FROM_NAME}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        # 添加纯文本和HTML版本
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)

        # 发送邮件
        if settings.SMTP_USE_SSL:
            # 使用 SSL (通常用于465端口，如QQ邮箱)
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            # 使用 STARTTLS (通常用于587端口，如Gmail)
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

        logger.info(f"✅ 验证码邮件已发送: {email}")
        return True

    except Exception as e:
        logger.error(f"❌ 发送验证码邮件失败: {email}, 错误: {e}")
        # 在开发环境下，即使SMTP失败也显示验证码
        if settings.ENVIRONMENT == "development":
            logger.info(f"📧 验证码邮件发送失败，开发模式下显示验证码: {email} -> {code}")
            print(f"\n{'='*60}")
            print(f"📧 邮箱验证码（SMTP发送失败，显示备用）")
            print(f"收件人: {email}")
            print(f"验证码: {code}")
            print(f"有效期: {settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES} 分钟")
            print(f"{'='*60}\n")
            return True
        return False
