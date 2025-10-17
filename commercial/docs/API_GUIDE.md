# iDoctor 商业化模块 API 使用指南

## 📋 概述

本文档提供 iDoctor 商业化模块的完整 API 使用指南，包括认证服务和支付服务的所有可用端点。

## 🌐 服务端点

- **认证服务**: http://localhost:9001
- **支付服务**: http://localhost:9002
- **API 文档**:
  - 认证服务文档: http://localhost:9001/docs
  - 支付服务文档: http://localhost:9002/docs

## 🔐 认证服务 API

### 用户认证

#### 1. 用户注册
```bash
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123"
}
```

**响应示例:**
```json
{
  "email": "user@example.com",
  "username": "username", 
  "id": "uuid",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-10-17T07:16:28.588049",
  "updated_at": "2025-10-17T07:16:28.588052"
}
```

#### 2. 用户登录
```bash
POST /auth/login
Content-Type: application/json

{
  "username_or_email": "username",
  "password": "password123"
}
```

**响应示例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### 3. 刷新令牌
```bash
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### 用户管理

#### 1. 获取当前用户信息
```bash
GET /users/me
Authorization: Bearer <access_token>
```

#### 2. 更新用户信息
```bash
PUT /users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "newemail@example.com",
  "username": "newusername"
}
```

#### 3. 获取用户信息（管理员）
```bash
GET /users/{user_id}
Authorization: Bearer <admin_access_token>
```

### API 密钥管理

#### 1. 创建 API 密钥
```bash
POST /api-keys/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "My API Key",
  "expires_at": "2025-12-31T23:59:59"
}
```

**响应示例:**
```json
{
  "id": "uuid",
  "key_prefix": "sk_live_abc...",
  "name": "My API Key", 
  "is_active": true,
  "created_at": "2025-10-17T07:16:28.588049",
  "expires_at": "2025-12-31T23:59:59",
  "key": "sk_live_example_key_for_documentation_only"
}
```

#### 2. 列出 API 密钥
```bash
GET /api-keys/
Authorization: Bearer <access_token>
```

#### 3. 删除 API 密钥
```bash
DELETE /api-keys/{key_id}
Authorization: Bearer <access_token>
```

#### 4. 停用 API 密钥
```bash
PATCH /api-keys/{key_id}/deactivate
Authorization: Bearer <access_token>
```

## 💳 支付服务 API

### 订阅计划管理

#### 1. 获取所有订阅计划
```bash
GET /plans/
# 可选参数: ?active_only=true
```

**响应示例:**
```json
[
  {
    "id": "uuid",
    "name": "Basic Plan",
    "description": "基础订阅计划",
    "price": "99.00",
    "currency": "CNY",
    "billing_cycle": "monthly",
    "quota_type": "processing_count",
    "quota_limit": 100,
    "features": {"api_access": true},
    "is_active": true,
    "created_at": "2025-10-17T07:16:28.588049"
  }
]
```

#### 2. 获取订阅计划详情
```bash
GET /plans/{plan_id}
```

#### 3. 创建订阅计划（管理员）
```bash
POST /plans/
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
  "name": "Premium Plan",
  "description": "高级订阅计划", 
  "price": 299.00,
  "currency": "CNY",
  "billing_cycle": "monthly",
  "quota_type": "processing_count",
  "quota_limit": 1000,
  "features": {
    "api_access": true,
    "priority_support": true,
    "advanced_features": true
  }
}
```

### 支付管理

#### 1. 创建支付订单

**匿名支付:**
```bash
POST /payments/
Content-Type: application/json

