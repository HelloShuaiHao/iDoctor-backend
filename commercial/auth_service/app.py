"""认证服务 FastAPI 应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from commercial.shared.config import settings
from commercial.shared.database import init_db
from .api import auth, users, api_keys

# 创建应用
app = FastAPI(
    title="iDoctor 认证服务",
    description="通用认证服务，支持 JWT 和 API Key",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"},
    swagger_ui_init_oauth={},
    swagger_ui_dist_url="https://cdn.staticfile.org/swagger-ui/5.11.0/"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 注册路由
app.include_router(auth.router, prefix="/auth", tags=["认证"])
app.include_router(users.router, prefix="/users", tags=["用户管理"])
app.include_router(api_keys.router, prefix="/api-keys", tags=["API密钥"])


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    await init_db()
    print(f"✅ 认证服务启动成功！端口：{settings.AUTH_SERVICE_PORT}")
    print(f"📚 API文档：http://localhost:{settings.AUTH_SERVICE_PORT}/docs")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "auth"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "commercial.auth_service.app:app",
        host="0.0.0.0",
        port=settings.AUTH_SERVICE_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
