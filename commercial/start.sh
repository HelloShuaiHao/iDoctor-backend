#!/bin/bash
# 便捷启动脚本 - 自动跳转到 docker 目录执行
cd "$(dirname "$0")/docker" && ./start.sh
