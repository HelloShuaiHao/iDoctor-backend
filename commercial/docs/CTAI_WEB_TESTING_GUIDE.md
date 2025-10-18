# CTAI_web 商业化功能测试指南

**版本**: v1.0
**日期**: 2025-10-18
**测试范围**: 认证系统、配额管理、用户交互

---

## 🚀 快速启动

### 1. 启动后端服务

```bash
# 终端 1: 启动认证服务（端口 9001）
cd /path/to/commercial/backend
uvicorn main:app --host 0.0.0.0 --port 9001

# 终端 2: 启动主服务（端口 4200）
cd /path/to/iDoctor-backend
uvicorn app:app --host 0.0.0.0 --port 4200 --workers 1
```

### 2. 启动前端服务

```bash
# 终端 3: 启动 CTAI_web（端口 7500）
cd /path/to/CTAI_web
npm run serve

# （可选）终端 4: 启动商业前端（端口 3000）
cd /path/to/commercial/frontend
npm run dev
```

### 3. 访问应用

- CTAI_web: http://localhost:7500
- 商业管理后台: http://localhost:3000

---

## ✅ 测试场景

### 场景 1: 新用户注册与登录

**步骤**:
1. 访问 http://localhost:7500
2. 自动跳转到 `/login` 页面
3. 点击"注册"标签
4. 填写表单：
   - 用户名: `testuser001`
   - 邮箱: `testuser001@example.com`
   - 密码: `password123`
   - 确认密码: `password123`
5. 点击"注册"按钮

**预期结果**:
- ✅ 注册成功，显示"注册成功，请登录"
- ✅ 自动切换到"登录"标签
- ✅ 后端自动分配初始配额（api_calls_full_process: 5）

---

### 场景 2: 用户登录与配额显示

**步骤**:
1. 在登录页输入刚注册的用户名和密码
2. 点击"登录"

**预期结果**:
- ✅ 登录成功，跳转到首页 `/`
- ✅ Header 右上角显示用户菜单：`👤 testuser001 5/5`
- ✅ 配额徽章以蓝色渐变显示

**检查点**:
```javascript
// 浏览器控制台检查
localStorage.getItem('access_token') // 应该返回 JWT token
```

---

### 场景 3: 查看配额详情

**步骤**:
1. 点击 Header 中的用户菜单（用户名部分）
2. 选择"📊 配额详情"

**预期结果**:
- ✅ 弹出对话框显示：
  ```
  已使用：0
  总配额：5
  可用配额：5
  ```

---

### 场景 4: 正常上传（有配额）

**步骤**:
1. 准备一个 DICOM ZIP 文件
2. 在首页填写：
   - 病人姓名: `TestPatient`
   - 检查日期: `20251018`
3. 选择 ZIP 文件
4. 点击"上传"

**预期结果**:
- ✅ 配额检查通过（无弹窗）
- ✅ 上传进度条显示
- ✅ 上传成功，进入步骤 2

---

### 场景 5: 处理数据与配额扣除

**步骤**:
1. 在步骤 2 页面点击"开始处理"
2. 等待处理完成

**预期结果**:
- ✅ 进度条显示处理状态
- ✅ 处理成功后自动跳转步骤 3
- ✅ Header 配额徽章更新为 `4/5`（已使用 1 次）

**验证**:
```bash
# 在后端控制台查看日志
# 应该看到 quota_middleware 扣除记录
```

---

### 场景 6: 配额耗尽提示

**步骤**:
1. 重复场景 4-5，直到配额用完（5 次处理）
2. 再次尝试上传新的 DICOM 文件

**预期结果**:
- ✅ 点击"上传"后立即弹窗：
  ```
  配额不足
  您的处理配额已用尽，无法继续上传。请升级套餐以获取更多配额。

  [立即升级] [取消]
  ```
- ✅ 点击"立即升级"跳转到商业前端订阅页（携带 token）

---

### 场景 7: 订阅管理跳转

**步骤**:
1. 点击 Header 用户菜单
2. 选择"💳 订阅管理"

**预期结果**:
- ✅ 跳转到 `http://localhost:3000/#/subscription?token=<your_token>`
- ✅ 商业前端接收 token 并自动登录（如果已实现阶段 4）

---

### 场景 8: 退出登录

**步骤**:
1. 点击 Header 用户菜单
2. 选择"🚪 退出登录"
3. 确认退出

**预期结果**:
- ✅ 弹出确认框
- ✅ 确认后清除 localStorage 中的 token
- ✅ Header 用户菜单消失
- ✅ 自动跳转到 `/login` 页面

---

### 场景 9: Token 过期处理

