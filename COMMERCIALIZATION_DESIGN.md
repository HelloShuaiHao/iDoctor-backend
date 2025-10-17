# 商业化模块架构设计

## 设计目标

1. **通用性**：认证和支付模块可被多个应用复用
2. **扩展性**：易于添加新的支付方式和认证方式
3. **解耦性**：模块间低耦合，可独立部署或集成部署
4. **安全性**：符合金融级安全标准

## 架构选择：模块化单体应用

考虑到项目规模和部署复杂度，采用**模块化单体架构**：
- 认证模块（`auth_service/`）：独立Python包
- 支付模块（`payment_service/`）：独立Python包
- 主应用（`app.py`）：通过依赖注入使用这两个模块

**优势**：
- 代码复用：其他项目可直接安装这两个包
- 部署简单：单一服务，无需微服务编排
- 易于迁移：未来可轻松拆分为微服务

## 技术栈

### 核心框架
- **FastAPI** - 现有框架，支持异步
- **SQLAlchemy 2.0** - ORM + 异步支持
- **Alembic** - 数据库迁移
- **Redis** - 缓存和会话存储（可选）

### 认证
- **python-jose** - JWT token生成和验证
- **passlib + bcrypt** - 密码哈希
- **python-multipart** - 表单数据支持

### 支付
- **alipay-sdk-python** - 支付宝SDK
- **wechatpy** - 微信支付SDK
- **stripe** - 国际信用卡支付

### 数据库
- **PostgreSQL** - 生产环境推荐
- **SQLite** - 开发/测试环境

## 数据库设计

### 用户表 (users)
```sql
id: UUID (主键)
email: String (唯一索引)
username: String (唯一索引)
hashed_password: String
is_active: Boolean (默认True)
is_superuser: Boolean (默认False)
created_at: DateTime
updated_at: DateTime
```

### 订阅计划表 (subscription_plans)
```sql
id: UUID (主键)
name: String (例如: "免费版", "专业版", "企业版")
price: Decimal
currency: String (CNY/USD)
billing_cycle: String (monthly/yearly/lifetime)
quota_type: String (例如: "processing_count")
quota_limit: Integer (每月处理次数限制)
features: JSON (功能列表)
is_active: Boolean
created_at: DateTime
```

### 用户订阅表 (user_subscriptions)
```sql
id: UUID (主键)
user_id: UUID (外键 -> users)
plan_id: UUID (外键 -> subscription_plans)
status: String (active/cancelled/expired)
current_period_start: DateTime
current_period_end: DateTime
quota_used: Integer (当前周期已使用配额)
quota_limit: Integer (配额上限，冗余存储)
auto_renew: Boolean
created_at: DateTime
updated_at: DateTime
```

### 支付交易表 (payment_transactions)
```sql
id: UUID (主键)
user_id: UUID (外键 -> users)
subscription_id: UUID (外键 -> user_subscriptions, 可为空)
amount: Decimal
currency: String
payment_method: String (alipay/wechat/stripe)
payment_provider_id: String (第三方交易ID)
status: String (pending/completed/failed/refunded)
metadata: JSON (额外信息)
created_at: DateTime
updated_at: DateTime
```

### API密钥表 (api_keys)
```sql
id: UUID (主键)
user_id: UUID (外键 -> users)
key_prefix: String (显示用，如 "sk_live_abc...")
key_hash: String (哈希后的完整密钥)
name: String (用户自定义名称)
last_used_at: DateTime
is_active: Boolean
created_at: DateTime
expires_at: DateTime (可为空，永不过期)
```

### 使用记录表 (usage_logs)
```sql
id: UUID (主键)
user_id: UUID (外键 -> users)
subscription_id: UUID (外键 -> user_subscriptions)
resource_type: String (例如: "dicom_processing")
resource_id: String (例如: 任务ID)
quota_cost: Integer (消耗的配额数)
created_at: DateTime
metadata: JSON (额外信息，如处理时长)
```

## 认证模块设计

### 目录结构
```
auth_service/
├── __init__.py
├── models.py          # SQLAlchemy模型
├── schemas.py         # Pydantic模型（请求/响应）
├── security.py        # 密码哈希、JWT生成/验证
├── dependencies.py    # FastAPI依赖项（获取当前用户）
├── router.py          # API路由
└── config.py          # 配置（密钥、过期时间等）
```

