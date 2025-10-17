@echo off
chcp 65001 >nul
echo 🚀 启动 iDoctor 商业化系统...
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未安装 Docker
    echo 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose 是否可用
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: Docker Compose 不可用
    echo 请确保 Docker Desktop 正在运行
    pause
    exit /b 1
)

echo ✅ Docker 环境检查通过
echo.

REM 进入 docker 目录
cd /d "%~dp0"

REM 启动服务
echo 📦 启动所有服务...
docker compose up -d

echo.
echo ⏳ 等待服务启动...
timeout /t 10 /nobreak >nul

echo.
echo ✅ 服务启动成功！
echo.
echo 📝 访问以下地址：
echo    - 认证服务 API 文档: http://localhost:9001/docs
echo    - 支付服务 API 文档: http://localhost:9002/docs
echo.
echo 📊 查看服务状态:
echo    docker compose ps
echo.
echo 📋 查看服务日志:
echo    docker compose logs -f
echo.
echo 🛑 停止服务:
echo    docker compose down
echo.
pause