**步骤**:
1. 登录成功后
2. 打开浏览器控制台，删除 token：
   ```javascript
   localStorage.removeItem('access_token')
   ```
3. 尝试访问首页或刷新页面

**预期结果**:
- ✅ API 拦截器捕获 401 错误
- ✅ 自动跳转到 `/login` 页面
- ✅ 显示提示"登录已过期"（如果已实现）

---

### 场景 10: 语言切换

**步骤**:
1. 登录后在 Header 切换语言（中文 ↔ English）
2. 观察配额徽章、菜单项、弹窗文案

**预期结果**:
- ✅ 配额徽章格式保持 `{used}/{limit}`（数字不变）
- ✅ 菜单项切换为对应语言
- ✅ 配额不足弹窗切换为英文提示

---

## 🐛 常见问题排查

### 问题 1: Header 不显示用户菜单

**排查步骤**:
```javascript
// 浏览器控制台
localStorage.getItem('access_token') // 检查 token 是否存在

// 网络面板
// 查看 /users/me 请求是否成功
// 查看 /admin/quotas/users/me 请求是否成功
```

**解决方案**:
- 确保认证服务（9001）和主服务（4200）都在运行
- 检查 CORS 配置是否允许 `http://localhost:7500`

---

### 问题 2: 配额徽章显示 `0/null`

**原因**: `/admin/quotas/users/me` 请求失败

**排查**:
```bash
# 检查后端日志
# 确认 quota_manager 是否正确初始化
```

**解决方案**:
```bash
# 重新初始化配额数据
cd commercial
python -c "from integrations.quota_manager import QuotaManager; qm = QuotaManager(); qm.init_quota_types()"
```

---

### 问题 3: 上传前配额检查失败

**错误信息**: "配额检查失败"

**原因**:
- 主服务配额端点未启用
- 用户没有配额记录

**解决方案**:
```bash
# 1. 确认 .env 配置
ENABLE_QUOTA=true

# 2. 重启主服务
uvicorn app:app --reload --port 4200
```

---

### 问题 4: 处理后配额未更新

**原因**: `quota-updated` 事件未触发

**排查**:
```javascript
// 在 Header.vue 的 mounted 钩子中添加调试
this.$root.$on('quota-updated', () => {
  console.log('收到配额更新事件')
  this.loadQuota()
})
```

**解决方案**:
- 确认 Content.vue 的 processData 成功时发出了事件
- 检查 Header 组件是否已挂载

---

## 📝 测试检查清单

打印此清单，逐项测试：

- [ ] 用户注册成功
- [ ] 用户登录成功，token 保存到 localStorage
- [ ] Header 显示用户名和配额徽章
- [ ] 配额详情对话框显示正确数据
- [ ] 有配额时上传成功
- [ ] 处理成功后配额自动扣除
- [ ] Header 配额徽章实时更新
- [ ] 配额耗尽时弹出升级提示
- [ ] "立即升级"跳转到商业前端（携带 token）
- [ ] 订阅管理菜单跳转正确
- [ ] 退出登录清除 token 并跳转
- [ ] Token 过期时自动跳转登录页
- [ ] 中英文切换正常

---

## 🔍 性能检查

### 网络请求优化

**正常流程应该有以下请求**:
```
登录时:
  POST /auth/login  (9001)

首页加载:
  GET /users/me (9001) - 获取用户信息
  GET /admin/quotas/users/me (4200) - 获取配额

上传前:
  GET /admin/quotas/users/me (4200) - 检查配额

处理完成后:
  GET /admin/quotas/users/me (4200) - 刷新配额
```

**优化建议**:
- 配额信息可以考虑增加缓存（30 秒 TTL）
- 避免在短时间内重复请求相同数据

---

## 📊 数据库验证

### 检查用户配额记录

```sql
-- 查看用户配额使用情况
SELECT u.username, uq.type_key, uq.used, uq.quota_limit
FROM users u
JOIN user_quotas uq ON u.id = uq.user_id
WHERE u.username = 'testuser001';
```

**预期结果**:
```
username     | type_key                | used | quota_limit
-------------|-------------------------|------|------------
testuser001  | api_calls_full_process  | 5    | 5
testuser001  | storage_mb              | 0    | 100
```

---

## 🎉 测试通过标准

以下所有条件满足，视为测试通过：

1. ✅ 所有 13 项检查清单通过
2. ✅ 无 JavaScript 控制台错误
3. ✅ 无网络请求失败（除了预期的 401）
4. ✅ 配额数据与数据库记录一致
5. ✅ UI 交互流畅，无明显延迟
6. ✅ 中英文翻译准确无遗漏

---

**测试完成后，请将结果记录在**: `FRONTEND_INTEGRATION_PROGRESS.md`