{
  "amount": 99.00,
  "currency": "CNY", 
  "payment_method": "alipay"
}
```

**用户关联支付:**
```bash
POST /payments/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "amount": 299.00,
  "currency": "CNY",
  "payment_method": "wechat",
  "subscription_id": "uuid_of_subscription"
}
```

**支付宝响应示例:**
```json
{
  "id": "1fd0d42b-c0b4-4089-abe9-37b87746abc2",
  "amount": "99.00",
  "currency": "CNY",
  "payment_method": "alipay", 
  "status": "pending",
  "payment_url": "https://sandbox-alipay.com/mock-payment?order_id=...",
  "qr_code": null,
  "created_at": "2025-10-17T07:15:55.215588"
}
```

**微信支付响应示例:**
```json
{
  "id": "1db52e11-fa0a-4738-b74f-be16b85a382a",
  "amount": "158.00", 
  "currency": "CNY",
  "payment_method": "wechat",
  "status": "pending",
  "payment_url": null,
  "qr_code": "weixin://wxpay/bizpayurl?order_id=...",
  "created_at": "2025-10-17T07:16:06.961346"
}
```

#### 2. 查询支付状态
```bash
GET /payments/{payment_id}
```

#### 3. 申请退款
```bash
POST /payments/{payment_id}/refund
Content-Type: application/json

{
  "refund_amount": 99.00,
  "reason": "用户申请退款"
}
```

### Webhook 回调

#### 支付宝回调
```bash
POST /webhooks/alipay
Content-Type: application/x-www-form-urlencoded

# 支付宝会发送表单数据
```

#### 微信回调  
```bash
POST /webhooks/wechat
Content-Type: text/xml

# 微信会发送XML数据
```

#### 测试回调接口
```bash
GET /webhooks/test
```

**响应示例:**
```json
{
  "message": "Webhook endpoints are working",
  "endpoints": {
    "alipay": "/webhooks/alipay",
    "wechat": "/webhooks/wechat"
  }
}
```

## 🔧 健康检查

### 认证服务健康检查
```bash
GET /health
```

**响应:**
```json
{"status": "ok", "service": "auth"}
```

### 支付服务健康检查
```bash
GET /health  
```

**响应:**
```json
{"status": "ok", "service": "payment"}
```

## 📊 状态码说明

- `200` - 成功
- `201` - 创建成功
- `204` - 删除成功
- `400` - 请求错误
- `401` - 未认证
- `403` - 权限不足
- `404` - 资源不存在
- `500` - 服务器错误

## 🚀 快速开始示例

### 完整的支付流程示例

```bash
# 1. 创建支付订单
PAYMENT_RESPONSE=$(curl -s -X POST "http://localhost:9002/payments/" \
  -H "Content-Type: application/json" \
  -d '{"amount": 99.00, "currency": "CNY", "payment_method": "alipay"}')

# 2. 提取支付ID和支付链接
PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
PAYMENT_URL=$(echo $PAYMENT_RESPONSE | jq -r '.payment_url')

echo "支付ID: $PAYMENT_ID"
echo "支付链接: $PAYMENT_URL"

# 3. 查询支付状态
curl -s "http://localhost:9002/payments/$PAYMENT_ID"
```

### 完整的用户注册和API密钥创建流程

```bash
# 1. 用户注册
curl -X POST "http://localhost:9001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser", "password": "password123"}'

# 2. 用户登录
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:9001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username_or_email": "testuser", "password": "password123"}')

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# 3. 创建API密钥
curl -X POST "http://localhost:9001/api-keys/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"name": "My Test API Key"}'
```

## ⚙️ 环境配置

### 开发环境
当前配置为开发环境，支付提供商返回模拟数据。

### 生产环境配置
要切换到生产环境，需要配置以下环境变量：

```bash
ENVIRONMENT=production
ALIPAY_APP_ID=your_real_alipay_app_id
ALIPAY_PRIVATE_KEY_PATH=/path/to/alipay_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=/path/to/alipay_public_key.pem
ALIPAY_NOTIFY_URL=https://yourdomain.com/webhooks/alipay

WECHAT_APP_ID=your_real_wechat_app_id  
WECHAT_MCH_ID=your_real_mch_id
WECHAT_API_KEY=your_real_api_key
WECHAT_CERT_PATH=/path/to/apiclient_cert.pem
WECHAT_KEY_PATH=/path/to/apiclient_key.pem
WECHAT_NOTIFY_URL=https://yourdomain.com/webhooks/wechat
```

## 📞 技术支持

如需帮助，请查看：
- API 交互式文档: http://localhost:9001/docs 和 http://localhost:9002/docs
- 项目状态文档: `docs/PROJECT_STATUS.md`
- 快速开始指南: `docs/QUICK_START.md`