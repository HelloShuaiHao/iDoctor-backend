# Phase 4: Quota Deduction and Monitoring

**Status**: ✅ Complete  
**Date**: 2025-01-15

## Overview

Phase 4 implements the quota deduction and monitoring system, including:
- Automatic quota checking before API calls
- Quota consumption tracking after successful operations
- Admin monitoring endpoints for usage analytics
- Comprehensive logging for auditing

## Components

### 1. Quota Manager (`integrations/quota_manager.py`)

Core quota management logic with database operations:

```python
from commercial.integrations.quota_manager import QuotaManager

manager = QuotaManager(database_url)

# Check quota availability
has_quota = await manager.check_quota(user_id, "api_calls_full_process", 1)

# Consume quota after successful operation
await manager.consume_quota(user_id, "api_calls_full_process", 1, metadata={...})

# Get remaining quota
remaining = await manager.get_remaining_quota(user_id, "api_calls_full_process")
```

**Key Methods**:
- `check_quota()` - Verify sufficient quota before operation
- `consume_quota()` - Deduct quota and log usage
- `get_remaining_quota()` - Get available quota amount
- `get_all_quotas()` - Get all quota types for a user

### 2. Quota Middleware (`integrations/middleware/quota_middleware.py`)

FastAPI middleware that automatically intercepts API calls:

```python
# Middleware flow:
# 1. Check if endpoint requires quota
# 2. Verify user has sufficient quota
# 3. Execute request
# 4. Consume quota on success (2xx status)
# 5. Add quota info to response headers
```

**Configuration**:

```python
# Endpoint → Quota mapping
ENDPOINT_QUOTA_MAP = {
    "/process/{patient_name}/{study_date}": {
        "quota_type": "api_calls_full_process",
        "amount": 1,
        "description": "完整CT扫描处理"
    },
    "/l3_detect/{patient_name}/{study_date}": {
        "quota_type": "api_calls_l3_detect",
        "amount": 1,
        "description": "L3椎骨检测"
    },
    ...
}

# Exempt paths (no quota checking)
EXEMPT_PATHS = {
    "/health", "/docs", "/list_patients", "/get_key_results", ...
}
```

**Response Headers**:
- `X-Quota-Type` - Quota type consumed
- `X-Quota-Remaining` - Remaining quota after operation
- `X-Quota-Used` - Amount consumed in this request

### 3. Admin Routes (`integrations/admin_routes.py`)

RESTful API for quota monitoring and management:

#### Get User Quotas
```bash
GET /admin/quotas/users/{user_id}
```
Returns all quota limits, usage, and remaining amounts for a user.

#### Get Usage Logs
```bash
GET /admin/quotas/usage-logs?user_id={id}&quota_type={type}&start_date={date}&limit=100
```
Paginated usage logs with filtering options.

#### Get Statistics
```bash
GET /admin/quotas/statistics/{quota_type}?days=30
```
Aggregated statistics: total usage, call count, unique users, peak usage date.

#### Reset Quota
```bash
POST /admin/quotas/users/{user_id}/reset?quota_type={type}
```
Reset quota usage (specific type or all types).

#### Adjust Quota Limit
```bash
PUT /admin/quotas/users/{user_id}/adjust?quota_type={type}&new_limit={amount}
```
Change quota limit for a user (set to -1 for unlimited).

## Quota Types

All quota types registered in the system:

| Type Key | Name | Unit | Default Limit | Description |
|----------|------|------|---------------|-------------|
| `api_calls_full_process` | 完整处理流程 | 次 | 100 | Full CT scan processing |
| `api_calls_l3_detect` | L3椎骨检测 | 次 | 200 | L3 vertebra detection |
| `api_calls_continue` | L3后续处理 | 次 | 200 | Continue after L3 detection |
| `api_calls_preview` | 预览生成 | 次 | 1000 | Preview generation |
| `api_calls_download` | 文件下载 | 次 | 500 | File downloads |
| `storage_dicom` | DICOM存储 | GB | 10 | DICOM file storage |
| `storage_results` | 结果存储 | GB | 5 | Processing results storage |
| `storage_usage` | 存储使用量 | GB | 10 | Total storage usage |
| `api_calls_image_analysis` | 图像分析 | 次 | 50 | AI image analysis |