### 核心功能

#### 1. JWT认证
- Access Token：短期（15分钟），用于API调用
- Refresh Token：长期（7天），用于刷新Access Token
- Token payload：`{sub: user_id, exp: expiry, type: "access"/"refresh"}`

#### 2. API Key认证
- 格式：`sk_live_xxxxxxxxxxxxx`（前缀+随机字符串）
- 存储：哈希后存储，类似密码
- 用途：适合服务端调用，无需频繁刷新

#### 3. 权限控制
- 基于装饰器：`@require_auth`, `@require_subscription(plan="pro")`
- 基于中间件：全局检查认证状态
- 细粒度权限：`@require_permission("admin")`

### API端点

```python
POST   /auth/register          # 用户注册
POST   /auth/login             # 登录（返回token）
POST   /auth/refresh           # 刷新token
POST   /auth/logout            # 登出（可选，主要用于撤销refresh token）
GET    /auth/me                # 获取当前用户信息
PUT    /auth/me                # 更新用户信息
POST   /auth/change-password   # 修改密码
POST   /auth/reset-password    # 重置密码（需邮件验证）

# API密钥管理
GET    /auth/api-keys          # 列出API密钥
POST   /auth/api-keys          # 创建API密钥
DELETE /auth/api-keys/{key_id} # 删除API密钥
```

## 支付模块设计

### 目录结构
```
payment_service/
├── __init__.py
├── models.py          # SQLAlchemy模型
├── schemas.py         # Pydantic模型
├── providers/
│   ├── __init__.py
│   ├── base.py        # 抽象基类PaymentProvider
│   ├── alipay.py      # 支付宝实现
│   ├── wechat.py      # 微信支付实现
│   └── stripe.py      # Stripe实现
├── router.py          # API路由
├── webhooks.py        # 支付回调处理
└── config.py          # 配置
```

### 抽象支付接口

```python
class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, amount, currency, order_id, **kwargs) -> Dict:
        """创建支付订单，返回支付URL或二维码"""
        pass

    @abstractmethod
    async def verify_payment(self, transaction_id: str) -> PaymentStatus:
        """验证支付状态"""
        pass

    @abstractmethod
    async def handle_webhook(self, request: Request) -> WebhookResult:
        """处理支付回调"""
        pass

    @abstractmethod
    async def refund(self, transaction_id: str, amount: Decimal) -> RefundResult:
        """退款"""
        pass
```

### API端点

```python
# 订阅计划
GET    /payments/plans                    # 列出所有计划
GET    /payments/plans/{plan_id}          # 获取计划详情

# 订阅管理
POST   /payments/subscriptions/subscribe  # 订阅计划（创建支付订单）
GET    /payments/subscriptions/current    # 获取当前订阅
POST   /payments/subscriptions/cancel     # 取消订阅
POST   /payments/subscriptions/renew      # 续费

# 支付
POST   /payments/create                   # 创建支付订单
GET    /payments/status/{transaction_id}  # 查询支付状态

# Webhook（不需要认证，但需要签名验证）
POST   /payments/webhooks/alipay          # 支付宝回调
POST   /payments/webhooks/wechat          # 微信回调
POST   /payments/webhooks/stripe          # Stripe回调

# 管理
GET    /payments/transactions             # 交易记录
POST   /payments/refund/{transaction_id}  # 退款（管理员）
```

## 配额管理系统

### 中间件设计

```python
class QuotaMiddleware:
    async def check_quota(self, user_id: UUID, resource_type: str, cost: int = 1):
        """检查并扣减配额"""
        subscription = await get_active_subscription(user_id)
        if subscription.quota_used + cost > subscription.quota_limit:
            raise QuotaExceededError()

        # 扣减配额
        subscription.quota_used += cost
        await db.commit()

        # 记录使用日志
        await log_usage(user_id, subscription.id, resource_type, cost)
```

### 装饰器用法

```python
@router.post("/process/{patient_name}/{study_date}")
@require_auth
@consume_quota(resource_type="dicom_processing", cost=1)
async def process_case(current_user: User, ...):
    # 处理逻辑
    pass
```

