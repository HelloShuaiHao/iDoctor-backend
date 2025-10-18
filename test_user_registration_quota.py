#!/usr/bin/env python3
"""
测试用户注册后是否自动分配配额
"""
import asyncio
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/idoctor_commercial"

async def test_user_quota_assignment():
    """测试用户配额分配"""
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        # 生成测试用户 email
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        print(f"\n1️⃣ 创建测试用户: {test_email}")

        async with engine.begin() as conn:
            # 插入测试用户
            result = await conn.execute(text("""
                INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser)
                VALUES (uuid_generate_v4(), :username, :email, :password, true, false)
                RETURNING id
            """), {
                "username": f"test_{uuid.uuid4().hex[:6]}",
                "email": test_email,
                "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LnYbyEjt.W6qvh5YS"
            })
            user_id = result.scalar()
            print(f"   ✅ 用户已创建: {user_id}")

            # 手动调用分配配额逻辑
            print(f"\n2️⃣ 为用户分配配额...")
            quota_types_result = await conn.execute(text("""
                SELECT id, type_key, default_limit
                FROM quota_types
                WHERE is_active = true
            """))
            quota_types = quota_types_result.fetchall()

            for quota_type_id, type_key, default_limit in quota_types:
                await conn.execute(text("""
                    INSERT INTO quota_limits (user_id, quota_type_id, limit_amount, used_amount)
                    VALUES (:user_id, :quota_type_id, :limit_amount, 0)
                    ON CONFLICT (user_id, quota_type_id) DO NOTHING
                """), {
                    "user_id": str(user_id),
                    "quota_type_id": quota_type_id,
                    "limit_amount": default_limit
                })

            print(f"   ✅ 已分配 {len(quota_types)} 种配额")

            # 验证配额是否分配成功
            print(f"\n3️⃣ 验证配额分配...")
            result = await conn.execute(text("""
                SELECT
                    qt.type_key,
                    qt.name,
                    ql.limit_amount,
                    ql.used_amount
                FROM quota_limits ql
                JOIN quota_types qt ON ql.quota_type_id = qt.id
                WHERE ql.user_id = :user_id
                ORDER BY qt.type_key
            """), {"user_id": str(user_id)})

            quotas = result.fetchall()

            if len(quotas) == 0:
                print("   ❌ 未找到配额记录！")
                return False

            print("   ✅ 配额分配成功:")
            print("   " + "="*70)
            for type_key, name, limit, used in quotas:
                print(f"   {type_key:30s} | 限额: {limit:>6} | 已用: {used}")
            print("   " + "="*70)

            # 清理测试用户
            print(f"\n4️⃣ 清理测试数据...")
            await conn.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": str(user_id)})
            print("   ✅ 测试数据已清理")

            return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    result = asyncio.run(test_user_quota_assignment())
    exit(0 if result else 1)
