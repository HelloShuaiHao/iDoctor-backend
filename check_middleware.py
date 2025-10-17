#!/usr/bin/env python3
"""
检查配额中间件状态
"""
import requests
import json

BASE_URL = "http://localhost:4200"
AUTH_URL = "http://localhost:9001"

def get_token():
    """获取测试token"""
    response = requests.post(
        f"{AUTH_URL}/auth/login",
        json={
            "username_or_email": "quota_test",
            "password": "test123456"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_middleware_registration():
    """测试中间件是否注册"""
    print("=" * 60)
    print("检查中间件注册状态")
    print("=" * 60)
    
    token = get_token()
    if not token:
        print("❌ 无法获取token")
        return
    
    print(f"✅ Token获取成功: {token[:20]}...")
    
    # 测试认证中间件（/status是GET请求，会被认证中间件处理）
    print("\n1. 测试认证中间件:")
    response = requests.get(
        f"{BASE_URL}/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   - 响应码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   - 用户ID: {data.get('user_id', 'None')}")
        print(f"   - 用户邮箱: {data.get('user_email', 'None')}")
        print(f"   - 认证开关: {data.get('enable_auth', False)}")
        print(f"   - 配额开关: {data.get('enable_quota', False)}")
        
        if data.get('user_id'):
            print("   ✅ 认证中间件正常工作（user_id已注入）")
        else:
            print("   ⚠️  认证中间件可能未正常工作（user_id为None）")
    
    # 测试配额中间件（需要POST请求）
    print("\n2. 测试配额中间件:")
    print("   提示: 配额中间件需要以下条件才会生效:")
    print("   - POST请求")
    print("   - 匹配的端点路径")
    print("   - 请求成功（2xx）")
    print("   - user_id已由认证中间件注入")
    
    # 尝试一个简单的POST端点
    response = requests.post(
        f"{BASE_URL}/process/test/20250101",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\n   POST /process/test/20250101")
    print(f"   - 响应码: {response.status_code}")
    print(f"   - 响应头: {dict(response.headers)}")
    
    if "X-Quota-Remaining" in response.headers:
        print("   ✅ 配额中间件正常工作")
        print(f"   - 配额类型: {response.headers.get('X-Quota-Type')}")
        print(f"   - 剩余配额: {response.headers.get('X-Quota-Remaining')}")
    else:
        print("   ⚠️  未检测到配额响应头")
        print("   可能原因:")
        print("   - 配额管理器未初始化（quota_manager is None）")
        print("   - 端点路径不匹配（_match_endpoint返回None）")
        print("   - user_id为None（认证中间件未注入）")
        print("   - 请求失败（非2xx响应码）")
        print("   - 中间件抛出异常（查看日志）")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_middleware_registration()
