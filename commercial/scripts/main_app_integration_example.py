"""
主应用集成示例代码

复制以下代码到你的主应用 app.py 文件中
"""

# ==================== 在 app.py 文件顶部添加 ====================
import os
from dotenv import load_dotenv
from fastapi import Request

# 加载环境变量
load_dotenv()

# 导入商业化系统中间件
from commercial.integrations.middleware.auth_middleware import auth_middleware
from commercial.integrations.middleware.quota_middleware import (
    quota_middleware,
    init_quota_manager
)
from commercial.shared.config import settings

# ==================== 在创建 FastAPI app 后添加 ====================

# 功能开关
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"
ENABLE_QUOTA = os.getenv("ENABLE_QUOTA", "false").lower() == "true"

print(f"🔐 认证系统: {'启用' if ENABLE_AUTH else '禁用'}")
print(f"📊 配额系统: {'启用' if ENABLE_QUOTA else '禁用'}")

# 初始化配额管理器
if ENABLE_QUOTA:
    try:
        init_quota_manager(settings.DATABASE_URL)
        print("✅ 配额管理器初始化成功")
    except Exception as e:
        print(f"❌ 配额管理器初始化失败: {e}")
        ENABLE_QUOTA = False

# 注册中间件（注意顺序：先认证，再配额）
if ENABLE_AUTH:
    app.middleware("http")(auth_middleware)
    print("✅ 认证中间件已注册")

if ENABLE_QUOTA:
    app.middleware("http")(quota_middleware)
    print("✅ 配额中间件已注册")

# ==================== 修改现有端点，添加 Request 参数 ====================

# 示例：修改处理端点
@app.post("/process/{patient_name}/{study_date}")
async def process_case(
    request: Request,  # 👈 添加此参数
    patient_name: str,
    study_date: str,
    background_tasks: BackgroundTasks
):
    """处理医学影像案例"""
    
    # 获取用户信息（如果启用认证）
    user_id = getattr(request.state, "user_id", None)
    user_email = getattr(request.state, "user_email", None)
    
    # 构建用户相关的数据路径
    if user_id and ENABLE_AUTH:
        # 启用认证时，数据按用户隔离
        folder_name = f"{user_id}/{patient_name}_{study_date}"
        print(f"🔐 用户 {user_email} ({user_id}) 正在处理: {patient_name}_{study_date}")
    else:
        # 开发模式，共享数据
        folder_name = f"{patient_name}_{study_date}"
        print(f"🔓 匿名用户正在处理: {patient_name}_{study_date}")
    
    patient_root = os.path.join(DATA_ROOT, folder_name)
    
    # 确保目录存在
    os.makedirs(patient_root, exist_ok=True)
    
    # 其余业务逻辑保持不变...
    # ...

# ==================== 可选：添加用户状态端点 ====================

@app.get("/user/profile")
async def get_user_profile(request: Request):
    """获取当前用户信息"""
    if not ENABLE_AUTH:
        return {"message": "认证系统未启用"}
    
    if not hasattr(request.state, "user_id"):
        return {"error": "用户未认证"}, 401
    
    return {
        "user_id": request.state.user_id,
        "email": getattr(request.state, "user_email", None),
        "is_superuser": getattr(request.state, "is_superuser", False)
    }

@app.get("/user/quota")
async def get_user_quota(request: Request):
    """获取当前用户配额信息"""
    if not ENABLE_QUOTA:
        return {"message": "配额系统未启用"}
    
    if not hasattr(request.state, "user_id"):
        return {"error": "用户未认证"}, 401
    
    from commercial.integrations.middleware.quota_middleware import get_user_quota_info
    quota_info = await get_user_quota_info(request)
    return quota_info

# ==================== 环境变量配置示例 ====================
"""
在项目根目录创建 .env 文件：

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
"""

# ==================== 启动命令示例 ====================
"""
# 开发模式（禁用认证）
export ENABLE_AUTH=false
export ENABLE_QUOTA=false
uvicorn app:app --reload --host 0.0.0.0 --port 4200

# 生产模式（启用认证和配额）
export ENABLE_AUTH=true
export ENABLE_QUOTA=true
uvicorn app:app --host 0.0.0.0 --port 4200
"""
