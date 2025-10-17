#!/usr/bin/env python3
"""Debug script to test JWT token generation and validation"""
import sys
import os
import requests
from jose import jwt, JWTError

# Add commercial to path
sys.path.insert(0, 'commercial')
from shared.config import settings

# Get a token from auth service
print("🔑 Getting token from auth service...")
response = requests.post(
    "http://localhost:9001/auth/login",
    json={
        "username_or_email": "quota_test",
        "password": "test123456"
    }
)

if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code} - {response.text}")
    sys.exit(1)

token = response.json()["access_token"]
print(f"✅ Token received: {token[:30]}...")

# Try to decode with the secret from settings
print(f"\n🔍 Decoding token with JWT_SECRET_KEY from settings...")
print(f"   Secret (first 20 chars): {settings.JWT_SECRET_KEY[:20]}...")

try:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    print(f"✅ Token decoded successfully!")
    print(f"   User ID (sub): {payload.get('sub')}")
    print(f"   Email: {payload.get('email')}")
    print(f"   Token type: {payload.get('type')}")
    print(f"   Expires: {payload.get('exp')}")
except JWTError as e:
    print(f"❌ Token decode failed: {e}")
    
# Now try to access the main app
print(f"\n🌐 Testing access to main app...")
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:4200/status", headers=headers)
print(f"   Status: {response.status_code}")
print(f"   Response: {response.text}")
