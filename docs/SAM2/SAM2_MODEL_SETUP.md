# SAM2 模型配置指南

## 快速开始

### 一键部署脚本

使用自动化脚本下载和部署 SAM2 模型:

```bash
# 本地开发环境
./scripts/setup_sam2_model.sh

# 生产环境
./scripts/setup_sam2_model.sh --production
```

脚本会自动完成以下步骤:
1. ✅ 检查环境依赖 (wget, docker)
2. ✅ 创建模型目录
3. ✅ 下载 SAM2.1 Hiera Large 模型 (约 856MB)
4. ✅ 复制模型到 Docker volume
5. ✅ 重启 SAM2 服务
6. ✅ 验证模型加载成功
7. ✅ 可选清理本地文件

### 手动部署(可选)

如果需要手动部署,请参考以下步骤:

#### 1. 下载模型

```bash
# 创建模型目录
mkdir -p ~/sam2_models

# 下载 SAM2.1 Hiera Large 模型
wget -O ~/sam2_models/sam2_hiera_large.pt \
  https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt
```

#### 2. 复制到 Docker Volume

```bash
# 检查 volume 是否存在
docker volume inspect docker_sam2_models

# 如果不存在,创建 volume
docker volume create docker_sam2_models

# 复制模型到 volume
docker run --rm \
  -v docker_sam2_models:/models \
  -v ~/sam2_models:/source \
  alpine \
  cp /source/sam2_hiera_large.pt /models/

# 验证
docker run --rm -v docker_sam2_models:/models alpine ls -lh /models/
```

#### 3. 重启服务

```bash
# 使用 docker-compose
cd commercial/docker
docker-compose restart sam2_service

# 或使用 docker
docker restart idoctor_sam2_service
```

#### 4. 验证

```bash
# 检查健康状态
curl http://localhost:8000/health

# 期望输出:
# {"status":"healthy","model_loaded":true,"service":"sam2_segmentation","version":"1.0.0"}

# 查看日志
docker logs --tail 50 idoctor_sam2_service
```

## 模型信息

### SAM2.1 Hiera Large

- **文件名**: `sam2_hiera_large.pt`
- **大小**: 约 856 MB (898,083,611 字节)
- **参数量**: 224.4M
- **性能**: 39.5 FPS on A100 GPU
- **下载地址**: https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt

### 其他可用模型

如需使用其他模型大小,可以下载:

| 模型 | 大小 | 参数量 | 下载链接 |
|------|------|--------|----------|
| sam2.1_hiera_tiny | ~38MB | 38.9M | https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt |
| sam2.1_hiera_small | ~90MB | 46.0M | https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt |
| sam2.1_hiera_base_plus | ~310MB | 80.8M | https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt |
| sam2.1_hiera_large | ~856MB | 224.4M | https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt |

> **注意**: 如果使用其他模型,需要修改环境变量 `SAM2_MODEL_PATH`

## 环境配置

### 环境变量

在 `.env` 或 `commercial/.env` 文件中配置:

```bash
# SAM2 服务配置
SAM2_ENABLED=true
SAM2_SERVICE_URL=http://localhost:8000  # 本地开发
# SAM2_SERVICE_URL=http://sam2_service:8000  # Docker 内部

# SAM2 模型配置
SAM2_MODEL_PATH=/app/models/sam2_hiera_large.pt
SAM2_DEVICE=cpu  # 或 cuda (如果有 GPU)
SAM2_BATCH_SIZE=1
SAM2_CONFIDENCE_THRESHOLD=0.5

# SAM2 客户端配置
SAM2_REQUEST_TIMEOUT=30
SAM2_CACHE_EXPIRE_HOURS=24
```

### Docker Volume 配置

在 `commercial/docker/docker-compose.yml` 中已配置:

```yaml
services:
  sam2_service:
    volumes:
      - sam2_models:/app/models      # 模型权重
      - sam2_cache:/tmp/sam2_cache   # 临时缓存

volumes:
  sam2_models:
    driver: local
  sam2_cache:
    driver: local
```

## 故障排除

### 问题: 模型下载失败

**解决方案**:
1. 检查网络连接
2. 尝试使用代理:
   ```bash
   export http_proxy=http://your-proxy:port
   export https_proxy=http://your-proxy:port
   ./scripts/setup_sam2_model.sh
   ```
3. 手动下载后放到 `~/sam2_models/` 目录