## Database Schema

### Tables

#### `quota_types`
Defines available quota types in the system.
```sql
CREATE TABLE quota_types (
    id UUID PRIMARY KEY,
    type_key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    unit VARCHAR(50) DEFAULT 'times',
    default_limit DECIMAL(15,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `quota_limits`
Stores per-user quota limits and usage.
```sql
CREATE TABLE quota_limits (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    quota_type_id UUID REFERENCES quota_types(id),
    limit_amount DECIMAL(15,2) NOT NULL,
    used_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    reset_date TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, quota_type_id)
);
```

#### `usage_logs`
Tracks every quota consumption event.
```sql
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    quota_type_id UUID REFERENCES quota_types(id),
    amount DECIMAL(15,2) NOT NULL,
    endpoint VARCHAR(200),
    metadata JSONB,
    created_at TIMESTAMP
);
```

## Configuration

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname
ENABLE_AUTH=true
ENABLE_QUOTA=true

# Optional
ADMIN_TOKEN=your-admin-secret-token
```

### Initialization

1. **Initialize database schema and quota types**:
```bash
python commercial/scripts/init_database.py
```

2. **Initialize quota limits for existing users**:
```bash
python commercial/scripts/init_idoctor_quotas.py
```

3. **Test the system**:
```bash
python commercial/scripts/test_quota_system.py
```

## Integration with Main App

The quota system is integrated in `app.py`:

```python
# 1. Import middleware
from commercial.integrations.middleware.quota_middleware import (
    quota_middleware,
    init_quota_manager
)

# 2. Initialize quota manager
if ENABLE_QUOTA:
    database_url = os.getenv("DATABASE_URL")
    init_quota_manager(database_url)

# 3. Register middleware (after auth middleware)
if ENABLE_QUOTA:
    app.middleware("http")(quota_middleware)

# 4. Register admin routes
if ENABLE_QUOTA:
    from commercial.integrations.admin_routes import router as admin_router
    app.include_router(admin_router)
```

## Usage Flow

### 1. User Makes API Call

```bash
POST /l3_detect/Patient_123/20250115
Authorization: Bearer {jwt_token}
```

### 2. Middleware Flow

```
Request → Auth Middleware (extract user_id)
       → Quota Middleware (check quota)
       → API Endpoint (if quota ok)
       → Response
       → Quota Middleware (consume quota on success)
       → Add quota headers
       → Return to client
```

### 3. Response

```json
HTTP 200 OK
X-Quota-Type: api_calls_l3_detect
X-Quota-Remaining: 199
X-Quota-Used: 1

{
  "status": "success",
  "data": {...}
}
```

### 4. Quota Exceeded

```json
HTTP 402 Payment Required

{
  "detail": "配额已用尽",
  "message": "L3椎骨检测配额不足。剩余: 0.00",
  "quota_type": "api_calls_l3_detect",
  "remaining": 0,
  "required": 1,
  "upgrade_url": "/subscription"
}
```

## Logging

All quota operations are logged with context:

```python
# Quota check
logger.info(
    f"Quota check: user={user_id}, type={quota_type}, "
    f"limit={limit}, used={used}, remaining={remaining}, result={'OK'|'INSUFFICIENT'}"
)

# Quota consumption
logger.info(
    f"Quota consumed: user={user_id}, type={quota_type}, "
    f"amount={amount}, remaining={remaining_after}"
)

# Quota exceeded
logger.warning(
    f"Quota exceeded: user={user_id}, type={quota_type}, "
    f"remaining={remaining}, required={required}"
)
```

