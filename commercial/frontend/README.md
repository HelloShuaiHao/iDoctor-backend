# iDoctor 商业化平台 - 前端

> 测试前端，用于测试 iDoctor 商业化模块的认证、支付和订阅功能

## 📋 项目概述

这是一个基于 React + TypeScript + Vite 构建的前端测试应用，用于测试 iDoctor 商业化后端服务的各项功能。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

应用将在 http://localhost:3000 启动。

### 3. 启动后端服务

确保后端服务已启动：
- 认证服务: http://localhost:9001
- 支付服务: http://localhost:9002

### 4. 测试功能

1. 访问 http://localhost:3000
2. 注册新用户或登录
3. 测试认证、支付、订阅功能

## 📖 主要功能

- ✅ 用户认证（注册/登录）
- ✅ Token 自动刷新
- ✅ 支付流程（支付宝/微信）
- ✅ 订阅计划管理
- ⏳ API Key 管理（开发中）

## 🛠️ 技术栈

- React 18 + TypeScript
- Vite
- shadcn/ui + Tailwind CSS
- React Router v6
- Axios

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/     # UI 组件
│   ├── pages/         # 页面
│   ├── services/      # API 服务
│   ├── hooks/         # React Hooks
│   ├── context/       # Context
│   ├── types/         # TypeScript 类型
│   └── utils/         # 工具函数
└── public/            # 静态资源
```

## 📝 更多文档

- [完整文档](./README_FULL.md)
- [API 文档](../docs/API_GUIDE.md)
- [项目状态](../docs/PROJECT_STATUS.md)
