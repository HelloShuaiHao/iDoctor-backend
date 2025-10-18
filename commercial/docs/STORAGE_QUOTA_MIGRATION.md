# 存储配额迁移指南：GB → MB

**日期**: 2025-10-18
**目的**: 将存储配额单位从 GB 改为 MB，默认配额从 10GB 改为 100MB

---

## 📋 变更摘要

### 配额单位变更

| 配额类型 | 旧单位 | 旧默认值 | 新单位 | 新默认值 |
|---------|--------|---------|--------|---------|
| `storage_dicom` | GB | 10 | MB | 100 |
| `storage_results` | GB | 5 | MB | 50 |
| `storage_usage` | MB | 10 | MB | 100 |

### 代码变更

1. **`storage_tracker.py`** - 添加 `bytes_to_mb()` 函数，所有计算改为 MB
2. **`init_database.py`** - 新用户默认配额改为 MB
3. **`app.py`** - 上传完成后自动同步存储使用量
4. **配额中间件** - 不再扣除上传配额（仅同步实际使用量）

---

## 🚀 迁移步骤

### 步骤 1: 备份数据库

```bash
# PostgreSQL 备份
pg_dump -h localhost -U your_user -d your_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 步骤 2: 运行迁移脚本

```bash
cd /Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend
python commercial/scripts/migrate_storage_to_mb.py
```

脚本会：
1. 更新 `quota_types` 表：单位 GB → MB，默认限制调整
2. 更新所有用户的 `quota_limits`：限制值调整，使用量重置为 0
3. 提示下一步操作

### 步骤 3: 同步实际存储使用量

```bash
python commercial/scripts/sync_all_users_storage.py
```

此脚本会：
- 遍历所有用户的数据目录
- 计算实际磁盘使用量（MB）
- 更新到数据库

### 步骤 4: 重启服务

```bash
# 停止当前运行的服务
# 然后重启
uvicorn app:app --host 0.0.0.0 --port 4200 --workers 1
```

### 步骤 5: 验证

```bash
# 查看配额状态
python check_quota_usage.py
```

应该能看到：
```
用户名             配额类型                           配额名                  单位       限制         已用         剩余
====================================================================================================
testuser        storage_dicom                  DICOM存储空间            MB       100.00     12.50      87.50
testuser        storage_results                结果存储空间               MB       50.00      8.30       41.70
testuser        storage_usage                  存储使用量                MB       100.00     20.80      79.20
```

---

## 🔧 工作原理

### 上传流程

```
用户上传 DICOM ZIP
    ↓
解压到 data/{user_id}/{patient}_{date}/input/
    ↓
触发存储同步: sync_storage_quota_to_db()
    ↓
计算 input/ 和 output/ 目录大小（MB）
    ↓
更新数据库:
  - storage_dicom (input 目录大小)
  - storage_results (output 目录大小)
  - storage_usage (总大小)
```

### 配额检查

**上传时**：不再检查配额（之前按 GB 扣除导致四舍五入问题）

**处理时**：检查 `api_calls_full_process` 配额（按次数扣除）

**定期同步**：可以定时运行 `sync_all_users_storage.py` 更新实际使用量

---

## 📊 数据库 Schema

### quota_types 表

```sql
-- storage_dicom
type_key: 'storage_dicom'
name: 'DICOM存储空间'
unit: 'MB'
default_limit: 100

-- storage_results
type_key: 'storage_results'
name: '结果存储空间'
unit: 'MB'
default_limit: 50

-- storage_usage
type_key: 'storage_usage'
name: '存储使用量'
unit: 'MB'
default_limit: 100
```

### quota_limits 表

```sql
-- 示例：用户上传了 12.5MB 的 DICOM 文件，处理后生成了 8.3MB 的结果
user_id: 'xxx-xxx-xxx'
quota_type_id: <storage_dicom UUID>
limit_amount: 100.00
used_amount: 12.50

user_id: 'xxx-xxx-xxx'
quota_type_id: <storage_results UUID>
limit_amount: 50.00
used_amount: 8.30

user_id: 'xxx-xxx-xxx'
quota_type_id: <storage_usage UUID>
limit_amount: 100.00
used_amount: 20.80  -- 12.5 + 8.3
```

---

## 🧪 测试场景

### 测试 1: 新用户注册

1. 注册新用户
2. 检查配额分配：
   ```bash
   python check_quota_usage.py | grep -A 10 "new_user"
   ```
3. **预期**: `storage_*` 配额单位为 MB，限制为 100/50/100

### 测试 2: 上传并同步

1. 上传一个 15MB 的 DICOM ZIP
2. 查看后端日志，应该看到：
   ```
   INFO: User xxx storage: DICOM=15.23MB, Results=0.00MB, Total=15.23MB, Cases=1
   ```
3. 查看配额：
   ```bash
   python check_quota_usage.py
   ```
4. **预期**: `storage_dicom` 和 `storage_usage` 使用量约 15MB

### 测试 3: 处理后同步

1. 处理上传的数据
2. 处理完成后，再次检查配额
3. **预期**: `storage_results` 和 `storage_usage` 增加

### 测试 4: 配额耗尽

1. 手动将用户的 `storage_usage` 限制设为 20MB
2. 尝试上传 25MB 的文件
3. **预期**: 上传成功（不再检查），但下次同步时会超额

---

## ⚠️ 注意事项

### 1. 不再在上传时检查存储配额

**原因**：
- 小文件（<10MB）转换为 GB 后被四舍五入为 0.00
- 导致配额扣除不准确

**新策略**：
- 上传时只记录实际使用量（不扣除配额）
- 管理员可以通过查看 `used_amount` 监控用户使用情况
- 如果用户超额，管理员可以手动限制或提示升级

### 2. 定期同步

建议设置 cron 任务定期同步：

```bash
# 每天凌晨 2 点同步所有用户存储使用量
0 2 * * * cd /path/to/iDoctor-backend && python commercial/scripts/sync_all_users_storage.py >> /var/log/storage_sync.log 2>&1
```

### 3. 清理旧数据

如果用户删除了文件，需要重新同步才能释放配额：

```bash
python commercial/scripts/sync_all_users_storage.py
```

---

## 🔄 回滚方案

如果需要回滚到 GB 单位：

1. 恢复数据库备份
2. 回退代码到迁移前的 commit
3. 重启服务

---

## 📞 问题排查

### 问题 1: 存储使用量显示 0

**原因**: 未运行同步脚本

**解决**:
```bash
python commercial/scripts/sync_all_users_storage.py
```

### 问题 2: 用户数据目录不存在

**原因**: 用户还没有上传过数据

**解决**: 正常现象，等待用户首次上传后会自动创建

### 问题 3: 权限错误

**原因**: 脚本无法读取 data/ 目录

**解决**:
```bash
chmod -R 755 data/
```

---

**完成时间**: 约 5-10 分钟（取决于用户数量和数据量）
