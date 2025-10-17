# 测试和验证指南

## 测试策略

采用**分层测试**策略，确保每个集成阶段的功能正确性。

### 测试层次
1. **单元测试**: 测试单个组件（中间件、配额管理器）
2. **集成测试**: 测试组件之间的交互
3. **端到端测试**: 测试完整用户流程
4. **性能测试**: 测试并发和负载情况

---

## 阶段 1: 基础中间件测试

### 测试环境准备

```bash
# 1. 确保依赖已安装
pip install pytest pytest-asyncio httpx

# 2. 启动认证服务
cd commercial/auth_service
python app.py &  # 后台运行在 9001

# 3. 启动主应用（关闭认证）
export ENABLE_AUTH=false
export ENABLE_QUOTA=false
uvicorn app:app --host 0.0.0.0 --port 4200 &
```

### Test 1.1: 关闭认证模式

**目标**: 验证关闭认证时，API 正常工作

```bash
# 测试健康检查
curl http://localhost:4200/
# 预期: 200 OK

# 测试 API（无需 token）
curl -X POST http://localhost:4200/process/TestPatient/20250101
# 预期: 正常处理或返回合理错误（如文件不存在）

# 测试列出患者
curl http://localhost:4200/list_patients
# 预期: 返回患者列表
```

**验证清单**:
- [ ] 健康检查返回 200
- [ ] API 可以无 token 访问
- [ ] 功能正常运行

### Test 1.2: 启用认证模式 - 未认证访问

**目标**: 验证启用认证后，未认证请求被拦截

```bash
# 重启主应用（启用认证）
export ENABLE_AUTH=true
uvicorn app:app --host 0.0.0.0 --port 4200 &

# 测试未认证访问
curl -X POST http://localhost:4200/process/TestPatient/20250101
# 预期: 401 Unauthorized

curl http://localhost:4200/list_patients
# 预期: 401 Unauthorized

# 测试健康检查（免认证）
curl http://localhost:4200/
# 预期: 200 OK（健康检查不需要认证）
```

**验证清单**:
- [ ] 未认证请求返回 401
- [ ] 错误信息清晰
- [ ] 免认证端点正常工作

### Test 1.3: 认证流程

**目标**: 验证完整的注册→登录→访问流程

```bash
# 1. 注册新用户
curl -X POST http://localhost:9001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "Test123456"
  }'
# 预期: 返回用户信息和 tokens

# 2. 登录
LOGIN_RESPONSE=$(curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "Test123456"
  }')

echo $LOGIN_RESPONSE | jq '.'
# 预期: 返回 access_token 和 refresh_token

# 3. 提取 token
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "Token: $TOKEN"

# 4. 使用 token 访问 API
curl -X POST http://localhost:4200/process/TestPatient/20250101 \
  -H "Authorization: Bearer $TOKEN"
# 预期: 认证通过，正常处理

curl http://localhost:4200/list_patients \
  -H "Authorization: Bearer $TOKEN"
# 预期: 返回患者列表
```

**验证清单**:
- [ ] 注册成功
- [ ] 登录成功获取 token
- [ ] token 能正确访问受保护端点
- [ ] request.state.user_id 被正确设置

### Test 1.4: Token 验证

**目标**: 验证 token 验证的各种场景

```bash
# 测试无效 token
curl -X POST http://localhost:4200/process/TestPatient/20250101 \
  -H "Authorization: Bearer invalid_token_12345"
# 预期: 401 Unauthorized

# 测试过期 token（如果有）
# 预期: 401 Unauthorized

# 测试错误格式的 Authorization header
curl -X POST http://localhost:4200/process/TestPatient/20250101 \
  -H "Authorization: InvalidFormat $TOKEN"
# 预期: 401 Unauthorized
```

**验证清单**:
- [ ] 无效 token 被拒绝
- [ ] 过期 token 被拒绝
- [ ] 错误格式被拒绝

---

## 阶段 2: 数据库测试

### Test 2.1: 配额类型验证

```bash
# 连接数据库
psql -U postgres -d idoctor_commercial

# 查询配额类型
SELECT id, app_id, type_key, name, unit, window 
FROM quota_types 
WHERE app_id = 'idoctor'
ORDER BY type_key;

# 预期输出:
# - api_calls_l3_detect
# - api_calls_full_process
# - api_calls_continue
# - storage_dicom
# - storage_results
```

**验证清单**:
- [ ] 5个配额类型已创建
- [ ] type_key 正确
- [ ] unit 和 window 正确

### Test 2.2: 订阅计划验证

```sql
-- 查询订阅计划
SELECT id, name, price, billing_cycle 
FROM subscription_plans 
ORDER BY price;

-- 预期: 免费版、专业版、企业版
```

