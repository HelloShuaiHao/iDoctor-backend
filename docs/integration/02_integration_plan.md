# 集成实施计划

## 总体策略

采用**渐进式集成**，分阶段实施，每个阶段可独立测试验证。

### 实施原则
1. **最小侵入**: 优先使用中间件和环境变量，减少代码改动
2. **开关控制**: 所有新功能可通过环境变量开关
3. **向后兼容**: 现有功能不受影响，可随时回退
4. **逐步验证**: 每个阶段完成后进行测试

---

## 阶段 1: 基础中间件集成 ⭐ 优先

### 目标
将认证和配额中间件集成到主应用，实现基本的认证和配额检查。

### 实施步骤

#### 1.1 环境配置
```bash
# 创建 .env 文件 (如果不存在)
cp .env.example .env

# 添加以下配置
cat >> .env << EOF

# ============ 商业化系统配置 ============
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/idoctor_commercial

# JWT 配置
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 功能开关 (开发阶段先关闭)
ENABLE_AUTH=false
ENABLE_QUOTA=false

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:7500
EOF
```

#### 1.2 修改 app.py - 导入和配置

在 `app.py` 顶部添加：

```python
# ==================== 商业化系统集成 ====================
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

# 配置开关
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
ENABLE_QUOTA = os.getenv("ENABLE_QUOTA", "false").lower() == "true"

print(f"🔐 认证中间件: {'✅ 启用' if ENABLE_AUTH else '❌ 关闭'}")
print(f"📊 配额中间件: {'✅ 启用' if ENABLE_QUOTA else '❌ 关闭'}")
```

#### 1.3 修改 app.py - 注册中间件

在 `app = FastAPI()` 之后，CORS 配置之前添加：

```python
# ==================== 注册商业化中间件 ====================
if ENABLE_QUOTA:
    # 初始化配额管理器
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        init_quota_manager(database_url)
        print("✅ 配额管理器已初始化")
    else:
        print("⚠️ 未配置 DATABASE_URL，配额功能将不可用")

# 注册中间件 (注意顺序：先认证，再配额)
if ENABLE_AUTH:
    app.middleware("http")(auth_middleware)
    print("✅ 认证中间件已注册")

if ENABLE_QUOTA:
    app.middleware("http")(quota_middleware)
    print("✅ 配额中间件已注册")
```

#### 1.4 修改端点 - 添加 Request 参数

为所有需要配额控制的端点添加 `request: Request` 参数：

```python
from fastapi import Request  # 确保已导入

# 示例 1: process 端点
@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    request: Request,  # 新增
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks
):
    # 获取用户ID
    user_id = getattr(request.state, "user_id", None)
    
    # 现有逻辑保持不变...
    patient_root = _patient_root(patient_name, study_date)
    # ...

# 示例 2: l3_detect 端点
@app.post("/l3_detect/{patient_name}/{study_date}")
async def l3_detect(
    request: Request,  # 新增
    patient_name: str,
    study_date: str
):
    user_id = getattr(request.state, "user_id", None)
    # ...
```

### 测试验证

#### 测试 1: 关闭认证模式（默认）
```bash
export ENABLE_AUTH=false
export ENABLE_QUOTA=false
uvicorn app:app --host 0.0.0.0 --port 4200 --reload

# 测试：直接访问 API
curl -X POST http://localhost:4200/process/TestPatient/20250101
# 预期：正常工作，无需认证
```

#### 测试 2: 启用认证模式
```bash
# 1. 启动认证服务
cd commercial/auth_service
python app.py  # 运行在 9001 端口

# 2. 启动主应用（启用认证）
export ENABLE_AUTH=true
uvicorn app:app --host 0.0.0.0 --port 4200 --reload

# 3. 测试未认证访问
curl -X POST http://localhost:4200/process/TestPatient/20250101
# 预期：401 Unauthorized

# 4. 注册用户
curl -X POST http://localhost:9001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'

# 5. 登录获取 token
TOKEN=$(curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "password123"
  }' | jq -r '.access_token')

# 6. 使用 token 访问
curl -X POST http://localhost:4200/process/TestPatient/20250101 \
  -H "Authorization: Bearer $TOKEN"
# 预期：认证通过，正常处理
```

### 成功标准
- ✅ 关闭认证时，API 正常工作
- ✅ 启用认证后，无 token 返回 401
- ✅ 提供有效 token 后，API 正常工作
- ✅ request.state.user_id 能正确获取

---

## 阶段 2: 数据库初始化 ⭐ 关键

### 目标
初始化数据库表和基础数据（配额类型、订阅计划）。

### 实施步骤

#### 2.1 检查数据库表
```bash
# 连接数据库
psql -U postgres -d idoctor_commercial

# 检查表是否存在
\dt

# 查看 quota_types 表
SELECT * FROM quota_types WHERE app_id = 'idoctor';
```

#### 2.2 创建配额类型初始化脚本

创建 `commercial/scripts/init_idoctor_quotas.py`:

```python
"""初始化 iDoctor 应用的配额类型"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from commercial.shared.database import Base

# iDoctor 配额类型定义
IDOCTOR_QUOTA_TYPES = [
    {
        "app_id": "idoctor",
        "type_key": "api_calls_l3_detect",
        "name": "L3椎骨检测次数",
        "unit": "次",
        "window": "monthly",
        "description": "每月可调用 /l3_detect 端点的次数"
    },
    {
        "app_id": "idoctor",
        "type_key": "api_calls_full_process",
        "name": "完整处理次数",
        "unit": "次",
        "window": "monthly",
        "description": "每月可调用 /process 端点的次数"
    },
    {
        "app_id": "idoctor",
        "type_key": "api_calls_continue",
        "name": "续传处理次数",
        "unit": "次",
        "window": "monthly",
        "description": "每月可调用 /continue_after_l3 端点的次数"
    },
    {
        "app_id": "idoctor",
        "type_key": "storage_dicom",
        "name": "DICOM存储空间",
        "unit": "GB",
        "window": "lifetime",
        "description": "可存储的DICOM文件总大小"
    },
    {
        "app_id": "idoctor",
        "type_key": "storage_results",
        "name": "结果存储空间",
        "unit": "GB",
        "window": "lifetime",
        "description": "处理结果的存储空间"
    }
]

async def init_quota_types():
    """初始化配额类型"""
    # 实现逻辑...
    pass

if __name__ == "__main__":
    asyncio.run(init_quota_types())
```

#### 2.3 运行初始化
```bash
cd /Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend
python commercial/scripts/init_idoctor_quotas.py
```

### 测试验证
```bash
# 验证配额类型已创建
psql -U postgres -d idoctor_commercial -c "SELECT * FROM quota_types WHERE app_id = 'idoctor';"
```

---

## 阶段 3: 用户数据隔离

### 目标
根据 user_id 隔离用户数据，确保多租户数据安全。

### 实施步骤

#### 3.1 修改 _patient_root 函数

```python
def _patient_root(patient_name: str, study_date: str, user_id: str = None) -> str:
    """获取患者数据根目录（支持用户隔离）"""
    if user_id and ENABLE_AUTH:
        # 认证模式：数据按用户隔离
        user_data_root = os.path.join(DATA_ROOT, str(user_id))
        os.makedirs(user_data_root, exist_ok=True)
        return os.path.join(user_data_root, f"{patient_name}_{study_date}")
    else:
        # 开发模式：共享数据
        return os.path.join(DATA_ROOT, f"{patient_name}_{study_date}")
```

#### 3.2 修改所有使用 _patient_root 的端点

```python
@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    request: Request,
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks
):
    user_id = getattr(request.state, "user_id", None)
    patient_root = _patient_root(patient_name, study_date, user_id)  # 传入 user_id
    # ...
```

#### 3.3 修改 list_patients 端点

```python
@app.get("/list_patients")
async def list_patients(request: Request):
    """列出患者（支持用户隔离）"""
    user_id = getattr(request.state, "user_id", None)
    
    if user_id and ENABLE_AUTH:
        # 只列出该用户的患者
        user_data_root = os.path.join(DATA_ROOT, str(user_id))
        if not os.path.exists(user_data_root):
            return {"patients": []}
        search_root = user_data_root
    else:
        # 开发模式：列出所有患者
        search_root = DATA_ROOT
    
    # 现有逻辑...
```

### 测试验证
```bash
# 1. 创建两个测试用户
# 2. 分别用两个用户上传数据
# 3. 验证用户A无法看到用户B的数据
```

---

## 阶段 4: 配额扣除和监控

### 目标
实现配额的实际扣除和使用记录。

### 实施步骤

#### 4.1 存储空间配额

在 `upload_dicom_zip` 端点添加：

```python
@app.post("/upload_dicom_zip")
async def upload_dicom_zip(request: Request, file: UploadFile = File(...)):
    user_id = getattr(request.state, "user_id", None)
    
    # 计算文件大小
    file_content = await file.read()
    file_size_gb = len(file_content) / (1024 ** 3)
    
    # 如果启用配额，检查存储空间
    if ENABLE_QUOTA and user_id:
        from commercial.integrations.quota_manager import quota_manager
        
        has_space = await quota_manager.check_quota(
            user_id=user_id,
            quota_type="storage_dicom",
            amount=file_size_gb
        )
        
        if not has_space:
            remaining = await quota_manager.get_remaining_quota(user_id, "storage_dicom")
            return JSONResponse(
                status_code=402,
                content={
                    "error": "存储空间不足",
                    "remaining_gb": round(remaining, 2)
                }
            )
    
    # 保存文件...
    
    # 扣除配额
    if ENABLE_QUOTA and user_id:
        await quota_manager.consume_quota(
            user_id=user_id,
            quota_type="storage_dicom",
            amount=file_size_gb
        )
```

---

## 阶段 5: 生产环境部署

### 目标
在生产环境安全部署商业化系统。

### 实施步骤

1. **配置生产数据库**
2. **设置强 JWT 密钥**
3. **配置 HTTPS**
4. **设置监控和日志**

---

## 回滚计划

如果集成出现问题，可快速回滚：

```bash
# 1. 关闭所有商业化功能
export ENABLE_AUTH=false
export ENABLE_QUOTA=false

# 2. 重启应用
uvicorn app:app --host 0.0.0.0 --port 4200

# 现有功能完全不受影响
```

---

## 时间估算

| 阶段 | 预计时间 | 优先级 |
|------|---------|-------|
| 阶段 1: 基础集成 | 2-3小时 | ⭐⭐⭐ |
| 阶段 2: 数据库初始化 | 1-2小时 | ⭐⭐⭐ |
| 阶段 3: 用户数据隔离 | 2-3小时 | ⭐⭐ |
| 阶段 4: 配额扣除监控 | 3-4小时 | ⭐⭐ |
| 阶段 5: 生产部署 | 2小时 | ⭐ |

**总计**: 10-14小时

---

**创建时间**: 2025-10-17  
**下一步**: 开始阶段 1 实施，参考 `03_status.md` 跟踪进度
