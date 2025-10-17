# 商业化系统集成设计

## 概述

本文档说明如何将认证和配额管理系统集成到现有的 iDoctor 医疗影像处理后台。

## 现有系统分析

### 主应用 (app.py)
- **端口**: 4200
- **框架**: FastAPI
- **主要功能**: CT扫描L3椎骨检测和肌肉分割

### 核心 API 端点

#### 需要配额控制的端点

| 端点 | 方法 | 功能 | 配额类型 |
|------|------|------|---------|
| `/process/{patient}/{date}` | POST | 完整处理流程 | API调用次数 + 存储空间 |
| `/l3_detect/{patient}/{date}` | POST | L3椎骨检测 | API调用次数 |
| `/continue_after_l3/{patient}/{date}` | POST | L3后续处理 | API调用次数 |
| `/upload_dicom_zip` | POST | 上传DICOM文件 | 存储空间 |
| `/upload_l3_mask/{patient}/{date}` | POST | 上传L3遮罩 | 存储空间 |

#### 无需认证的端点

| 端点 | 方法 | 功能 | 说明 |
|------|------|------|------|
| `/list_patients` | GET | 列出患者 | 需用户自己的数据 |
| `/get_key_results/{patient}/{date}` | GET | 获取结果 | 需用户自己的数据 |
| `/get_image/{patient}/{date}/{filename}` | GET | 获取图片 | 需用户自己的数据 |
| `/task_status/{task_id}` | GET | 任务状态 | 轮询接口 |

---

## 集成架构

### 1. 配额类型设计（灵活多应用）

```python
# 为 iDoctor 医疗影像应用定义的配额类型
IDOCTOR_QUOTA_TYPES = {
    # API 调用配额
    "api_calls_l3_detect": {
        "name": "L3椎骨检测次数",
        "unit": "次",
        "description": "调用 /l3_detect 端点的次数",
        "window": "monthly"  # 每月重置
    },
    "api_calls_full_process": {
        "name": "完整处理次数",
        "unit": "次",
        "description": "调用 /process 端点的完整处理流程次数",
        "window": "monthly"
    },
    "api_calls_continue": {
        "name": "续传处理次数",
        "unit": "次",
        "description": "调用 /continue_after_l3 端点的次数",
        "window": "monthly"
    },

    # 存储空间配额
    "storage_dicom": {
        "name": "DICOM存储空间",
        "unit": "GB",
        "description": "可存储的DICOM文件总大小",
        "window": "lifetime"  # 终身累计
    },
    "storage_results": {
        "name": "结果存储空间",
        "unit": "GB",
        "description": "处理结果（图片+CSV）的存储空间",
        "window": "lifetime"
    },

    # 患者案例配额
    "patient_cases": {
        "name": "患者案例数量",
        "unit": "个",
        "description": "可处理的不同患者案例数量",
        "window": "monthly"
    }
}
```

### 2. 订阅计划示例

```python
# 免费版
FREE_PLAN = {
    "name": "免费版",
    "price": 0,
    "quotas": {
        "api_calls_l3_detect": 10,      # 每月10次L3检测
        "api_calls_full_process": 5,     # 每月5次完整处理
        "api_calls_continue": 10,        # 每月10次续传
        "storage_dicom": 1,              # 1GB DICOM存储
        "storage_results": 0.5,          # 500MB结果存储
        "patient_cases": 10              # 每月10个患者案例
    }
}

# 专业版
PRO_PLAN = {
    "name": "专业版",
    "price": 299,
    "billing_cycle": "monthly",
    "quotas": {
        "api_calls_l3_detect": 100,
        "api_calls_full_process": 50,
        "api_calls_continue": 100,
        "storage_dicom": 10,
        "storage_results": 5,
        "patient_cases": 100
    }
}

# 企业版
ENTERPRISE_PLAN = {
    "name": "企业版",
    "price": 2999,
    "billing_cycle": "yearly",
    "quotas": {
        "api_calls_l3_detect": -1,    # -1 表示无限制
        "api_calls_full_process": -1,
        "api_calls_continue": -1,
        "storage_dicom": 100,
        "storage_results": 50,
        "patient_cases": -1
    }
}
```

### 3. 中间件设计

#### 3.1 认证中间件 (auth_middleware.py)

```python
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from commercial.auth_service.core.jwt import decode_access_token
from commercial.shared.database import get_db

security = HTTPBearer(auto_error=False)

# 无需认证的路径（健康检查、文档等）
EXEMPT_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health"
]

async def auth_middleware(request: Request, call_next):
    """JWT认证中间件"""
    path = request.url.path

    # 跳过免认证路径
    if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
        return await call_next(request)

    # 提取 Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证"
        )

    token = auth_header.split(" ")[1]

    try:
        # 验证 JWT
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌"
            )

        # 将用户信息注入request.state
        request.state.user_id = user_id
        request.state.user_email = payload.get("email")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )

    return await call_next(request)
```