**验证清单**:
- [ ] 3个计划已创建
- [ ] 价格正确
- [ ] 计费周期正确

### Test 2.3: 用户配额验证

```bash
# 为测试用户分配配额（使用脚本）
python commercial/scripts/assign_default_quota.py --username testuser

# 验证配额
psql -U postgres -d idoctor_commercial -c "
  SELECT qt.type_key, ql.limit_amount, ql.used_amount
  FROM quota_limits ql
  JOIN quota_types qt ON ql.quota_type_id = qt.id
  JOIN users u ON ql.user_id = u.id
  WHERE u.username = 'testuser';
"
```

**验证清单**:
- [ ] 用户有配额记录
- [ ] limit_amount 正确
- [ ] used_amount 初始为 0

---

## 阶段 3: 用户数据隔离测试

### Test 3.1: 数据路径隔离

**目标**: 验证不同用户的数据存储在不同目录

```bash
# 1. 用户A登录
TOKEN_A=$(curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "userA",
    "password": "password123"
  }' | jq -r '.access_token')

# 2. 用户A上传数据
curl -X POST http://localhost:4200/process/PatientA/20250101 \
  -H "Authorization: Bearer $TOKEN_A"

# 3. 检查文件路径
USER_A_ID=$(curl http://localhost:9001/auth/me \
  -H "Authorization: Bearer $TOKEN_A" | jq -r '.id')
  
ls -la data/$USER_A_ID/
# 预期: 看到 PatientA_20250101 目录

# 4. 用户B登录并上传
TOKEN_B=$(curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "userB",
    "password": "password123"
  }' | jq -r '.access_token')

curl -X POST http://localhost:4200/process/PatientB/20250102 \
  -H "Authorization: Bearer $TOKEN_B"

# 5. 验证用户B的数据在不同目录
USER_B_ID=$(curl http://localhost:9001/auth/me \
  -H "Authorization: Bearer $TOKEN_B" | jq -r '.id')
  
ls -la data/$USER_B_ID/
# 预期: 看到 PatientB_20250102 目录
```

**验证清单**:
- [ ] 用户A的数据在 `data/{user_a_id}/` 下
- [ ] 用户B的数据在 `data/{user_b_id}/` 下
- [ ] 两个目录不同

### Test 3.2: 数据访问隔离

**目标**: 验证用户A无法访问用户B的数据

```bash
# 用户A尝试列出患者
curl http://localhost:4200/list_patients \
  -H "Authorization: Bearer $TOKEN_A"
# 预期: 只看到 PatientA

# 用户B尝试列出患者
curl http://localhost:4200/list_patients \
  -H "Authorization: Bearer $TOKEN_B"
# 预期: 只看到 PatientB

# 用户A尝试访问用户B的数据
curl http://localhost:4200/get_key_results/PatientB/20250102 \
  -H "Authorization: Bearer $TOKEN_A"
# 预期: 404 Not Found 或 403 Forbidden
```

**验证清单**:
- [ ] 用户只能看到自己的患者
- [ ] 跨用户访问被拦截

---

## 阶段 4: 配额扣除测试 ✅

**状态**: 代码实现完成，测试框架就绪

### Test 4.0: 自动化测试脚本

**目标**: 验证配额系统的核心功能

```bash
# 运行全面测试套件
cd /Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend
python commercial/scripts/test_quota_system.py

# 测试内容:
# 1. 数据库连接和模式验证
# 2. 配额类型验证
# 3. 端点映射测试
# 4. (可选) QuotaManager操作测试
```

**验证清单**:
- [ ] 数据库表存在验证
- [ ] 配额类型完整性检查
- [ ] 端点路径匹配测试
- [ ] QuotaManager API调用测试

### Test 4.1: API调用配额自动扣除

**目标**: 验证中间件自动扣除配额

**实现状态**: ✅ 代码完成

```bash
# 1. 查询初始配额
curl http://localhost:4200/my_quota \
  -H "Authorization: Bearer $TOKEN"
# 记录 api_calls_full_process 的剩余量

# 2. 调用 API
curl -X POST http://localhost:4200/process/TestPatient/20250103 \
  -H "Authorization: Bearer $TOKEN"

# 3. 再次查询配额
curl http://localhost:4200/my_quota \
  -H "Authorization: Bearer $TOKEN"
# 预期: api_calls_full_process 减少 1

# 4. 检查响应头
curl -i -X POST http://localhost:4200/process/TestPatient/20250104 \
  -H "Authorization: Bearer $TOKEN"
# 预期: 响应头包含 X-Quota-Remaining: <数字>
```

**验证清单**:
- [ ] 配额自动扣除
- [ ] 响应头包含剩余配额
- [ ] 数据库 usage_logs 有记录

### Test 4.2: 配额用尽场景

**目标**: 验证配额用尽时的行为

