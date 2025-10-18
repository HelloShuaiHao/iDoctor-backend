#!/usr/bin/env python3
"""测试配额端点"""
import requests
import sys

def test_quota_endpoint():
    """测试 /admin/quotas/users/me 端点"""

    # 1. 先登录获取token
    print("1. 登录获取token...")
    login_url = "http://localhost:9001/auth/login"
    login_data = {
        "username": "testuser",
        "password": "password123"
    }

    try:
        response = requests.post(login_url, data=login_data)
        response.raise_for_status()
        token = response.json()["access_token"]
        print(f"✅ 登录成功，获取token: {token[:20]}...")
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        print("请确保认证服务运行在 http://localhost:9001")
        print("测试用户: testuser / password123")
        sys.exit(1)

    # 2. 测试配额端点
    print("\n2. 测试配额端点...")
    quota_url = "http://localhost:4200/admin/quotas/users/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(quota_url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ 配额信息获取成功!")
            print(f"用户ID: {data['user_id']}")
            print(f"配额数量: {data['total_quotas']}")
            print("\n配额详情:")
            for quota in data['quotas']:
                print(f"  - {quota['name']} ({quota['type_key']})")
                print(f"    已用/总数: {quota['used']}/{quota['limit']} {quota['unit']}")
                print(f"    剩余: {quota['remaining']}, 使用率: {quota['usage_percent']:.1f}%")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(f"错误: {response.text}")

    except Exception as e:
        print(f"❌ 请求异常: {e}")
        print("\n请检查:")
        print("1. 主服务是否运行在 http://localhost:4200")
        print("2. DATABASE_URL 是否正确配置")
        print("3. ENABLE_AUTH 和 ENABLE_QUOTA 是否为 true")
        print("4. 数据库中是否有该用户的配额记录")

if __name__ == "__main__":
    test_quota_endpoint()
