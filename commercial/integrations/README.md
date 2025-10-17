# 商业化系统集成指南

本目录包含将认证和配额系统集成到主应用的所有组件。

## 📁 目录结构

```
integrations/
├── __init__.py
├── README.md                    # 本文件
├── quota_manager.py             # 配额管理器（数据库操作）
└── middleware/
    ├── __init__.py
    ├── auth_middleware.py       # JWT认证中间件
    └── quota_middleware.py      # 配额检查中间件
```

## 🚀 一键启动集成

### 🎯 最简单方式（推荐）

```bash
# 1. 在项目根目录启动商业化系统
cd commercial && ./start.sh

# 2. 等待启动完成后，启动您的主应用即可！
# 认证和配额功能将自动生效
```

### Step 1: 在主应用 app.py 中添加以下代码（如需手动集成）

```python
# ==================== 在文件顶部添加 ====================
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入中间件
from commercial.integrations.middleware.auth_middleware import auth_middleware
from commercial.integrations.middleware.quota_middleware import (
    quota_middleware,
    init_quota_manager
)
from commercial.shared.config import settings

# ==================== 在创建 FastAPI app 后添加 ====================

# 配置开关
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
ENABLE_QUOTA = os.getenv("ENABLE_QUOTA", "false").lower() == "true"

# 初始化配额管理器
if ENABLE_QUOTA:
    init_quota_manager(settings.DATABASE_URL)
    print("✅ 配额管理器已初始化")

# 注册中间件（注意顺序：先认证，再配额）
if ENABLE_AUTH:
    app.middleware("http")(auth_middleware)
    print("✅ 认证中间件已启用")

if ENABLE_QUOTA:
    app.middleware("http")(quota_middleware)
    print("✅ 配额中间件已启用")

# ==================== 可选：添加用户数据隔离 ====================

# 修改 _patient_root 函数
def _patient_root(patient_name: str, study_date: str):
    \"\"\"获取患者数据根目录（支持用户隔离）\"\"\"
    if ENABLE_AUTH and hasattr(request.state, "user_id"):
        # 启用认证时，数据按用户隔离
        user_id = request.state.user_id
        return os.path.join(DATA_ROOT, str(user_id), f"{patient_name}_{study_date}")
    else:
        # 开发模式，共享数据
        return os.path.join(DATA_ROOT, f"{patient_name}_{study_date}")

# ==================== 所有端点添加 Request 参数 ====================

@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    request: Request,  # 添加这个参数
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks
):
    # 获取用户ID（如果启用了认证）
    user_id = getattr(request.state, "user_id", None)

    # 使用 user_id 构建数据路径
    if user_id and ENABLE_AUTH:
        folder_name = f"{user_id}/{patient_name}_{study_date}"
    else:
        folder_name = f"{patient_name}_{study_date}"

    patient_root = os.path.join(DATA_ROOT, folder_name)
    # ... 其余逻辑不变 ...
```

### Step 2: 配置环境变量

在主项目根目录创建 `.env` 文件：

```bash
# 数据库配置（与 commercial 共享）
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/idoctor_commercial

# JWT配置
JWT_SECRET_KEY=your-super-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 认证和配额开关
ENABLE_AUTH=true   # 开发时可设为 false
ENABLE_QUOTA=true  # 开发时可设为 false

# CORS配置（添加前端地址）
CORS_ORIGINS=http://localhost:3000,http://localhost:7500
```

### Step 3: 安装依赖

```bash
cd /path/to/iDoctor-backend
pip install python-dotenv
pip install -r commercial/requirements.txt
```

### Step 4: 初始化数据库

```bash
# 创建数据库
createdb idoctor_commercial

# 运行初始化脚本（见后续章节）
python commercial/scripts/init_database.py
```

### Step 5: 测试集成

```bash
# 1. 启动认证服务（另一个终端）
cd commercial/auth_service
python app.py

# 2. 启动主应用（启用认证）
export ENABLE_AUTH=true
export ENABLE_QUOTA=true
uvicorn app:app --host 0.0.0.0 --port 4200

# 3. 测试认证流程
# 注册用户
curl -X POST http://localhost:9001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'

# 登录获取token
curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "password123"
  }'

# 使用token调用主应用API
TOKEN="<从登录响应中复制access_token>"

curl -X POST http://localhost:4200/process/TestPatient/20250101 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 高级配置

### 1. 自定义免认证路径

```python
from commercial.integrations.middleware.auth_middleware import add_exempt_path

# 添加无需认证的路径
add_exempt_path("/public/data")
add_exempt_path("/health_check")
```

### 2. 自定义配额映射

```python
from commercial.integrations.middleware.quota_middleware import add_endpoint_quota

# 为新端点添加配额
add_endpoint_quota(
    template="/analyze_image/{image_id}",
    quota_type="api_calls_image_analysis",
    amount=1,
    description="图像分析"
)
```

### 3. 禁用特定端点的配额检查

```python
# 在 quota_middleware.py 的 EXEMPT_PATHS 中添加
EXEMPT_PATHS.add("/generate_preview")
```

---

## 📊 监控和调试

### 查看用户配额

```python
# 在端点中获取用户配额信息
from commercial.integrations.quota_manager import QuotaManager

quota_manager = QuotaManager(settings.DATABASE_URL)

@app.get("/my_quota")
async def get_my_quota(request: Request):
    user_id = request.state.user_id
    quotas = await quota_manager.get_all_quotas(user_id)
    return quotas
```

### 日志输出

中间件会自动记录以下日志：
- 认证成功/失败
- 配额检查结果
- 配额扣除记录

查看日志：
```bash
tail -f logs/app.log | grep -E "(Authenticated|Quota)"
```

---

## ❓ 常见问题

### Q1: 如何在开发时跳过认证？

A: 设置环境变量：
```bash
export ENABLE_AUTH=false
export ENABLE_QUOTA=false
uvicorn app:app --reload
```

### Q2: 认证通过但配额检查失败？

A: 检查数据库中是否为用户分配了配额：
```sql
SELECT * FROM quota_limits WHERE user_id = '<user_id>';
```

如果没有记录，运行初始化脚本创建默认配额。

### Q3: 如何为现有用户添加配额？

A:
```python
# 使用初始化脚本
python commercial/scripts/assign_default_quota.py --user-id <uuid>
```

### Q4: 中间件顺序重要吗？

A: **非常重要！** 必须先注册认证中间件，再注册配额中间件。因为配额中间件依赖 `request.state.user_id`。

正确顺序：
```python
app.middleware("http")(auth_middleware)   # 第一个
app.middleware("http")(quota_middleware)  # 第二个
```

---

## 🧪 测试

### 单元测试

```bash
pytest commercial/tests/test_auth_middleware.py
pytest commercial/tests/test_quota_middleware.py
```

### 集成测试

```bash
pytest commercial/tests/test_integration.py -v
```

---

## 📚 相关文档

- [集成设计文档](../docs/INTEGRATION_DESIGN.md) - 详细架构说明
- [集成状态](../docs/INTEGRATION_STATUS.md) - 当前进度
- [数据库初始化](../scripts/README.md) - 数据库设置指南

---

**维护者**: iDoctor Team
**最后更新**: 2025-01-17
