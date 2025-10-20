"""创建管理员用户"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
# /app/scripts/create_admin.py -> /app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commercial.shared.database import AsyncSessionLocal
from commercial.auth_service.models.user import User
from commercial.auth_service.core.security import get_password_hash


async def create_admin(email: str, username: str, password: str):
    """创建管理员用户"""
    async with AsyncSessionLocal() as db:
        # 检查是否已存在
        from sqlalchemy import select
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"⚠️  用户已存在: {email}")
            return

        # 创建管理员
        admin = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True
        )

        db.add(admin)
        await db.commit()

        print(f"✅ 管理员用户创建成功！")
        print(f"   邮箱: {email}")
        print(f"   用户名: {username}")
        print(f"   密码: {password}")
        print(f"   ⚠️  请妥善保管密码！")


if __name__ == "__main__":
    import getpass

    print("🚀 创建管理员用户")
    print("-" * 50)

    email = input("邮箱: ").strip()
    username = input("用户名: ").strip()
    password = getpass.getpass("密码: ")
    confirm_password = getpass.getpass("确认密码: ")

    if password != confirm_password:
        print("❌ 两次密码不一致！")
        sys.exit(1)

    if len(password) < 8:
        print("❌ 密码至少8位！")
        sys.exit(1)

    asyncio.run(create_admin(email, username, password))
    print("✨ 完成！")