```bash
# 1. 手动将配额设置为接近上限
psql -U postgres -d idoctor_commercial -c "
  UPDATE quota_limits 
  SET used_amount = limit_amount - 1
  WHERE user_id = '$USER_ID' 
    AND quota_type_id = (
      SELECT id FROM quota_types WHERE type_key = 'api_calls_full_process'
    );
"

# 2. 调用一次（应该成功）
curl -X POST http://localhost:4200/process/TestPatient/20250105 \
  -H "Authorization: Bearer $TOKEN"
# 预期: 200 OK

# 3. 再次调用（应该失败）
curl -X POST http://localhost:4200/process/TestPatient/20250106 \
  -H "Authorization: Bearer $TOKEN"
# 预期: 402 Payment Required
# 响应: {"error": "配额已用尽", "remaining": 0}
```

**验证清单**:
- [ ] 配额用尽返回 402
- [ ] 错误信息包含剩余配额
- [ ] 请求未被处理

### Test 4.3: 管理API端点测试

**目标**: 验证管理监控和管理功能

**实现状态**: ✅ 代码完成

```bash
# 设置管理员token
export ADMIN_TOKEN="your-admin-secret-token"

# 1. 查看用户配额
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:7500/admin/quotas/users/{user_id}
# 预期: 返回用户所有配额信息

# 2. 查询使用日志
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:7500/admin/quotas/usage-logs?user_id={id}&limit=10"
# 预期: 返回最近10条使用记录

# 3. 获取统计数据
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:7500/admin/quotas/statistics/api_calls_l3_detect?days=30"
# 预期: 返回30天内的统计数据

# 4. 重置用户配额
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:7500/admin/quotas/users/{user_id}/reset?quota_type=api_calls_full_process"
# 预期: 配额重置为0

# 5. 调整配额限制
curl -X PUT -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:7500/admin/quotas/users/{user_id}/adjust?quota_type=api_calls_full_process&new_limit=500"
# 预期: 配额限制调整为500

# 6. 测试无效token
curl -H "X-Admin-Token: invalid_token" \
  http://localhost:7500/admin/quotas/users/{user_id}
# 预期: 403 Forbidden
```

**验证清单**:
- [ ] 用户配额查看返回正确数据
- [ ] 使用日志查询支持过滤
- [ ] 统计数据计算正确
- [ ] 配额重置功能正常
- [ ] 配额调整功能正常
- [ ] 管理员身份验证有效

### Test 4.4: 存储空间配额

**目标**: 验证文件上传的存储配额检查

**实现状态**: ✅ 中间件实现，等待集成测试

```bash
# 创建一个大文件（假设10MB）
dd if=/dev/zero of=test_dicom.zip bs=1M count=10

# 上传文件
curl -X POST http://localhost:4200/upload_dicom_zip \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_dicom.zip"

# 查询配额
curl http://localhost:4200/my_quota \
  -H "Authorization: Bearer $TOKEN"
# 预期: storage_dicom 减少约 0.01 GB
```

**验证清单**:
- [ ] 文件大小正确计算
- [ ] 存储配额正确扣除
- [ ] 空间不足时返回 402

### Test 4.5: 配额类型验证

**目标**: 验证所有配额类型已正确注册

```sql
-- 查询所有iDoctor配额类型
SELECT type_key, name, unit, default_limit, is_active
FROM quota_types
WHERE type_key IN (
  'api_calls_full_process',
  'api_calls_l3_detect', 
  'api_calls_continue',
  'storage_dicom',
  'storage_results'
)
ORDER BY type_key;

-- 预期输出: 5个配额类型
```

**验证清单**:
- [ ] api_calls_full_process 存在
- [ ] api_calls_l3_detect 存在
- [ ] api_calls_continue 存在  
- [ ] storage_dicom 存在
- [ ] storage_results 存在
- [ ] 所有类型 is_active = true

### Test 4.6: 使用日志验证

**目标**: 验证配额消费自动记录到usage_logs表

```sql
-- 查询最近的使用日志
SELECT 
  ul.id,
  ul.user_id,
  qt.type_key,
  ul.amount,
  ul.endpoint,
  ul.created_at
FROM usage_logs ul
JOIN quota_types qt ON ul.quota_type_id = qt.id
ORDER BY ul.created_at DESC
LIMIT 10;

-- 验证metadata字段包含详细信息
SELECT metadata
FROM usage_logs
WHERE endpoint = '/l3_detect'
LIMIT 1;

-- 预期: metadata 包含 patient_name, study_date 等
```

**验证清单**:
- [ ] 每次API调用自动记录
- [ ] user_id 正确关联
- [ ] quota_type_id 正确关联
- [ ] amount 值正确
- [ ] endpoint 路径正确
- [ ] metadata 包含完整信息

---

## 阶段 4 完整性检查

