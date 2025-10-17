# 支付系统配置指南

本文档详细说明如何配置支付宝和微信支付的真实支付功能。

## 📋 目录

1. [支付宝配置](#支付宝配置)
2. [微信支付配置](#微信支付配置)
3. [密钥文件管理](#密钥文件管理)
4. [环境变量配置](#环境变量配置)
5. [测试指南](#测试指南)
6. [常见问题](#常见问题)

---

## 🔵 支付宝配置

### 1. 创建支付宝应用

1. 登录 [支付宝开放平台](https://open.alipay.com/)
2. 进入「开发者中心」→「网页&移动应用」
3. 创建应用，选择「电脑网站支付」或「手机网站支付」
4. 记录 **APPID**

### 2. 生成应用密钥

支付宝使用 RSA2 签名方式，需要生成公钥和私钥：

#### 方法一：使用支付宝工具（推荐）

1. 下载 [支付宝开放平台开发助手](https://opendocs.alipay.com/common/02kipl)
2. 选择「RSA2(SHA256)密钥」→「生成密钥」
3. 将生成的密钥保存到 `keys/` 目录

#### 方法二：使用 OpenSSL 命令

```bash
# 生成私钥
openssl genrsa -out keys/alipay_private_key.pem 2048

# 从私钥生成公钥
openssl rsa -in keys/alipay_private_key.pem -pubout -out keys/alipay_public_key_temp.pem

# 提取公钥内容（去掉头尾）
cat keys/alipay_public_key_temp.pem
```

### 3. 上传公钥到支付宝

1. 在应用详情页，找到「接口加签方式」→「设置」
2. 选择「公钥」模式
3. 粘贴你生成的**应用公钥**（不包含 BEGIN/END 行）
4. 保存后，支付宝会生成**支付宝公钥**
5. 复制支付宝公钥，保存到 `keys/alipay_public_key.pem`（需要添加 BEGIN/END 行）

**支付宝公钥格式示例：**
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
...
-----END PUBLIC KEY-----
```

### 4. 配置异步通知地址

在应用设置中配置：
- **授权回调地址**：`http://your-domain.com:9002/payments/return`
- **应用网关**：`http://your-domain.com:9002/payments/webhooks/alipay`

⚠️ **注意**：
- 开发环境可以使用内网穿透工具（如 ngrok、frp）
- 生产环境必须使用公网可访问的 HTTPS 地址

### 5. 环境变量配置

编辑 `.env` 文件：

```bash
# 支付宝应用配置
ALIPAY_APP_ID=2021001199600000  # 你的应用APPID

# 密钥文件路径（相对于项目根目录）
ALIPAY_PRIVATE_KEY_PATH=./keys/alipay_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=./keys/alipay_public_key.pem

# 支付宝网关
# 沙箱环境（测试）
ALIPAY_GATEWAY=https://openapi.alipaydev.com/gateway.do
# 生产环境（正式）
# ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do

# 回调地址（必须是公网可访问）
ALIPAY_RETURN_URL=http://your-domain.com:4200/payment/return
ALIPAY_NOTIFY_URL=http://your-domain.com:9002/payments/webhooks/alipay
```

---

## 💚 微信支付配置

### 1. 注册微信商户平台

1. 访问 [微信支付商户平台](https://pay.weixin.qq.com/)
2. 注册并完成企业认证
3. 记录 **商户号（mch_id）**

### 2. 创建应用并获取密钥

1. 登录 [微信开放平台](https://open.weixin.qq.com/)
2. 创建「网站应用」或「公众号」
3. 记录 **AppID**

4. 在商户平台设置 **API密钥**：
   - 登录商户平台 → 账户中心 → API安全 → 设置API密钥
   - 设置32位的随机字符串（必须妥善保管）

### 3. 下载商户证书

1. 在商户平台 → 账户中心 → API安全 → 申请API证书
2. 下载证书工具，生成证书
3. 将以下文件保存到 `keys/` 目录：
   - `apiclient_cert.pem` （商户证书）
   - `apiclient_key.pem` （商户私钥）

### 4. 配置支付目录和回调

在商户平台配置：
- **支付授权目录**：`http://your-domain.com/payment/`
- **扫码回调链接**：`http://your-domain.com:9002/payments/webhooks/wechat`

### 5. 环境变量配置

编辑 `.env` 文件：

```bash
# 微信支付配置
WECHAT_APP_ID=wx1234567890abcdef  # 你的AppID
WECHAT_MCH_ID=1234567890          # 你的商户号
WECHAT_API_KEY=your32characterlongapikeyhere12  # API密钥（32位）

# 证书路径
WECHAT_CERT_PATH=./keys/apiclient_cert.pem
WECHAT_KEY_PATH=./keys/apiclient_key.pem

# 回调地址
WECHAT_NOTIFY_URL=http://your-domain.com:9002/payments/webhooks/wechat
```

---

## 🔐 密钥文件管理

### 目录结构

```
commercial/
├── keys/                              # 密钥文件目录
│   ├── .gitignore                     # 忽略密钥文件
│   ├── alipay_private_key.pem         # 支付宝应用私钥
│   ├── alipay_public_key.pem          # 支付宝公钥
│   ├── apiclient_cert.pem             # 微信商户证书
│   ├── apiclient_key.pem              # 微信商户私钥
│   └── README.md                      # 密钥说明文档
```

### 安全注意事项

⚠️ **重要**：密钥文件绝对不能提交到 Git！

1. 确保 `keys/.gitignore` 包含：
```
*.pem
*.p12
*.pfx
```

2. 生产环境密钥管理建议：
   - 使用环境变量或密钥管理服务（如 AWS Secrets Manager）
   - 限制文件权限：`chmod 600 keys/*.pem`
   - 定期轮换密钥
   - 使用不同的开发/生产密钥

---

## ⚙️ 环境变量配置

### 完整 `.env` 示例

```bash
# ==================== 数据库配置 ====================
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/idoctor_commercial

# ==================== JWT配置 ====================
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ==================== 支付宝配置 ====================
ALIPAY_APP_ID=2021001199600000
ALIPAY_PRIVATE_KEY_PATH=./keys/alipay_private_key.pem
ALIPAY_PUBLIC_KEY_PATH=./keys/alipay_public_key.pem
# 沙箱：https://openapi.alipaydev.com/gateway.do
# 生产：https://openapi.alipay.com/gateway.do
ALIPAY_GATEWAY=https://openapi.alipaydev.com/gateway.do
ALIPAY_RETURN_URL=http://your-domain.com:4200/payment/return
ALIPAY_NOTIFY_URL=http://your-domain.com:9002/payments/webhooks/alipay

# ==================== 微信支付配置 ====================
WECHAT_APP_ID=wx1234567890abcdef
WECHAT_MCH_ID=1234567890
WECHAT_API_KEY=your32characterlongapikeyhere12
WECHAT_CERT_PATH=./keys/apiclient_cert.pem
WECHAT_KEY_PATH=./keys/apiclient_key.pem
WECHAT_NOTIFY_URL=http://your-domain.com:9002/payments/webhooks/wechat

# ==================== Redis配置 ====================
REDIS_URL=redis://localhost:6379/0

# ==================== 服务端口 ====================
AUTH_SERVICE_PORT=9001
PAYMENT_SERVICE_PORT=9002
GATEWAY_PORT=9000

# ==================== CORS配置 ====================
CORS_ORIGINS=http://localhost:7500,http://localhost:4200,http://your-domain.com

# ==================== 环境 ====================
# development = 沙箱模式（模拟支付）
# production = 生产模式（真实支付）
ENVIRONMENT=development
```

---

## 🧪 测试指南

### 1. 沙箱环境测试（推荐先测试）

**支付宝沙箱**：
1. 访问 [支付宝开放平台沙箱](https://openhome.alipay.com/platform/appDaily.htm)
2. 获取沙箱应用信息（AppID、网关地址）
3. 下载沙箱钱包APP进行测试

**微信沙箱**：
微信没有公开沙箱，建议先设置 `ENVIRONMENT=development` 使用模拟模式。

### 2. 测试支付流程

```bash
# 启动支付服务
cd payment_service
python app.py

# 测试创建支付订单
curl -X POST "http://localhost:9002/payments/" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 0.01,
    "currency": "CNY",
    "payment_method": "alipay",
    "return_url": "http://localhost:4200/payment/return"
  }'
```

返回示例：
```json
{
  "id": "uuid-here",
  "amount": 0.01,
  "payment_url": "https://openapi.alipaydev.com/...",
  "status": "pending"
}
```

访问 `payment_url` 进行支付测试。

### 3. 测试回调通知

使用内网穿透工具（开发环境）：

```bash
# 使用 ngrok
ngrok http 9002

# 将生成的公网地址配置到 ALIPAY_NOTIFY_URL
# 例如：https://abc123.ngrok.io/payments/webhooks/alipay
```

---

## ❓ 常见问题

### Q1: 支付宝报错 "invalid-app-id"
**原因**：APPID 配置错误或未审核通过
**解决**：检查 `.env` 中的 `ALIPAY_APP_ID`，确认应用已签约

### Q2: 支付宝报错 "invalid-signature"
**原因**：密钥配置错误或格式不对
**解决**：
1. 确认应用私钥和支付宝公钥都正确
2. 检查 PEM 文件格式（必须有 BEGIN/END 行）
3. 确认公钥已上传到支付宝平台

### Q3: 微信支付报错 "签名错误"
**原因**：API密钥配置错误
**解决**：检查 `WECHAT_API_KEY` 是否为32位，与商户平台设置一致

### Q4: 回调地址无法访问
**原因**：localhost 无法被外网访问
**解决**：
- 开发环境：使用 ngrok、frp 等内网穿透
- 生产环境：配置公网域名和 HTTPS

### Q5: 如何切换沙箱/生产环境？
**方法**：修改 `.env` 中的 `ENVIRONMENT` 和 `ALIPAY_GATEWAY`

```bash
# 沙箱环境
ENVIRONMENT=development
ALIPAY_GATEWAY=https://openapi.alipaydev.com/gateway.do

# 生产环境
ENVIRONMENT=production
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
```

### Q6: 支付成功但订阅未激活？
**原因**：回调处理失败或未正确更新数据库
**解决**：
1. 检查 `payment_service/api/webhooks.py` 日志
2. 确认数据库连接正常
3. 手动触发回调测试

---

## 📚 相关文档

- [支付宝开放平台文档](https://opendocs.alipay.com/open/270/105898)
- [微信支付开发文档](https://pay.weixin.qq.com/wiki/doc/api/index.html)
- [项目 API 文档](./API_GUIDE.md)
- [快速开始指南](./QUICK_START.md)

---

## 🆘 获取帮助

如遇到配置问题：
1. 检查本文档「常见问题」章节
2. 查看服务日志：`logs/payment_service.log`
3. 参考官方文档
4. 提交 Issue 到项目仓库

---

**最后更新**：2025-01-17
**维护者**：iDoctor Team
