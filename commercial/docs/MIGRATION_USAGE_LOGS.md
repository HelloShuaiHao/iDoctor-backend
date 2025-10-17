# usage_logs 表结构迁移说明

## 问题背景

在开发过程中，`usage_logs` 表经历了一次结构变更：

### 旧版本结构
```sql
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    subscription_id UUID REFERENCES user_subscriptions(id),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    quota_cost INTEGER DEFAULT 1,
    created_at TIMESTAMP,
    extra_info JSON
);
```

### 新版本结构
```sql
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    quota_type_id UUID REFERENCES quota_types(id),  -- ✨ 新字段
    amount DECIMAL(15,2) NOT NULL,                   -- ✨ 新字段
    endpoint VARCHAR(200),                           -- ✨ 新字段
    metadata JSONB,                                  -- ✨ 新字段
    created_at TIMESTAMP WITH TIME ZONE
);
```

## 迁移方案

### 自动迁移（推荐）

已在 `commercial/scripts/docker_init.sh` 中集成了自动迁移检查：

```bash
# 迁移 usage_logs 表到新结构（如果需要）
echo "🔄 检查并迁移 usage_logs 表..."
python scripts/migrate_usage_logs.py || echo "⚠️  迁移检查跳过"
```

**迁移脚本逻辑：**

1. ✅ **表不存在** → 跳过（由 `init_database.py` 创建新表）
2. ✅ **已是新结构**（有 `quota_type_id`）→ 跳过
3. ⚠️ **旧结构**（有 `subscription_id`）→ 自动迁移：
   - 备份旧数据到 `usage_logs_backup_old`
   - 删除旧表
   - 创建新表
   - 创建索引

### 手动迁移

如果需要手动迁移现有数据库：

```bash
# 从项目根目录运行
PYTHONPATH=$(pwd) python commercial/scripts/migrate_usage_logs.py
```

## Docker 部署说明

### 全新部署

全新部署时会自动创建正确的表结构，无需担心迁移问题。

### 升级已有系统

如果已有 Docker 部署使用了旧版本，重新部署时会：

1. `init_database.py` 创建基础表（旧表已存在则跳过）
2. `migrate_usage_logs.py` 检测并迁移旧表到新结构 ✅
3. 系统正常启动

**数据卷持久化：**

如果使用了 Docker 数据卷持久化，旧数据会被自动备份到 `usage_logs_backup_old` 表中。

## 测试验证

### 检查当前表结构

```bash
python check_usage_logs_schema.py
```

### 测试配额消耗

```bash
python test_quota_consume.py
```

应该看到：
- ✅ 配额正确扣除
- ✅ `remaining` 递减
- ✅ usage_logs 表正确记录日志

## 常见问题

### Q: 旧数据会丢失吗？

**A:** 不会。迁移前会自动备份到 `usage_logs_backup_old` 表。但由于新旧表结构差异较大，不会自动转换数据。如需保留旧数据，请手动编写转换脚本。

### Q: 如何回滚到旧版本？

**A:**

```sql
-- 1. 删除新表
DROP TABLE usage_logs;

-- 2. 从备份恢复（如果有）
CREATE TABLE usage_logs AS SELECT * FROM usage_logs_backup_old;
```

### Q: 迁移失败怎么办？

**A:** 迁移脚本使用事务，失败会自动回滚。检查日志查看具体错误：

```bash
python commercial/scripts/migrate_usage_logs.py
```

### Q: 如何手动触发迁移？

**A:**

```bash
# 方式1：直接运行迁移脚本
PYTHONPATH=$(pwd) python commercial/scripts/migrate_usage_logs.py

# 方式2：重新运行 Docker 初始化
docker-compose exec commercial-db-init bash /app/scripts/docker_init.sh
```

## 影响的文件

- ✅ `commercial/scripts/init_database.py` - 新表定义
- ✅ `commercial/scripts/migrate_usage_logs.py` - 迁移脚本（新增）
- ✅ `commercial/scripts/docker_init.sh` - Docker 初始化流程（已更新）
- ✅ `commercial/integrations/quota_manager.py` - 配额管理器（使用新字段）
- ✅ `commercial/integrations/middleware/quota_middleware.py` - 配额中间件

## 更新日期

- **2025-10-18**: 创建迁移脚本并集成到 Docker 初始化流程
