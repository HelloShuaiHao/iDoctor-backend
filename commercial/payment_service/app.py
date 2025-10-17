"""支付服务 FastAPI 应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from commercial.shared.config import settings
from commercial.shared.database import init_db
from .api import plans, subscriptions

# 创建应用
app = FastAPI(
    title="iDoctor 支付服务",
    description="通用支付服务，支持支付宝和微信支付",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
app.include_router(plans.router, prefix="/plans", tags=["订阅计划"])
app.include_router(subscriptions.router, prefix="/subscriptions", tags=["订阅管理"])

# TODO: 添加支付和Webhook路由
# app.include_router(payments.router, prefix="/payments", tags=["支付"])
# app.include_router(webhooks.router, prefix="/webhooks", tags=["支付回调"])


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    await init_db()
    print(f"✅ 支付服务启动成功！端口：{settings.PAYMENT_SERVICE_PORT}")
    print(f"📚 API文档：http://localhost:{settings.PAYMENT_SERVICE_PORT}/docs")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "payment"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.PAYMENT_SERVICE_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
