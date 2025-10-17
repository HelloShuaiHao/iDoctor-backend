FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件到 /app/commercial 目录，保持包结构
COPY . /app/commercial/

# 设置 Python 路径
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 9002

# 启动命令
CMD ["python", "-m", "commercial.payment_service.app"]
