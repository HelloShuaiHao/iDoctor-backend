#!/usr/bin/env python3
"""
简单的配额系统集成测试
测试认证和配额功能是否正常工作
"""
import requests
import json
import sys

BASE_URL = "http://localhost:4200"
AUTH_URL = "http://localhost:9001"  # 认证服务

def test_without_auth():
    """测试1: 不带认证访问应该被拒绝"""
    print("\n🧪 测试1: 不带认证访问...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 401:
            print("✅ 正确拒绝了未认证请求")
            return True
        elif response.status_code == 200:
            print("⚠️  未启用认证，请求被允许（开发模式）")
            return True
        else:
            print(f"❌ 意外的响应码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def register_test_user():
    """注册测试用户"""
    print("\n🧪 注册测试用户...")
    try:
        response = requests.post(
            f"{AUTH_URL}/auth/register",
            json={
                "email": "quota_test@example.com",
                "username": "quota_test",
                "password": "test123456"
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print("✅ 用户注册成功")
            return True
        elif response.status_code in [400, 422]:
            # 检查是否是用户已存在的错误
            error_text = response.text.lower()
            if "already exists" in error_text or "已被注册" in response.text or "已被使用" in response.text:
                print("ℹ️  用户已存在，跳过注册")
                return True
        
        print(f"❌ 注册失败: {response.status_code} - {response.text}")
        return False
    except requests.exceptions.ConnectionError:
        print("⚠️  认证服务未运行，跳过认证测试")
        return False
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        return False

def login_and_get_token():
    """登录并获取token"""
    print("\n🧪 登录获取token...")
    try:
        response = requests.post(
            f"{AUTH_URL}/auth/login",
            json={
                "username_or_email": "quota_test",
                "password": "test123456"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print(f"✅ 登录成功，获取token: {token[:20]}...")
                return token
        
        print(f"❌ 登录失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return None

def test_with_auth(token):
    """测试2: 带认证访问（GET请求）"""
    print("\n🧪 测试2: 带认证访问（GET请求）...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/status", headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ 认证请求成功")
            data = response.json()
            print(f"   - 已认证用户: {data.get('user_email', 'N/A')}")
            print(f"   - 认证开关: {data.get('enable_auth', False)}")
            print(f"   - 配额开关: {data.get('enable_quota', False)}")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def test_quota_headers(token):
    """测试3: 配额响应头（POST请求）"""
    print("\n🧪 测试3: 配额响应头（POST请求）...")
    print("提示: 测试配额系统需要触发一个POST请求，但数据可能不存在")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试多个端点，找到一个能响应的
        test_endpoints = [
            ("/process/test_patient/20250101", "api_calls_full_process"),
            ("/l3_detect/test_patient/20250101", "api_calls_l3_detect"),
            ("/continue_after_l3/test_patient/20250101", "api_calls_continue"),
        ]
        
        quota_detected = False
        
        for endpoint, expected_type in test_endpoints:
            print(f"\n  测试端点: {endpoint}")
            try:
                response = requests.post(
                    f"{BASE_URL}{endpoint}",
                    headers=headers,
                    timeout=5
                )
                
                # 检查配额响应头
                if "X-Quota-Remaining" in response.headers:
                    print(f"  ✅ 配额系统已启用:")
                    print(f"     - 配额类型: {response.headers.get('X-Quota-Type', 'N/A')}")
                    print(f"     - 剩余配额: {response.headers.get('X-Quota-Remaining', 'N/A')}")
                    print(f"     - 已用配额: {response.headers.get('X-Quota-Used', 'N/A')}")
                    print(f"     - 请求状态: {response.status_code}")
                    quota_detected = True
                    break
                elif response.status_code == 402:
                    print(f"  ⚠️  配额已耗尽（但配额系统正常工作）")
                    try:
                        error_data = response.json()
                        print(f"     - 错误信息: {error_data.get('message', 'N/A')}")
                        print(f"     - 配额类型: {error_data.get('quota_type', 'N/A')}")
                        print(f"     - 剩余配额: {error_data.get('remaining', 'N/A')}")
                    except:
                        pass
                    quota_detected = True
                    break
                else:
                    print(f"     - 响应码: {response.status_code}, 未检测到配额头")
            except Exception as e:
                print(f"     - 请求失败: {e}")
                continue
        
        if quota_detected:
            return True
        else:
            print(f"\n⚠️  所有测试端点均未检测到配额响应头")
            print(f"   - 原因: 配额中间件仅在请求成功（2xx）时添加响应头")
            print(f"   - 建议: 上传真实数据后再测试，或查看后端日志")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def check_service_status():
    """检查服务状态"""
    print("\n🔍 检查服务状态...")
    
    # 检查主应用
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 主应用 (4200) 正在运行")
            main_running = True
        else:
            print("❌ 主应用可能未运行")
            main_running = False
    except:
        print("❌ 主应用 (4200) 未响应")
        main_running = False
    
    # 检查认证服务
    try:
        response = requests.get(f"{AUTH_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 认证服务 (9001) 正在运行")
            auth_running = True
        else:
            print("⚠️  认证服务可能未运行")
            auth_running = False
    except:
        print("⚠️  认证服务 (9001) 未响应")
        auth_running = False
    
    return main_running, auth_running

def main():
    print("=" * 60)
    print("🚀 配额系统集成测试")
    print("=" * 60)
    
    # 检查服务状态
    main_running, auth_running = check_service_status()
    
    if not main_running:
        print("\n❌ 主应用未运行，请先启动:")
        print("   uvicorn app:app --reload --host 0.0.0.0 --port 4200")
        sys.exit(1)
    
    # 测试1: 不带认证访问
    test_without_auth()
    
    if auth_running:
        # 测试完整认证流程
        if register_test_user():
            token = login_and_get_token()
            if token:
                test_with_auth(token)
                test_quota_headers(token)
            else:
                print("\n⚠️  无法获取token，跳过认证测试")
        else:
            print("\n⚠️  无法注册用户，跳过认证测试")
    else:
        print("\n⚠️  认证服务未运行，无法测试完整认证流程")
        print("   启动认证服务:")
        print("   cd commercial && ./start.sh")
    
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    print("✅ 主应用运行中" if main_running else "❌ 主应用未运行")
    print("✅ 认证服务运行中" if auth_running else "⚠️  认证服务未运行")
    print("\n💡 提示:")
    print("  1. 如果要启用完整的认证和配额功能:")
    print("     - 确保 .env 文件中 ENABLE_AUTH=true 和 ENABLE_QUOTA=true")
    print("     - 启动认证服务: cd commercial && ./start.sh")
    print("     - 重启主应用")
    print("  2. 查看启动日志中是否有:")
    print("     🔐 认证中间件: ✅ 启用")
    print("     📊 配额中间件: ✅ 启用")
    print("=" * 60)

if __name__ == "__main__":
    main()