## Admin Operations

### View User Quotas

```bash
curl -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  http://localhost:7500/admin/quotas/users/{user_id}
```

### View Usage Logs

```bash
curl -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "http://localhost:7500/admin/quotas/usage-logs?user_id={id}&limit=50"
```

### Reset Monthly Quotas

```bash
# Reset specific quota type
curl -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "http://localhost:7500/admin/quotas/users/{user_id}/reset?quota_type=api_calls_full_process"

# Reset all quotas
curl -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "http://localhost:7500/admin/quotas/users/{user_id}/reset"
```

### Adjust Quota Limit

```bash
# Set to 500
curl -X PUT -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "http://localhost:7500/admin/quotas/users/{user_id}/adjust?quota_type=api_calls_full_process&new_limit=500"

# Set to unlimited
curl -X PUT -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  "http://localhost:7500/admin/quotas/users/{user_id}/adjust?quota_type=api_calls_full_process&new_limit=-1"
```

## Testing

Run the comprehensive test suite:

```bash
cd /Users/mbp/Desktop/Work/Life/IDoctor/iDoctor-backend
python commercial/scripts/test_quota_system.py
```

Tests include:
- ✅ Database connection and schema validation
- ✅ Quota types verification
- ✅ Endpoint pattern matching
- ✅ QuotaManager operations (optional, requires test user)

## Monitoring

### Key Metrics to Track

1. **Quota Usage by Type**
   - Most consumed quota types
   - Users approaching limits
   - Peak usage times

2. **User Behavior**
   - Heavy users (top consumers)
   - Inactive users
   - Users hitting limits frequently

3. **System Health**
   - Average quota consumption rate
   - Response time for quota checks
   - Database query performance

### Usage Analytics

```sql
-- Top users by consumption
SELECT user_id, SUM(amount) as total_usage
FROM usage_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id
ORDER BY total_usage DESC
LIMIT 10;

-- Most popular endpoints
SELECT endpoint, COUNT(*) as call_count
FROM usage_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY endpoint
ORDER BY call_count DESC;

-- Quota exhaustion events
SELECT user_id, quota_type_id, COUNT(*) as denials
FROM usage_logs
WHERE metadata->>'quota_exceeded' = 'true'
GROUP BY user_id, quota_type_id;
```

## Future Enhancements

### Planned Features

1. **Automated Quota Reset**
   - Scheduled task to reset monthly quotas
   - Configurable reset periods (daily/weekly/monthly)

2. **Quota Alerts**
   - Email notifications when approaching limits
   - Admin dashboard for quota monitoring

3. **Usage Reports**
   - Monthly usage summaries for users
   - Export usage data to CSV/Excel

4. **Dynamic Quota Adjustment**
   - Automatically increase limits based on payment tier
   - Promotional quota bonuses

5. **Quota Rollover**
   - Unused quota carries over to next period
   - Maximum rollover limits

## Troubleshooting

### Quota Not Being Checked

1. Verify `ENABLE_QUOTA=true` in environment
2. Check middleware registration in app.py
3. Verify endpoint is not in `EXEMPT_PATHS`
4. Check logs for middleware initialization

### Database Connection Issues

1. Verify `DATABASE_URL` format: `postgresql+asyncpg://...`
2. Test connection: `psql $DATABASE_URL`
3. Check firewall/network settings
4. Verify database exists and tables are created

### Incorrect Quota Consumption

1. Check endpoint pattern matching
2. Verify quota type mapping in `ENDPOINT_QUOTA_MAP`
3. Review usage logs for actual consumption
4. Check metadata in logs for debugging info

## References

- [Integration Design](INTEGRATION_DESIGN.md)
- [Database Schema](../scripts/init_database.py)
- [Quota Manager Code](../integrations/quota_manager.py)
- [Admin Routes API](../integrations/admin_routes.py)
