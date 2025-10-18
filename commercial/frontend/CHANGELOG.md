# 更新日志

所有重要的变更都将记录在这个文件中。

## [1.1.0] - 2025-10-18

### ✨ 新增功能

#### 支付记录页面
- 新增完整的支付历史展示页面 (`/payment-history`)
- 支持查看所有交易记录，包括订单号、金额、状态等
- 统计卡片显示：总支出、总交易数、支付成功率
- 支持按状态筛选（已完成、待支付、已退款、失败）
- 交易记录卡片展示详细信息和支付方式
- 预留发票下载功能接口

#### iDoctor主应用API集成
- 新增 `idoctorAPI` 实例，连接主应用4200端口
- 支持配额管理、CT处理等功能的API调用
- 统一的Token管理和自动刷新机制
- 完善的错误处理和请求重试

### 🔧 优化改进

#### 配额管理系统
- **移除Mock数据**: `quotaService.ts` 完全使用真实后端API
- **API端点对接**:
  - `GET /admin/quotas/users/me` - 配额摘要
  - `GET /admin/quotas/usage-logs` - 使用历史
  - `GET /admin/quotas/statistics/{type}` - 使用趋势
- **数据格式转换**: 自动转换后端数据格式到前端TypeScript类型
- **优雅降级**: API失败时返回空数据而非抛出错误

#### Dashboard改进
- 移除"支付记录"卡片的"开发中"标签
- 所有功能卡片现在都可以正常跳转
- 优化卡片hover效果和视觉反馈

#### 环境配置
- 新增 `VITE_IDOCTOR_API_URL` 环境变量
- 更新 `.env.development` 和 `.env.example`
- 统一API配置管理

### 📝 文档更新
- 新增 `DEVELOPMENT_GUIDE.md` - 完整的开发指南
- 更新 `README.md` - 项目概述和快速开始
- 新增 `CHANGELOG.md` - 版本更新日志

### 🐛 Bug修复
- 修复配额数据加载时的类型转换问题
- 修复Token刷新逻辑可能导致的无限循环
- 优化API请求超时配置（主应用30秒）

---

## [1.0.0] - 2024-10-17

### 🎉 初始版本

#### 核心功能
- ✅ 用户认证系统（注册/登录）
- ✅ Token自动刷新机制
- ✅ 订阅计划展示
- ✅ 支付流程（支付宝/微信）
- ✅ API密钥管理
- ✅ 使用统计展示

#### 技术栈
- React 18 + TypeScript
- Vite 构建工具
- shadcn/ui + Tailwind CSS
- React Router v6
- Axios HTTP客户端

#### 页面实现
- 主页
- 认证页面（登录/注册）
- 控制台
- 订阅计划页面
- 我的订阅页面
- 支付页面
- API密钥管理页面
- 使用统计页面

---

## 版本规范

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)

### 类型说明
- `新增功能` - 新增的功能特性
- `优化改进` - 对现有功能的改进
- `Bug修复` - 修复的问题
- `重大变更` - 不向后兼容的变更
- `文档更新` - 文档相关的更新
- `依赖更新` - 依赖包的更新