### 问题: Docker volume 权限错误

**解决方案**:
```bash
# 删除旧 volume
docker volume rm docker_sam2_models

# 重新创建
docker volume create docker_sam2_models

# 重新运行脚本
./scripts/setup_sam2_model.sh
```

### 问题: 服务启动后 model_loaded=false

**检查步骤**:

1. 验证文件存在:
   ```bash
   docker run --rm -v docker_sam2_models:/models alpine ls -lh /models/
   ```

2. 检查文件大小:
   ```bash
   # 应该显示约 856M
   docker run --rm -v docker_sam2_models:/models alpine du -h /models/sam2_hiera_large.pt
   ```

3. 查看服务日志:
   ```bash
   docker logs idoctor_sam2_service | grep -i "model\|error\|warning"
   ```

4. 可能的原因:
   - 文件损坏 → 重新下载
   - 内存不足 → 增加 Docker 内存限制
   - Python 依赖缺失 → 重新构建镜像

### 问题: 推理速度慢

**优化建议**:

1. **使用 GPU** (如果可用):
   ```yaml
   # docker-compose.yml
   sam2_service:
     environment:
       SAM2_DEVICE: cuda
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
   ```

2. **使用更小的模型**:
   - 下载 `sam2.1_hiera_small.pt` 或 `sam2.1_hiera_base_plus.pt`
   - 修改 `SAM2_MODEL_PATH` 环境变量

3. **调整超时时间**:
   ```bash
   SAM2_REQUEST_TIMEOUT=60  # 增加到 60 秒
   ```

## 性能基准

| 硬件 | 模型 | 推理时间 |
|------|------|----------|
| MacBook Pro M1 (CPU) | sam2.1_hiera_large | ~15-25s |
| MacBook Pro M1 (CPU) | sam2.1_hiera_small | ~5-10s |
| NVIDIA A100 (GPU) | sam2.1_hiera_large | ~0.025s (39.5 FPS) |
| NVIDIA RTX 3090 (GPU) | sam2.1_hiera_large | ~0.1-0.2s |

> **注意**: 实际性能取决于图像大小、复杂度和硬件配置

## Git 配置

**.gitignore** 已配置忽略模型文件:

```gitignore
# SAM2 模型文件 (大文件)
models/
*.pt
*.pth
*.ckpt
sam2_models/
checkpoints/
```

**重要**:
- ✅ 模型文件不会被 Git 追踪
- ✅ 每个环境需要单独下载模型
- ✅ 使用 `scripts/setup_sam2_model.sh` 脚本简化部署

## 生产部署建议

### 服务器部署步骤

1. **上传脚本到服务器**:
   ```bash
   scp scripts/setup_sam2_model.sh user@server:/path/to/project/scripts/
   ```

2. **SSH 登录服务器**:
   ```bash
   ssh user@server
   cd /path/to/project
   ```

3. **运行部署脚本**:
   ```bash
   ./scripts/setup_sam2_model.sh --production
   ```

4. **验证部署**:
   ```bash
   curl http://localhost:8000/health
   docker logs idoctor_sam2_service
   ```

### 使用预下载的模型

如果服务器网络受限,可以:

1. 在本地下载模型
2. 上传到服务器:
   ```bash
   scp ~/sam2_models/sam2_hiera_large.pt user@server:~/sam2_models/
   ```
3. 在服务器上运行脚本(会跳过下载步骤)

### 生产环境优化

```yaml
# docker-compose.prod.yml
services:
  sam2_service:
    deploy:
      resources:
        limits:
          memory: 8G  # 增加内存限制
        reservations:
          memory: 4G
    restart: always  # 自动重启
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 参考资料

- **SAM2 官方仓库**: https://github.com/facebookresearch/sam2
- **SAM2 论文**: https://ai.meta.com/research/publications/sam-2/
- **模型许可**: Apache 2.0
- **API 文档**: 见 `app.py:884` (SAM2 分割端点)
- **部署文档**: `docs/SAM2/SAM2_DEPLOYMENT.md`

## 支持

遇到问题请:
1. 查看日志: `docker logs idoctor_sam2_service`
2. 检查健康: `curl http://localhost:8000/health`
3. 重新运行脚本: `./scripts/setup_sam2_model.sh`
4. 查看 OpenSpec 任务: `openspec/changes/add-sam2-one-click-segmentation/`
