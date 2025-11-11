#!/bin/sh
set -e

# iDoctor Commercial Nginx 启动脚本
# 功能：替换配置文件中的环境变量并启动 Nginx

echo "==================================="
echo " iDoctor Commercial Nginx"
echo "==================================="

# 设置默认环境变量
export NGINX_PORT=${NGINX_PORT:-3000}
export NGINX_SERVER_NAME=${NGINX_SERVER_NAME:-localhost}
export AUTH_SERVICE_HOST=${AUTH_SERVICE_HOST:-auth_service}
export AUTH_SERVICE_PORT=${AUTH_SERVICE_PORT:-9001}
export PAYMENT_SERVICE_HOST=${PAYMENT_SERVICE_HOST:-payment_service}
export PAYMENT_SERVICE_PORT=${PAYMENT_SERVICE_PORT:-9002}
export IDOCTOR_API_HOST=${IDOCTOR_API_HOST:-host.docker.internal}
export IDOCTOR_API_PORT=${IDOCTOR_API_PORT:-4200}
export SAM2_SERVICE_HOST=${SAM2_SERVICE_HOST:-sam2_service}
export SAM2_SERVICE_PORT=${SAM2_SERVICE_PORT:-8000}
export STATIC_ROOT=${STATIC_ROOT:-/usr/share/nginx/html}

echo "配置信息:"
echo "  监听端口: ${NGINX_PORT}"
echo "  服务器名: ${NGINX_SERVER_NAME}"
echo "  认证服务: ${AUTH_SERVICE_HOST}:${AUTH_SERVICE_PORT}"
echo "  支付服务: ${PAYMENT_SERVICE_HOST}:${PAYMENT_SERVICE_PORT}"
echo "  主应用API: ${IDOCTOR_API_HOST}:${IDOCTOR_API_PORT}"
echo "  SAM2服务: ${SAM2_SERVICE_HOST}:${SAM2_SERVICE_PORT}"
echo "  静态文件: ${STATIC_ROOT}"
echo "==================================="

# 使用 envsubst 替换配置文件中的环境变量
echo "生成 Nginx 配置文件..."
envsubst '${NGINX_PORT} ${NGINX_SERVER_NAME} ${AUTH_SERVICE_HOST} ${AUTH_SERVICE_PORT} ${PAYMENT_SERVICE_HOST} ${PAYMENT_SERVICE_PORT} ${IDOCTOR_API_HOST} ${IDOCTOR_API_PORT} ${SAM2_SERVICE_HOST} ${SAM2_SERVICE_PORT} ${STATIC_ROOT}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# 检查配置文件
echo "测试 Nginx 配置..."
nginx -t

echo "启动 Nginx..."
echo "==================================="

# 执行传入的命令（通常是 nginx -g 'daemon off;'）
exec "$@"
