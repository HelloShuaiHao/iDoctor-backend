# 支付宝真实支付接口集成问题排查指南

## 🔍 问题概述

在集成支付宝真实支付接口时遇到的关键问题和解决方案总结。

## ⚠️ 核心问题

### 1. 环境配置问题
**问题**：Docker Compose 中的环境变量覆盖了 .env 文件配置
```yaml
# ❌ 错误配置
environment:
  DATABASE_URL: postgresql+asyncpg://...
  ENVIRONMENT: development  # 这里强制设为开发环境
```

**解决**：
```yaml
# ✅ 正确配置
env_file:
  - ../.env  # 让 .env 文件控制环境
environment:
  DATABASE_URL: postgresql+asyncpg://...
  # 移除 ENVIRONMENT 让 .env 控制
```

### 2. 密钥文件格式问题
**问题**：支付宝 SDK 要求严格的密钥格式

**错误格式**：
```
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSk...  # 缺少头尾
```

**正确格式**：
```
-----BEGIN RSA PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSk...
-----END RSA PRIVATE KEY-----
```

**转换命令**：
```bash
# PKCS8 转 PKCS1 (RSA格式)
openssl rsa -in alipay_private_key.pem -traditional -out alipay_private_key_rsa.pem
```

### 3. SDK 兼容性问题
**错误信息**：
```
int() argument must be a string, a bytes-like object or a real number, not 'Sequence'
```

**原因**：Python RSA 库对密钥格式检查严格

## 🔧 完整解决方案

### 1. 环境配置
```bash
# .env 文件
ENVIRONMENT=production
ALIPAY_APP_ID=2021006102604338  # 16位数字格式
ALIPAY_PRIVATE_KEY_PATH=./keys/alipay_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=./keys/alipay_public_key.pem
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
ALIPAY_RETURN_URL=http://localhost:3000/payment/success
ALIPAY_NOTIFY_URL=http://localhost:9002/webhooks/alipay
```

### 2. Docker 配置
```yaml
payment_service:
  build:
    context: ..
    dockerfile: payment_service/Dockerfile
  env_file:
    - ../.env
  volumes:
    - ../keys:/app/keys:ro  # 挂载密钥文件
```

### 3. 密钥文件转换
```bash
# 1. 检查当前格式
head -1 alipay_private_key.pem

# 2. 如果不是 RSA 格式，转换
openssl rsa -in alipay_private_key.pem -traditional -out alipay_private_key_rsa.pem
cp alipay_private_key_rsa.pem alipay_private_key.pem

# 3. 验证格式
head -1 alipay_private_key.pem  # 应该显示 -----BEGIN RSA PRIVATE KEY-----
```

## ✅ 验证测试

### 1. 环境验证
```bash
docker exec payment_service printenv | grep ENVIRONMENT
# 应该输出：ENVIRONMENT=production
```

### 2. 密钥验证
```bash
docker exec payment_service head -1 /app/keys/alipay_private_key.pem
# 应该输出：-----BEGIN RSA PRIVATE KEY-----
```

### 3. 支付接口测试
```bash
curl -X POST "http://localhost:9002/payments/" \
  -H "Content-Type: application/json" \
  -d '{"amount": 10.00, "currency": "CNY", "payment_method": "alipay", "return_url": "http://localhost:3000/payment/success"}'
```

**成功响应**：
```json
{
  "id": "f7f6759a-a037-42b9-bb1e-767c16b16924",
  "amount": "10.00",
  "currency": "CNY", 
  "payment_method": "alipay",
  "status": "pending",
  "payment_url": "https://openapi.alipay.com/gateway.do?timestamp=2025-10-18+10%3A53%3A19&app_id=2021006102604338&method=alipay.trade.page.pay...",
  "qr_code": null,
  "created_at": "2025-10-18T10:53:19.124205"
}
```

## 🎯 关键经验总结

1. **Docker 环境变量优先级**：compose 文件 > env_file > 默认值
2. **支付宝密钥格式要求**：必须是 RSA PKCS1 格式，包含完整 PEM 头尾
3. **APP_ID 格式**：必须是 16 位数字字符串，不能是自定义名称
4. **生产/沙箱切换**：通过 ENVIRONMENT 变量控制，而非硬编码
5. **密钥文件权限**：建议设置为只读 (chmod 600)

## 🚀 技术栈

- **后端**：Python 3.11 + FastAPI
- **支付SDK**：alipay-sdk-python
- **部署**：Docker Compose
- **加密**：RSA2048 + SHA256 签名
- **环境管理**：pydantic-settings

## 📚 参考资料

- [支付宝开放平台](https://open.alipay.com/)
- [Python OpenSSL 命令](https://www.openssl.org/docs/man1.1.1/man1/rsa.html)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)