#!/usr/bin/env python3
"""
测试用户注册 API 是否自动分配配额
"""
import requests
import uuid
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

AUTH_SERVICE_URL = "http://localhost:9001"
DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/idoctor_commercial"

async def check_user_quotas(email: str):
    """检查用户配额"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            # 查询用户ID
            result = await conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
            row = result.fetchone()
            if not row:
                print(f"   ❌ 未找到用户: {email}")
                return False

            user_id = row[0]
            print(f"   ✅ 找到用户 ID: {user_id}")

            # 查询配额
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

            print(f"   ✅ 已分配 {len(quotas)} 种配额:")
            print("   " + "="*70)
            for type_key, name, limit, used in quotas:
                print(f"   {type_key:30s} | 限额: {limit:>6} | 已用: {used}")
            print("   " + "="*70)

            return True
    finally:
        await engine.dispose()

def test_registration():
    """测试注册流程"""
    # 生成唯一的测试用户
    test_id = uuid.uuid4().hex[:8]
    test_data = {
        "username": f"test_{test_id}",
        "email": f"test_{test_id}@example.com",
        "password": "testpassword123"
    }

    print(f"\n📝 测试用户注册 API...")
    print(f"   用户名: {test_data['username']}")
    print(f"   邮箱: {test_data['email']}")

    # 尝试注册
    try:
        response = requests.post(f"{AUTH_SERVICE_URL}/auth/register", json=test_data, timeout=10)

        if response.status_code == 201:
            print(f"   ✅ 注册成功！")
            user_data = response.json()
            print(f"   用户 ID: {user_data.get('id')}")

            # 检查配额是否自动分配
            print(f"\n📊 检查自动分配的配额...")
            has_quotas = asyncio.run(check_user_quotas(test_data['email']))

            if has_quotas:
                print(f"\n✅ 测试通过：用户注册时自动分配了配额")
                return True
            else:
                print(f"\n❌ 测试失败：用户注册后没有配额")
                return False

        else:
            print(f"   ❌ 注册失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"   ⚠️  无法连接到认证服务 ({AUTH_SERVICE_URL})")
        print(f"   提示: 请先启动认证服务")
        print(f"   命令: cd commercial && uvicorn auth_service.main:app --port 9001")
        return False
    except Exception as e:
        print(f"   ❌ 测试出错: {e}")
        return False

if __name__ == "__main__":
    result = test_registration()
    exit(0 if result else 1)
