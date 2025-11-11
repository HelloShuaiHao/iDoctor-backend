#!/bin/bash
# IDoctor Backend启动脚本

cd "$(dirname "$0")"

# 停止旧进程
pkill -f "uvicorn app:app"

# 等待进程完全停止
sleep 2

# 启动新进程（开发模式使用--reload，生产模式去掉--reload）
# 开发模式：
nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 4200 --reload > app.log 2>&1 &

# 生产模式（去掉注释使用）：
# nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 4200 --workers 4 > app.log 2>&1 &

echo "App started. Check app.log for details."
echo "PID: $(pgrep -f 'uvicorn app:app')"
