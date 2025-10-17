# 商业化系统集成文档

## 📋 目标

将 `commercial` 目录下的中间件系统集成到运行在 **4200端口** 的 uvicorn 后台应用中，实现以下功能：
- API 调用记录和配额管理
- AI 分析次数统计
- 内存/存储使用量监控
- 用户认证和数据隔离

## 📁 文档结构

```
docs/integration/
├── README.md              # 本文件 - 总览
├── 01_analysis.md         # 当前系统分析
├── 02_integration_plan.md # 集成计划和步骤
├── 03_status.md           # 集成进度跟踪
└── 04_testing.md          # 测试和验证
```

## 📚 参考资源

### Commercial 系统文档
- [commercial/integrations/README.md](../../commercial/integrations/README.md) - 集成指南
- [commercial/docs/INTEGRATION_DESIGN.md](../../commercial/docs/INTEGRATION_DESIGN.md) - 架构设计
- [commercial/docs/INTEGRATION_STATUS.md](../../commercial/docs/INTEGRATION_STATUS.md) - 商业化系统状态

### 主应用信息
- **端口**: 4200
- **框架**: FastAPI + uvicorn
- **主要功能**: CT扫描处理、L3椎骨检测、肌肉分割

## 🎯 集成关键点

### 1. 中间件集成
- ✅ 认证中间件 (`auth_middleware.py`)
- ✅ 配额中间件 (`quota_middleware.py`)
- 配额管理器 (`quota_manager.py`)

### 2. 需要记录的指标
- API 调用次数（按端点分类）
- AI 分析次数（L3检测、肌肉分割）
- 存储空间使用（DICOM文件、处理结果）
- 内存使用量

### 3. 数据库集成
- 共享数据库: `idoctor_commercial`
- 用户表、配额表、使用日志表
- 用户数据隔离

## 🚀 快速开始

### 前置条件
```bash
# 1. 确保 PostgreSQL 运行中
# 2. 确保安装了依赖
pip install -r commercial/requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和 JWT
```

### 开发模式（跳过认证）
```bash
export ENABLE_AUTH=false
export ENABLE_QUOTA=false
uvicorn app:app --host 0.0.0.0 --port 4200 --reload
```

### 生产模式（启用认证）
```bash
export ENABLE_AUTH=true
export ENABLE_QUOTA=true
uvicorn app:app --host 0.0.0.0 --port 4200
```

## ⚠️ 注意事项

1. **中间件顺序很重要**
   - 先注册认证中间件
   - 再注册配额中间件

2. **最小侵入性原则**
   - 通过环境变量控制功能开关
   - 现有代码改动最小化
   - 保持向后兼容

3. **用户数据隔离**
   - 认证后按 `user_id` 组织数据
   - 开发模式共享数据

## 📈 进度追踪

当前状态将在 `03_status.md` 中实时更新。

---

**创建时间**: 2025-10-17  
**负责人**: Development Team  
**最后更新**: 2025-10-17
