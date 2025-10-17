# iDoctor 商业化模块

通用的认证、支付和配额管理系统，可复用于多个应用。

## 端口分配

```
API网关：        9000  (统一入口，可选)
认证服务：       9001
支付服务：       9002
iDoctor后端：   4200  (现有系统)
```

## ⚡ 快速开始

### 方法一：一键启动（推荐）🚀

**前置要求**: 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)

**macOS / Linux:**
```bash
cd commercial
./start.sh
```

**Windows:**
```bash
cd commercial
start.bat
```

就这么简单！30秒后访问：
- 认证服务 API 文档: http://localhost:9001/docs
- 支付服务 API 文档: http://localhost:9002/docs

**常用命令:**
```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

---

### 方法二：传统部署

<details>
<summary>点击展开详细步骤</summary>

#### 1. 安装依赖

```bash
cd commercial
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入数据库和支付配置
```

#### 3. 初始化数据库

```bash
# 创建数据库
createdb idoctor_commercial

# 运行迁移
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head

# 初始化订阅计划
python scripts/seed_plans.py
```

#### 4. 启动服务

**终端1: 启动认证服务**
```bash
cd auth_service
python app.py
```

**终端2: 启动支付服务**
```bash
cd payment_service
python app.py
```

</details>

---

### 方法三：集成到现有应用

```python
# 在 iDoctor-backend/app.py 中
from commercial.auth_service.core.dependencies import get_current_user
from commercial.payment_service.core.quota import consume_quota

@app.post("/process")
async def process(
    user = Depends(get_current_user),
    db = Depends(get_db)
):
    # 检查并扣减配额
    await consume_quota(db, user.id, "dicom_processing", cost=1)
    # 原有业务逻辑...
```

## 目录结构

```
commercial/
├── README.md                # 本文档
├── requirements.txt         # Python 依赖
├── alembic.ini              # 数据库迁移配置
├── .env.example             # 环境变量模板
├── auth_service/            # 认证服务 (JWT, API Key)
├── payment_service/         # 支付服务 (支付宝, 微信)
├── shared/                  # 共享工具模块
├── scripts/                 # 初始化脚本
├── alembic/                 # 数据库迁移
├── docs/                    # 📚 所有文档
│   ├── QUICK_START.md       #   - 快速开始指南
│   ├── DOCKER_GUIDE.md      #   - Docker 详细指南
│   ├── IMPLEMENTATION_GUIDE.md  # - 集成实施指南
│   ├── DELIVERY_SUMMARY.md  #   - 交付总结
│   ├── PROJECT_STATUS.md    #   - 开发进度
│   └── COMPLETION_REPORT.md #   - 完成报告
└── docker/                  # 🐳 Docker 相关
    ├── docker-compose.yml   #   - Docker Compose 配置
    ├── Dockerfile.init      #   - 数据库初始化镜像
    ├── start.sh             #   - macOS/Linux 启动脚本
    ├── start.bat            #   - Windows 启动脚本
    └── .dockerignore        #   - Docker 忽略文件
```

## API文档

启动服务后访问：
- 认证服务: http://localhost:9001/docs
- 支付服务: http://localhost:9002/docs

## 📖 详细文档

查看 `docs/` 目录获取完整文档：

- **[快速开始](docs/QUICK_START.md)** - 30秒快速部署指南
- **[Docker 指南](docs/DOCKER_GUIDE.md)** - Docker 详细使用说明
- **[集成实施](docs/IMPLEMENTATION_GUIDE.md)** - 如何集成到现有项目
- **[交付总结](docs/DELIVERY_SUMMARY.md)** - 系统架构和功能总结
- **[开发进度](docs/PROJECT_STATUS.md)** - 开发状态和进度跟踪
- **[完成报告](docs/COMPLETION_REPORT.md)** - 最终交付清单

## 其他应用接入

### 方式1: 作为Python包引入

```python
from commercial.auth_service.core.dependencies import get_current_user
from commercial.payment_service.core.quota import check_quota

@app.get("/my-resource")
async def my_endpoint(user = Depends(get_current_user)):
    await check_quota(user.id, "resource_type", cost=1)
    return {"message": "success"}
```

### 方式2: 通过HTTP调用独立服务

```python
import httpx

async def verify_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:9001/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

## 许可证

MIT License
