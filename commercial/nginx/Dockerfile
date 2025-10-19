FROM nginx:1.24-alpine

# 安装 envsubst 工具（用于替换环境变量）
RUN apk add --no-cache gettext

# 复制配置模板
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# 复制启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 创建日志目录
RUN mkdir -p /var/log/nginx

# 设置工作目录
WORKDIR /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:${NGINX_PORT:-3000}/health || exit 1

EXPOSE ${NGINX_PORT:-3000}

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