#### 3.2 配额中间件 (quota_middleware.py)

```python
from fastapi import Request, HTTPException, status
from commercial.quota_service.quota_manager import QuotaManager

# 端点与配额类型的映射
ENDPOINT_QUOTA_MAP = {
    "/process/{patient_name}/{study_date}": "api_calls_full_process",
    "/l3_detect/{patient_name}/{study_date}": "api_calls_l3_detect",
    "/continue_after_l3/{patient_name}/{study_date}": "api_calls_continue",
}

quota_manager = QuotaManager(db_url=settings.DATABASE_URL)

async def quota_middleware(request: Request, call_next):
    """配额检查中间件"""

    # 只检查 POST 请求（消耗性操作）
    if request.method != "POST":
        return await call_next(request)

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # 未认证用户已被 auth_middleware 拦截
        return await call_next(request)

    # 确定配额类型
    path_template = _get_path_template(request.url.path)
    quota_type = ENDPOINT_QUOTA_MAP.get(path_template)

    if not quota_type:
        # 该端点不需要配额检查
        return await call_next(request)

    # 检查配额
    try:
        has_quota = await quota_manager.check_quota(
            user_id=user_id,
            quota_type=quota_type,
            amount=1
        )

        if not has_quota:
            remaining = await quota_manager.get_remaining_quota(user_id, quota_type)
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"配额已用尽。剩余: {remaining}，请升级订阅"
            )

        # 执行请求
        response = await call_next(request)

        # 请求成功后扣除配额
        await quota_manager.consume_quota(
            user_id=user_id,
            quota_type=quota_type,
            amount=1
        )

        # 添加配额信息到响应头
        remaining_after = await quota_manager.get_remaining_quota(user_id, quota_type)
        response.headers["X-Quota-Remaining"] = str(remaining_after)

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配额检查失败: {str(e)}"
        )

def _get_path_template(path: str):
    """将实际路径转换为模板路径"""
    # /process/John_Doe/20250101 -> /process/{patient_name}/{study_date}
    parts = path.split("/")
    if len(parts) >= 4 and parts[1] in ["process", "l3_detect", "continue_after_l3"]:
        return f"/{parts[1]}/{{patient_name}}/{{study_date}}"
    return path
```

### 4. 存储空间配额检查

```python
# 在 upload_dicom_zip 中添加
async def upload_dicom_zip(...):
    # ... 现有代码 ...

    user_id = request.state.user_id
    file_size_gb = file_size / (1024 ** 3)  # 转换为GB

    # 检查存储空间配额
    has_space = await quota_manager.check_quota(
        user_id=user_id,
        quota_type="storage_dicom",
        amount=file_size_gb
    )

    if not has_space:
        remaining_gb = await quota_manager.get_remaining_quota(user_id, "storage_dicom")
        return {
            "status": "quota_exceeded",
            "message": f"存储空间不足。剩余: {remaining_gb:.2f}GB"
        }

    # ... 继续上传逻辑 ...

    # 上传成功后扣除配额
    await quota_manager.consume_quota(
        user_id=user_id,
        quota_type="storage_dicom",
        amount=file_size_gb
    )
```

---

## 集成步骤

### Step 1: 添加依赖

```bash
cd /Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend

# 安装商业化系统依赖
pip install -r commercial/requirements.txt
```

### Step 2: 配置环境变量

在主项目根目录创建 `.env`:

```bash
# 数据库配置（与 commercial 共享）
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/idoctor_commercial

# JWT配置
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256

# 启用认证（开发时可设为false）
ENABLE_AUTH=true
ENABLE_QUOTA=true
```

### Step 3: 修改 app.py

```python
# 在 app.py 顶部添加
import os
from dotenv import load_dotenv

load_dotenv()  # 加载环境变量

# 导入中间件
from commercial.integrations.middleware.auth_middleware import auth_middleware
from commercial.integrations.middleware.quota_middleware import quota_middleware

# 配置开关
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
ENABLE_QUOTA = os.getenv("ENABLE_QUOTA", "false").lower() == "true"

# 注册中间件
if ENABLE_AUTH:
    app.middleware("http")(auth_middleware)
    print("✅ 认证中间件已启用")

if ENABLE_QUOTA:
    app.middleware("http")(quota_middleware)
    print("✅ 配额中间件已启用")
```

### Step 4: 用户数据隔离

```python
# 修改 _patient_root 函数，添加用户隔离
def _patient_root(patient_name: str, study_date: str, user_id: str = None):
    if user_id and ENABLE_AUTH:
        # 启用认证时，数据按用户隔离
        return os.path.join(DATA_ROOT, user_id, f"{patient_name}_{study_date}")
    else:
        # 开发模式，共享数据
        return os.path.join(DATA_ROOT, f"{patient_name}_{study_date}")

# 所有端点添加 user_id 参数
@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    request: Request,
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks
):
    user_id = getattr(request.state, "user_id", None)
    # ... 使用 user_id ...
```