## 与现有系统集成

### 修改现有API

在 `app.py` 中添加认证中间件：

```python
from auth_service.dependencies import get_current_user, require_subscription
from payment_service.quota import consume_quota

# 需要认证的端点
@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)  # 添加认证
):
    # 检查配额
    await consume_quota(current_user.id, "dicom_processing", cost=1)

    # 原有逻辑
    ...
```

### 公开端点保持不变

某些端点可以保持公开（例如健康检查）：

```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

## 部署建议

### 环境变量配置

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost/idoctor

# JWT密钥
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# 支付宝
ALIPAY_APP_ID=your-app-id
ALIPAY_PRIVATE_KEY=path/to/private_key.pem
ALIPAY_PUBLIC_KEY=path/to/alipay_public_key.pem
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do  # 或沙箱环境

# 微信支付
WECHAT_APP_ID=your-app-id
WECHAT_MCH_ID=your-mch-id
WECHAT_API_KEY=your-api-key
WECHAT_CERT_PATH=path/to/apiclient_cert.pem
WECHAT_KEY_PATH=path/to/apiclient_key.pem

# Stripe
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Redis（可选，用于缓存和会话）
REDIS_URL=redis://localhost:6379/0
```

### 数据库迁移

```bash
# 初始化Alembic
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial tables"

# 应用迁移
alembic upgrade head
```

## 安全考虑

1. **密码安全**
   - 使用bcrypt哈希，cost factor >= 12
   - 强制密码复杂度要求

2. **Token安全**
   - JWT使用HS256或RS256签名
   - Access Token短期，Refresh Token长期
   - 存储refresh token黑名单（Redis）

3. **API Key安全**
   - 只显示前缀（sk_live_abc...）
   - 哈希后存储完整key
   - 支持撤销和过期

4. **支付安全**
   - 验证回调签名
   - 使用HTTPS
   - 金额校验（防止篡改）
   - 幂等性处理（防止重复支付）

5. **CORS配置**
   - 限制允许的origin
   - 生产环境禁用通配符`*`

## 其他应用接入指南

### 作为Python包使用

```python
# requirements.txt
idoctor-auth-service>=1.0.0
idoctor-payment-service>=1.0.0

# main.py
from fastapi import FastAPI, Depends
from auth_service import AuthService, get_current_user
from payment_service import PaymentService

app = FastAPI()

# 初始化服务
auth_service = AuthService(database_url="postgresql://...")
payment_service = PaymentService(database_url="postgresql://...")

# 注册路由
app.include_router(auth_service.router, prefix="/auth", tags=["auth"])
app.include_router(payment_service.router, prefix="/payments", tags=["payments"])

# 在自己的端点中使用
@app.get("/my-protected-resource")
async def my_endpoint(current_user = Depends(get_current_user)):
    return {"user": current_user.email}
```

### 作为独立服务使用

可以将认证和支付模块部署为独立的微服务，其他应用通过HTTP调用：

```python
# 其他应用中
async def verify_token(token: str):
    response = await httpx.get(
        "http://auth-service:8000/auth/verify",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()
```

## 开发路线图

### Phase 1: 认证模块（Week 1-2）
- [ ] 数据库模型和迁移
- [ ] JWT认证实现
- [ ] API Key认证实现
- [ ] 注册/登录API
- [ ] 用户管理API

### Phase 2: 支付模块（Week 3-4）
- [ ] 数据库模型
- [ ] 订阅计划CRUD
- [ ] 支付宝集成
- [ ] 微信支付集成
- [ ] Stripe集成
- [ ] Webhook处理

### Phase 3: 配额系统（Week 5）
- [ ] 配额检查中间件
- [ ] 使用日志记录
- [ ] 配额重置定时任务
- [ ] 使用统计API

### Phase 4: 集成和测试（Week 6）
- [ ] 集成到现有系统
- [ ] 单元测试
- [ ] 集成测试
- [ ] 文档完善

### Phase 5: 打包发布（Week 7）
- [ ] 打包为可复用Python包
- [ ] Docker镜像
- [ ] 部署文档
- [ ] API文档（Swagger）