### 代码实现验证

- [x] quota_manager.py SQL查询使用 text()
- [x] JSON序列化支持JSONB字段
- [x] 所有数据库操作异步兼容
- [x] admin_routes.py 管理API实现
- [x] 管理员身份验证
- [x] 配额重置功能
- [x] 配额调整功能  
- [x] 全面日志记录
- [x] 测试框架实现
- [x] 语法验证通过

### 数据库模式验证

- [x] quota_types 表存在
- [x] quota_limits 表存在
- [x] usage_logs 表存在
- [x] 索引正确创建
- [x] 外键关系正确

### 功能完整性

- [x] 配额检查功能
- [x] 配额消费功能
- [x] 剩余配额查询
- [x] 所有配额查询
- [x] 管理API端点
- [x] 使用日志记录
- [x] 统计数据计算

### 文档完整性

- [x] PHASE4_QUOTA_SYSTEM.md (465行)
- [x] PHASE4_COMPLETE.md (369行)
- [x] test_quota_system.py (324行)
- [x] 更新 03_status.md
- [x] 更新 04_testing.md

---

## 端到端测试场景

### Scenario 1: 新用户完整流程

```bash
#!/bin/bash
# 新用户从注册到使用的完整流程

# 1. 注册
curl -X POST http://localhost:9001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "NewUser123"
  }'

# 2. 登录
TOKEN=$(curl -X POST http://localhost:9001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "newuser",
    "password": "NewUser123"
  }' | jq -r '.access_token')

# 3. 查看配额
curl http://localhost:4200/my_quota \
  -H "Authorization: Bearer $TOKEN"

# 4. 上传DICOM
curl -X POST http://localhost:4200/upload_dicom_zip \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.zip"

# 5. 处理数据
curl -X POST http://localhost:4200/process/NewPatient/20250101 \
  -H "Authorization: Bearer $TOKEN"

# 6. 查看结果
curl http://localhost:4200/get_key_results/NewPatient/20250101 \
  -H "Authorization: Bearer $TOKEN"

# 7. 再次查看配额
curl http://localhost:4200/my_quota \
  -H "Authorization: Bearer $TOKEN"

echo "✅ 完整流程测试完成"
```

### Scenario 2: 配额升级流程

```bash
#!/bin/bash
# 模拟用户用尽免费配额后升级

# 1. 耗尽免费配额（调用5次）
for i in {1..5}; do
  curl -X POST http://localhost:4200/process/Patient$i/20250101 \
    -H "Authorization: Bearer $TOKEN"
done

# 2. 尝试第6次（应失败）
curl -X POST http://localhost:4200/process/Patient6/20250101 \
  -H "Authorization: Bearer $TOKEN"
# 预期: 402 Payment Required

# 3. 升级订阅（调用支付服务）
curl -X POST http://localhost:9002/subscriptions/upgrade \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"plan_id": "pro_plan_id"}'

# 4. 再次尝试
curl -X POST http://localhost:4200/process/Patient6/20250101 \
  -H "Authorization: Bearer $TOKEN"
# 预期: 200 OK
```

---

## 性能测试

### 并发测试

```bash
# 使用 Apache Bench 进行并发测试
ab -n 100 -c 10 \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:4200/list_patients

# 预期:
# - Requests per second > 100
# - 无500错误
# - 平均响应时间 < 100ms
```

### 负载测试

```bash
# 使用 wrk 进行负载测试
wrk -t4 -c100 -d30s \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:4200/list_patients

# 预期:
# - 系统保持稳定
# - 无内存泄漏
# - 响应时间合理
```

---

## 回归测试清单

在每次修改后运行，确保没有破坏现有功能：

- [ ] 关闭认证模式下，所有功能正常
- [ ] 启用认证后，认证流程正常
- [ ] 用户数据隔离有效
- [ ] 配额正确扣除
- [ ] 配额用尽正确拦截
- [ ] 性能无明显下降

---

## 测试数据清理

```bash
# 清理测试用户
psql -U postgres -d idoctor_commercial -c "
  DELETE FROM usage_logs WHERE user_id IN (
    SELECT id FROM users WHERE email LIKE '%test%' OR email LIKE '%example.com'
  );
  DELETE FROM quota_limits WHERE user_id IN (
    SELECT id FROM users WHERE email LIKE '%test%' OR email LIKE '%example.com'
  );
  DELETE FROM user_subscriptions WHERE user_id IN (
    SELECT id FROM users WHERE email LIKE '%test%' OR email LIKE '%example.com'
  );
  DELETE FROM users WHERE email LIKE '%test%' OR email LIKE '%example.com';
"

# 清理测试数据目录
rm -rf data/*/Test*
```

---

**创建时间**: 2025-10-17  
**维护**: 每个阶段完成后更新测试结果