---

## 数据库表结构

### 核心表

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 订阅计划表
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    billing_cycle VARCHAR(20),  -- monthly/yearly/one_time
    quota_limit INTEGER,
    features JSONB
);

-- 用户订阅表
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    plan_id UUID REFERENCES subscription_plans(id),
    status VARCHAR(20),  -- active/expired/cancelled
    start_date TIMESTAMP,
    end_date TIMESTAMP
);

-- 配额定义表（灵活配置）
CREATE TABLE quota_types (
    id UUID PRIMARY KEY,
    app_id VARCHAR(50),  -- 'idoctor_imaging'
    type_key VARCHAR(100),  -- 'api_calls_full_process'
    name VARCHAR(200),
    unit VARCHAR(20),
    window VARCHAR(20),  -- monthly/yearly/lifetime
    description TEXT
);

-- 用户配额表
CREATE TABLE quota_limits (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    quota_type_id UUID REFERENCES quota_types(id),
    limit_amount DECIMAL(10, 2),
    used_amount DECIMAL(10, 2) DEFAULT 0
);

-- 使用记录表
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    quota_type_id UUID REFERENCES quota_types(id),
    amount DECIMAL(10, 2),
    endpoint VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 前端集成

### 登录流程

```typescript
// 1. 用户登录
const response = await fetch('http://localhost:9001/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username_or_email: 'user@example.com',
    password: 'password123'
  })
});

const { access_token } = await response.json();
localStorage.setItem('auth_token', access_token);

// 2. 调用主应用API（带token）
const result = await fetch('http://localhost:4200/process/John/20250101', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});

// 3. 检查配额（从响应头）
const remainingQuota = result.headers.get('X-Quota-Remaining');
console.log(`剩余配额: ${remainingQuota}`);
```

---

## 测试计划

### 1. 单元测试

```bash
# 测试认证中间件
pytest commercial/tests/test_auth_middleware.py

# 测试配额中间件
pytest commercial/tests/test_quota_middleware.py
```

### 2. 集成测试

```python
# test_integration.py
import pytest
from fastapi.testclient import TestClient

def test_authenticated_request():
    client = TestClient(app)

    # 登录获取token
    login_response = client.post("/auth/login", json={
        "username_or_email": "testuser",
        "password": "password123"
    })
    token = login_response.json()["access_token"]

    # 调用受保护的端点
    response = client.post(
        "/process/TestPatient/20250101",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

def test_quota_exceeded():
    # ... 模拟配额用尽场景 ...
    response = client.post("/process/TestPatient/20250101", ...)
    assert response.status_code == 402  # Payment Required
```

---

## 性能考虑

### 1. 配额查询优化

- 使用 Redis 缓存用户配额信息
- 每次查询先查缓存，避免频繁数据库访问

### 2. 数据库连接池

```python
# commercial/shared/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # 连接池大小
    max_overflow=10,     # 最大溢出连接
    pool_pre_ping=True   # 连接前检查
)
```

### 3. 异步处理

- 认证验证：异步JWT验证
- 配额检查：异步数据库查询
- 使用记录：异步写入（不阻塞主请求）

---

## 灵活扩展

### 为其他应用添加配额

```python
# 假设要支持另一个 AI 应用
OTHER_APP_QUOTA_TYPES = {
    "ai_text_generation": {
        "name": "AI文本生成次数",
        "unit": "次",
        "window": "monthly"
    },
    "ai_image_generation": {
        "name": "AI图像生成次数",
        "unit": "次",
        "window": "monthly"
    }
}

# 在 quota_types 表中添加记录
await quota_manager.register_quota_types(
    app_id="ai_text_app",
    quota_types=OTHER_APP_QUOTA_TYPES
)
```

### 多应用共享用户系统

```
User Table (共享)
    ├── iDoctor Imaging 应用 (quota_types: api_calls_full_process, storage_dicom)
    ├── AI Text Generator 应用 (quota_types: ai_text_generation)
    └── AI Image Generator 应用 (quota_types: ai_image_generation)
```

---

## 总结

通过以上设计，我们实现了：

1. ✅ **灵活的配额系统** - 支持多种配额类型（API调用、存储、案例数）
2. ✅ **多应用支持** - 一套认证系统支持多个应用
3. ✅ **用户数据隔离** - 每个用户的患者数据独立存储
4. ✅ **最小侵入性** - 通过中间件集成，原有代码改动最小
5. ✅ **可配置开关** - 开发时可关闭认证，生产环境启用
6. ✅ **性能优化** - 异步处理、连接池、Redis缓存

**下一步**: 开始实现中间件代码和数据库初始化脚本。
