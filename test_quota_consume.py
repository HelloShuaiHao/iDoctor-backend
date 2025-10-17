#!/usr/bin/env python3
import requests

# 1. 登录获取 token
response = requests.post(
    "http://localhost:9001/auth/login",
    json={"username_or_email": "quota_test", "password": "test123456"}
)
token = response.json()["access_token"]
print(f"Token: {token[:30]}...\n")

# 2. 连续发送 3 次请求，观察配额消耗
endpoint = "/continue_after_l3/test_patient/20250101"
headers = {"Authorization": f"Bearer {token}"}

for i in range(1, 4):
    print(f"第 {i} 次请求: POST {endpoint}")
    response = requests.post(f"http://localhost:4200{endpoint}", headers=headers)
    
    print(f"  状态: {response.status_code}")
    print(f"  配额类型: {response.headers.get('x-quota-type', 'N/A')}")
    print(f"  剩余配额: {response.headers.get('x-quota-remaining', 'N/A')}")
    print(f"  已用配额: {response.headers.get('x-quota-used', 'N/A')}")
    print()
