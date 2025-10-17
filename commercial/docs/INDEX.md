# 📚 文档索引

iDoctor 商业化模块完整文档导航

---

## 🚀 快速开始

### 新手入门
- **[后端快速开始](./QUICK_START.md)** ⭐️
  - 30秒一键启动后端服务
  - Docker 和传统部署方式
  - 基础测试示例

- **[前端快速开始](../frontend/QUICK_START.md)** ⭐️
  - 前端应用启动指南
  - 功能测试步骤
  - 开发提示

---

## 📖 开发文档

### API 文档
- **[API 使用指南](./API_GUIDE.md)**
  - 认证服务 API (端口 9001)
  - 支付服务 API (端口 9002)
  - 完整的请求/响应示例
  - 错误码说明

### 架构文档
- **[前端架构规划](./FRONTEND_STRUCTURE.md)**
  - 前端项目结构详解
  - 技术栈选型说明
  - 组件设计规范
  - 开发流程指南

- **[项目进度](./PROJECT_STATUS.md)**
  - 当前开发状态
  - 已完成功能清单
  - 待开发功能列表
  - 下一步行动计划

---

## 🐳 部署文档

### Docker 部署
- **[Docker 指南](./DOCKER_GUIDE.md)**
  - Docker Compose 配置说明
  - 容器编排详解
  - 环境变量配置
  - 常见问题排查

---

## 📊 项目总结

### 交付文档
- **[交付总结](./DELIVERY_SUMMARY.md)**
  - 系统架构总览
  - 核心功能介绍
  - 技术亮点说明

---

## 📁 文档结构

```
docs/
├── INDEX.md                    # 📚 本文件 - 文档索引
│
├── 🚀 快速开始
│   ├── QUICK_START.md         # 后端快速开始
│   └── ../frontend/QUICK_START.md  # 前端快速开始
│
├── 📖 开发文档
│   ├── API_GUIDE.md           # API 使用指南
│   ├── FRONTEND_STRUCTURE.md  # 前端架构
│   └── PROJECT_STATUS.md      # 项目进度
│
├── 🐳 部署文档
│   └── DOCKER_GUIDE.md        # Docker 指南
│
└── 📊 项目总结
    └── DELIVERY_SUMMARY.md    # 交付总结
```

---

## 🔗 外部链接

### API 交互文档
- 认证服务 Swagger: http://localhost:9001/docs
- 支付服务 Swagger: http://localhost:9002/docs

### 前端应用
- 测试前端: http://localhost:3000

### 代码仓库
- 项目根目录: [../README.md](../README.md)
- 前端项目: [../frontend/README.md](../frontend/README.md)

---

## 📝 文档使用建议

### 第一次使用？
1. 阅读 [后端快速开始](./QUICK_START.md)
2. 启动服务
3. 阅读 [API 使用指南](./API_GUIDE.md)
4. 启动 [前端应用](../frontend/QUICK_START.md) 进行测试

### 前端开发？
1. 阅读 [前端快速开始](../frontend/QUICK_START.md)
2. 查看 [前端架构](./FRONTEND_STRUCTURE.md)
3. 参考 [API 使用指南](./API_GUIDE.md) 进行集成

### 部署上线？
1. 阅读 [Docker 指南](./DOCKER_GUIDE.md)
2. 配置环境变量
3. 运行 `./start.sh` 或 `docker compose up`

### 了解进度？
- 查看 [项目进度](./PROJECT_STATUS.md)
- 查看 [交付总结](./DELIVERY_SUMMARY.md)

---

## 💡 文档维护

### 文档更新
文档会随着项目开发持续更新，建议定期查看最新版本。

### 反馈建议
如果发现文档问题或有改进建议，请：
1. 创建 Issue
2. 提交 Pull Request
3. 联系项目维护者

---

**提示**: 所有文档均支持 Markdown 格式，建议使用支持 Markdown 的编辑器查看。
