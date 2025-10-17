# 商业化模块实施指南

## ✅ 已完成部分（可直接使用）

### 1. 认证服务（100%完成）

**位置**: `commercial/auth_service/`

**功能**:
- ✅ 用户注册/登录
- ✅ JWT Token 认证（Access + Refresh）
- ✅ API Key 管理
- ✅ 用户信息管理
- ✅ 权限控制（普通用户/管理员）

**API端点**:
```
POST   /auth/register          # 注册
POST   /auth/login             # 登录
POST   /auth/refresh           # 刷新token
GET    /users/me               # 获取当前用户
PUT    /users/me               # 更新用户信息
POST   /api-keys/              # 创建API密钥
GET    /api-keys/              # 列出API密钥
DELETE /api-keys/{key_id}      # 删除API密钥
```

**启动方式**:
```bash
cd commercial
cp .env.example .env
# 编辑.env配置数据库
cd auth_service
python app.py  # 端口9001
```

### 2. 数据库模型（100%完成）

**位置**:
- `commercial/auth_service/models/`
- `commercial/payment_service/models/`

**表结构**:
- Users (用户)
- APIKeys (API密钥)
- SubscriptionPlans (订阅计划)
- UserSubscriptions (用户订阅)
- PaymentTransactions (支付交易)
- UsageLogs (使用记录)

### 3. Pydantic模型（100%完成）

**位置**:
- `commercial/auth_service/schemas/`
- `commercial/payment_service/schemas/`

## 🚧 需要完成的部分

### 1. 支付提供商实现

#### 支付宝提供商 (`payment_service/providers/alipay.py`)

```python
"""支付宝支付提供商"""
from decimal import Decimal
from typing import Dict, Any, Optional
from alipay.aop.api.AlipayClient import AlipayClient
from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from .base import PaymentProvider, PaymentStatus, RefundResult


class AlipayProvider(PaymentProvider):
    """支付宝支付提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 初始化支付宝客户端
        self.client = AlipayClient(
            appid=config["app_id"],
            app_notify_url=config.get("notify_url"),
            app_private_key_path=config["private_key_path"],
            alipay_public_key_path=config["public_key_path"],
            sign_type="RSA2",
            debug=config.get("debug", False)
        )

    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "CNY",
        subject: str = "订阅付款",
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建支付宝支付"""
        model = AlipayTradePagePayModel()
        model.out_trade_no = order_id
        model.total_amount = str(amount)
        model.subject = subject
        model.product_code = "FAST_INSTANT_TRADE_PAY"

        request = AlipayTradePagePayRequest(biz_model=model)
        if return_url:
            request.return_url = return_url

        # 获取支付链接
        response = self.client.page_execute(request, http_method="GET")

        return {
            "payment_url": response,
            "order_id": order_id
        }

    async def verify_payment(self, transaction_id: str) -> PaymentStatus:
        """查询支付状态"""
        request = AlipayTradeQueryRequest()
        request.biz_content = {"out_trade_no": transaction_id}

        response = self.client.execute(request)

        if response.get("trade_status") == "TRADE_SUCCESS":
            return PaymentStatus.COMPLETED
        elif response.get("trade_status") == "TRADE_CLOSED":
            return PaymentStatus.FAILED
        else:
            return PaymentStatus.PENDING

    async def verify_webhook(self, request_data: Dict[str, Any]) -> bool:
        """验证支付宝回调签名"""
        # 支付宝SDK会自动验证签名
        return self.client.verify(request_data, request_data.pop("sign"))

    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理支付宝回调"""
        return {
            "order_id": request_data.get("out_trade_no"),
            "transaction_id": request_data.get("trade_no"),
            "status": "completed" if request_data.get("trade_status") == "TRADE_SUCCESS" else "failed",
            "amount": request_data.get("total_amount")
        }

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
        reason: str = "用户申请退款"
    ) -> RefundResult:
        """支付宝退款"""
        from alipay.aop.api.request.AlipayTradeRefundRequest import AlipayTradeRefundRequest

        request = AlipayTradeRefundRequest()
        request.biz_content = {
            "out_trade_no": transaction_id,
            "refund_amount": str(amount),
            "refund_reason": reason
        }

        response = self.client.execute(request)

        if response.get("code") == "10000":
            return RefundResult(
                success=True,
                refund_id=response.get("trade_no"),
                message="退款成功"
            )
        else:
            return RefundResult(
                success=False,
                message=response.get("sub_msg", "退款失败")
            )
```

#### 微信支付提供商 (`payment_service/providers/wechat.py`)

