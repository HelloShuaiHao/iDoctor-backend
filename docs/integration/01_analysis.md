# 当前系统分析

## 1. 主应用架构

### 基本信息
- **位置**: `/Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend/app.py`
- **框架**: FastAPI
- **端口**: 4200
- **运行方式**: uvicorn
- **主要功能**: CT扫描医疗影像处理

### 核心端点分析

#### 需要配额控制的端点

| 端点 | 方法 | 功能 | 建议配额类型 | 扣除量 |
|------|------|------|------------|--------|
| `/process/{patient}/{date}` | POST | 完整处理流程 | `api_calls_full_process` | 1次 |
| `/l3_detect/{patient}/{date}` | POST | L3椎骨检测 | `api_calls_l3_detect` | 1次 |
| `/continue_after_l3/{patient}/{date}` | POST | L3后续处理 | `api_calls_continue` | 1次 |
| `/upload_dicom_zip` | POST | 上传DICOM | `storage_dicom` | 文件大小(GB) |
| `/upload_l3_mask/{patient}/{date}` | POST | 上传L3遮罩 | `storage_results` | 文件大小(GB) |

#### 需要认证但不计费的端点

| 端点 | 方法 | 功能 | 说明 |
|------|------|------|------|
| `/list_patients` | GET | 列出患者 | 需用户数据隔离 |
| `/get_key_results/{patient}/{date}` | GET | 获取结果 | 需用户数据隔离 |
| `/get_image/{patient}/{date}/{filename}` | GET | 获取图片 | 需用户数据隔离 |
| `/task_status/{task_id}` | GET | 任务状态 | 高频轮询接口 |

#### 无需认证的端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 健康检查 |
| `/docs` | GET | API文档 |
| `/openapi.json` | GET | OpenAPI规范 |

## 2. Commercial 系统架构

### 目录结构
```
commercial/
├── integrations/              # 集成组件
│   ├── middleware/
│   │   ├── auth_middleware.py    # ✅ 认证中间件
│   │   └── quota_middleware.py   # ✅ 配额中间件
│   ├── quota_manager.py          # ✅ 配额管理器
│   └── README.md                 # 集成指南
├── auth_service/              # 认证服务 (端口 9001)
│   ├── api/
│   │   ├── auth.py              # 登录/注册
│   │   └── users.py             # 用户管理
│   └── core/
│       ├── security.py          # 密码哈希
│       └── jwt.py               # JWT生成/验证
├── payment_service/           # 支付服务 (端口 9002)
└── shared/                    # 共享组件
    ├── database.py            # 数据库连接
    └── config.py              # 配置管理
```

### 数据库表结构
```sql
users                  -- 用户表
user_subscriptions     -- 用户订阅
subscription_plans     -- 订阅计划
quota_types            -- 配额类型定义 (灵活配置)
quota_limits           -- 用户配额限制
usage_logs             -- 使用记录日志
```

## 3. 集成要点

### 3.1 认证流程
```
前端请求
  ↓
Authorization: Bearer <JWT>
  ↓
auth_middleware 验证 JWT
  ↓
提取 user_id → request.state.user_id
  ↓
quota_middleware 检查配额
  ↓
主应用处理
  ↓
扣除配额 + 记录日志
  ↓
返回响应 (含剩余配额信息)
```

### 3.2 配额类型设计（iDoctor 应用）

```python
IDOCTOR_QUOTA_TYPES = {
    # API 调用
    "api_calls_l3_detect": {
        "name": "L3椎骨检测",
        "unit": "次",
        "window": "monthly"
    },
    "api_calls_full_process": {
        "name": "完整处理",
        "unit": "次",
        "window": "monthly"
    },
    
    # 存储空间
    "storage_dicom": {
        "name": "DICOM存储",
        "unit": "GB",
        "window": "lifetime"
    },
    
    # AI分析
    "ai_analysis_l3_detection": {
        "name": "L3检测分析",
        "unit": "次",
        "window": "monthly"
    },
    "ai_analysis_muscle_segmentation": {
        "name": "肌肉分割分析",
        "unit": "次",
        "window": "monthly"
    }
}
```

### 3.3 订阅计划示例

#### 免费版
- L3检测: 10次/月
- 完整处理: 5次/月
- 存储: 1GB

#### 专业版 (¥299/月)
- L3检测: 100次/月
- 完整处理: 50次/月
- 存储: 10GB

#### 企业版 (¥2999/年)
- 无限次数
- 存储: 100GB

## 4. 集成挑战

### 4.1 需要解决的问题
1. ✅ 中间件已实现，需要集成到 `app.py`
2. ⚠️ 数据库初始化脚本（配额类型、默认计划）
3. ⚠️ 用户数据隔离逻辑（按 `user_id` 组织文件）
4. ⚠️ 存储空间计算和扣除
5. ⚠️ AI分析次数统计
6. ⚠️ 内存使用监控

### 4.2 改动点清单

#### app.py 需要修改的地方
1. **导入中间件**
   ```python
   from commercial.integrations.middleware import auth_middleware, quota_middleware
   from commercial.integrations.quota_manager import init_quota_manager
   ```

2. **注册中间件** (在 `app = FastAPI()` 之后)
   ```python
   ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
   ENABLE_QUOTA = os.getenv("ENABLE_QUOTA", "false").lower() == "true"
   
   if ENABLE_AUTH:
       app.middleware("http")(auth_middleware)
   if ENABLE_QUOTA:
       init_quota_manager(settings.DATABASE_URL)
       app.middleware("http")(quota_middleware)
   ```

3. **所有端点添加 `request: Request` 参数**
   ```python
   @app.post("/process/{patient_name}/{study_date}")
   async def process_case(
       request: Request,  # 新增
       patient_name: str,
       study_date: str,
       background_tasks: BackgroundTasks
   ):
       user_id = getattr(request.state, "user_id", None)
       # 使用 user_id 构建数据路径
   ```

4. **修改数据路径逻辑**
   ```python
   def _patient_root(patient_name: str, study_date: str, user_id: str = None):
       if user_id and ENABLE_AUTH:
           return os.path.join(DATA_ROOT, user_id, f"{patient_name}_{study_date}")
       return os.path.join(DATA_ROOT, f"{patient_name}_{study_date}")
   ```

### 4.3 环境变量配置

需要在 `.env` 中添加：
```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/idoctor_commercial

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256

# 功能开关
ENABLE_AUTH=true
ENABLE_QUOTA=true

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:7500
```

## 5. 下一步

### 优先级 1: 基础集成
- [ ] 在 `app.py` 添加中间件
- [ ] 测试认证流程
- [ ] 测试配额检查

### 优先级 2: 数据库初始化
- [ ] 创建配额类型记录
- [ ] 创建默认订阅计划
- [ ] 创建测试用户

### 优先级 3: 用户数据隔离
- [ ] 修改文件路径逻辑
- [ ] 修改 `list_patients` 端点
- [ ] 修改 `get_key_results` 端点

### 优先级 4: 存储和AI监控
- [ ] 文件上传时计算大小
- [ ] AI分析调用记录
- [ ] 内存使用监控

---

**分析完成时间**: 2025-10-17  
**下一步**: 查看 `02_integration_plan.md`