```python
"""微信支付提供商"""
from decimal import Decimal
from typing import Dict, Any, Optional
import time
from wechatpy.pay import WeChatPay
from .base import PaymentProvider, PaymentStatus, RefundResult


class WechatProvider(PaymentProvider):
    """微信支付提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 初始化微信支付客户端
        self.client = WeChatPay(
            appid=config["app_id"],
            mch_id=config["mch_id"],
            api_key=config["api_key"],
            mch_cert=config.get("cert_path"),
            mch_key=config.get("key_path")
        )

    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "CNY",
        subject: str = "订阅付款",
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """创建微信支付（Native扫码支付）"""
        # 金额转换为分
        total_fee = int(amount * 100)

        # 创建统一下单
        result = self.client.order.create(
            trade_type="NATIVE",  # 扫码支付
            body=subject,
            out_trade_no=order_id,
            total_fee=total_fee,
            notify_url=self.config.get("notify_url"),
            client_ip=kwargs.get("client_ip", "127.0.0.1")
        )

        return {
            "qr_code": result["code_url"],  # 二维码链接
            "order_id": order_id
        }

    async def verify_payment(self, transaction_id: str) -> PaymentStatus:
        """查询微信支付状态"""
        result = self.client.order.query(out_trade_no=transaction_id)

        trade_state = result.get("trade_state")

        if trade_state == "SUCCESS":
            return PaymentStatus.COMPLETED
        elif trade_state in ["CLOSED", "REVOKED", "PAYERROR"]:
            return PaymentStatus.FAILED
        else:
            return PaymentStatus.PENDING

    async def verify_webhook(self, request_data: Dict[str, Any]) -> bool:
        """验证微信支付回调签名"""
        return self.client.check_signature(request_data)

    async def handle_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理微信支付回调"""
        # 解析XML数据
        data = self.client.parse_payment_result(request_data)

        return {
            "order_id": data.get("out_trade_no"),
            "transaction_id": data.get("transaction_id"),
            "status": "completed" if data.get("result_code") == "SUCCESS" else "failed",
            "amount": str(Decimal(data.get("total_fee", 0)) / 100)  # 分转元
        }

    async def refund(
        self,
        transaction_id: str,
        amount: Decimal,
        reason: str = "用户申请退款"
    ) -> RefundResult:
        """微信退款"""
        # 金额转换为分
        refund_fee = int(amount * 100)

        try:
            result = self.client.refund.apply(
                out_trade_no=transaction_id,
                out_refund_no=f"refund_{transaction_id}_{int(time.time())}",
                total_fee=refund_fee,
                refund_fee=refund_fee,
                refund_desc=reason
            )

            if result.get("result_code") == "SUCCESS":
                return RefundResult(
                    success=True,
                    refund_id=result.get("refund_id"),
                    message="退款成功"
                )
            else:
                return RefundResult(
                    success=False,
                    message=result.get("err_code_des", "退款失败")
                )
        except Exception as e:
            return RefundResult(
                success=False,
                message=str(e)
            )
```

### 2. 配额管理系统

#### 配额管理核心 (`payment_service/core/quota.py`)

```python
"""配额管理"""
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from commercial.shared.exceptions import QuotaExceededError, ResourceNotFoundError
from ..models.subscription import UserSubscription
from ..models.usage_log import UsageLog


async def check_quota(
    db: AsyncSession,
    user_id: UUID,
    resource_type: str,
    cost: int = 1
) -> UserSubscription:
    """检查配额是否充足（不扣减）"""
    # 获取用户当前有效订阅
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == user_id,
        UserSubscription.status == "active",
        UserSubscription.current_period_end > datetime.utcnow()
    ).order_by(UserSubscription.current_period_start.desc())

    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise ResourceNotFoundError("您还没有订阅，请先购买订阅计划")

    # 检查配额
    if subscription.quota_used + cost > subscription.quota_limit:
        raise QuotaExceededError(
            f"配额不足。已用: {subscription.quota_used}/{subscription.quota_limit}"
        )

    return subscription


async def consume_quota(
    db: AsyncSession,
    user_id: UUID,
    resource_type: str,
    cost: int = 1,
    resource_id: str = None,
    metadata: dict = None
) -> UsageLog:
    """消耗配额并记录日志"""
    # 检查并获取订阅
    subscription = await check_quota(db, user_id, resource_type, cost)

    # 扣减配额
    subscription.quota_used += cost

    # 记录使用日志
    usage_log = UsageLog(
        user_id=user_id,
        subscription_id=subscription.id,
        resource_type=resource_type,
        resource_id=resource_id,
        quota_cost=cost,
        metadata=metadata
    )

    db.add(usage_log)
    await db.commit()
    await db.refresh(usage_log)

    return usage_log
```

#### 配额装饰器 (`payment_service/core/dependencies.py`)

```python
"""支付服务依赖注入"""
from functools import wraps
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from commercial.shared.database import get_db
from commercial.auth_service.core.dependencies import get_current_user
from commercial.auth_service.models.user import User
from .quota import consume_quota


def require_quota(resource_type: str, cost: int = 1):
    """配额检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user和db
            current_user: User = kwargs.get("current_user")
            db: AsyncSession = kwargs.get("db")

            if not current_user or not db:
                raise ValueError("缺少current_user或db参数")

            # 消耗配额
            await consume_quota(
                db=db,
                user_id=current_user.id,
                resource_type=resource_type,
                cost=cost
            )

            # 执行原函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator
```

### 3. Alembic 数据库迁移配置

#### 配置文件 (`commercial/alembic.ini`)

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

#### 迁移环境 (`commercial/alembic/env.py`)

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from commercial.shared.config import settings
from commercial.shared.database import Base

# 导入所有模型
from commercial.auth_service.models import User, APIKey
from commercial.payment_service.models import (
    SubscriptionPlan, UserSubscription, PaymentTransaction, UsageLog
)

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4. 初始化脚本

#### 初始化订阅计划 (`commercial/scripts/seed_plans.py`)

```python
"""初始化订阅计划"""
import asyncio
from decimal import Decimal
from commercial.shared.database import AsyncSessionLocal
from commercial.payment_service.models.plan import SubscriptionPlan


async def seed_plans():
    """创建默认订阅计划"""
    plans = [
        {
            "name": "免费版",
            "description": "适合个人用户试用",
            "price": Decimal("0.00"),
            "currency": "CNY",
            "billing_cycle": "monthly",
            "quota_type": "processing_count",
            "quota_limit": 10,
            "features": {"max_concurrent": 1, "priority": "low"}
        },
        {
            "name": "专业版",
            "description": "适合小型团队",
            "price": Decimal("99.00"),
            "currency": "CNY",
            "billing_cycle": "monthly",
            "quota_type": "processing_count",
            "quota_limit": 100,
            "features": {"max_concurrent": 3, "priority": "medium"}
        },
        {
            "name": "企业版",
            "description": "无限制使用",
            "price": Decimal("999.00"),
            "currency": "CNY",
            "billing_cycle": "monthly",
            "quota_type": "processing_count",
            "quota_limit": 999999,
            "features": {"max_concurrent": 10, "priority": "high", "custom_support": True}
        }
    ]

    async with AsyncSessionLocal() as db:
        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)

        await db.commit()
        print("✅ 订阅计划初始化完成")


if __name__ == "__main__":
    asyncio.run(seed_plans())
```

## 📖 完整使用流程

### 1. 安装和配置

```bash
# 1. 安装依赖
cd commercial
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
nano .env  # 配置数据库和支付密钥

# 3. 创建数据库
createdb idoctor_commercial

# 4. 运行迁移
alembic upgrade head

# 5. 初始化订阅计划
python scripts/seed_plans.py
```

### 2. 启动服务

```bash
# 终端1: 认证服务
cd auth_service
python app.py  # 端口9001

# 终端2: 支付服务（完成后）
cd payment_service
python app.py  # 端口9002
```

### 3. 集成到现有系统

在 `iDoctor-backend/app.py` 中：

```python
from commercial.auth_service.core.dependencies import get_current_user
from commercial.payment_service.core.quota import consume_quota

@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),  # 添加认证
    db: AsyncSession = Depends(get_db)
):
    # 检查并消耗配额
    await consume_quota(
        db=db,
        user_id=current_user.id,
        resource_type="dicom_processing",
        cost=1,
        resource_id=f"{patient_name}_{study_date}"
    )

    # 原有处理逻辑...
    task_id = f"main_{patient_name}_{study_date}"
    # ...
```

## 🎯 下一步行动

1. **完成支付提供商实现**（复制上面的代码到对应文件）
2. **完成配额管理**（复制上面的代码）
3. **配置Alembic**（复制配置文件）
4. **运行数据库迁移**
5. **测试支付流程**（需要支付宝/微信沙箱环境）
6. **集成到主应用**

## 💬 需要帮助？

告诉我您需要：
- 继续完成剩余代码实现
- 测试指导
- 部署帮助
- 其他定制需求
