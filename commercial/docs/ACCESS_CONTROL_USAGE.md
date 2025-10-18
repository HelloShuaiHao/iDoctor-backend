# 用户数据访问控制使用指南

## 概述

`access_control.py` 模块提供用户数据隔离和访问权限验证功能，确保用户只能访问自己的数据。

## 核心功能

### 1. 验证数据所有权

```python
from commercial.integrations.access_control import require_data_ownership

@app.get("/get_key_results/{patient_name}/{study_date}")
async def get_results(
    request: Request,
    patient_name: str,
    study_date: str
):
    # 获取用户ID
    user_id = getattr(request.state, "user_id", None)

    # 验证用户是否拥有该数据（如果没有，自动返回 403）
    require_data_ownership(user_id, patient_name, study_date)

    # 继续处理...
    return {"status": "ok"}
```

### 2. 列出用户的所有病例

```python
from commercial.integrations.access_control import list_user_patients

@app.get("/list_patients")
async def list_patients(request: Request):
    user_id = getattr(request.state, "user_id", None)

    patients = list_user_patients(user_id)

    return {
        "total": len(patients),
        "patients": patients
    }
```

### 3. 清理孤立数据

```python
from commercial.integrations.access_control import cleanup_orphaned_data

# 定期任务或管理命令
async def cleanup_task():
    # 先检查（不删除）
    orphaned = await cleanup_orphaned_data(dry_run=True)
    print(f"找到 {len(orphaned)} 个孤立目录")

    # 确认后删除
    orphaned = await cleanup_orphaned_data(dry_run=False)
    print(f"已删除 {len(orphaned)} 个孤立目录")
```

## 集成到现有端点

### 需要添加访问控制的端点

```python
# app.py 中需要添加访问控制的端点示例

@app.post("/continue_after_l3/{patient_name}/{study_date}")
async def continue_after_l3(request: Request, patient_name: str, study_date: str):
    user_id = getattr(request.state, "user_id", None)

    # ✅ 添加访问控制
    from commercial.integrations.access_control import require_data_ownership
    require_data_ownership(user_id, patient_name, study_date)

    # 原有逻辑...
    pass

@app.get("/get_image/{patient_name}/{study_date}/{filename}")
async def get_image(request: Request, patient_name: str, study_date: str, filename: str):
    user_id = getattr(request.state, "user_id", None)

    # ✅ 添加访问控制
    from commercial.integrations.access_control import require_data_ownership
    require_data_ownership(user_id, patient_name, study_date)

    # 原有逻辑...
    pass
```

## 批量应用到所有端点

创建一个装饰器来简化应用：

```python
from functools import wraps
from commercial.integrations.access_control import require_data_ownership

def require_patient_access(patient_param: str = "patient_name", date_param: str = "study_date"):
    """装饰器：要求用户拥有患者数据访问权限"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = getattr(request.state, "user_id", None)
            patient_name = kwargs.get(patient_param)
            study_date = kwargs.get(date_param)

            require_data_ownership(user_id, patient_name, study_date)

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@app.get("/get_results/{patient_name}/{study_date}")
@require_patient_access()
async def get_results(request: Request, patient_name: str, study_date: str):
    # 自动验证访问权限
    return {"status": "ok"}
```

## 测试

```bash
# 测试访问控制
curl -H "Authorization: Bearer <user1_token>" \
     http://localhost:4200/get_results/John_Doe/20250101

# 应该成功（用户自己的数据）

curl -H "Authorization: Bearer <user1_token>" \
     http://localhost:4200/get_results/Jane_Doe/20250101

# 应该返回 403 Forbidden（其他用户的数据）
```

## 日志输出

启用访问控制后，日志会记录：

```
✅ 访问授权: 用户 123e4567-e89b-12d3-a456-426614174000 访问 John_Doe_20250101
❌ 访问拒绝: 用户 123e4567-e89b-12d3-a456-426614174000 试图访问 Jane_Doe_20250101
```

## 注意事项

1. **性能考虑**: 访问控制检查只验证目录存在性，开销很小
2. **缓存**: 可以考虑缓存用户的患者列表以提升性能
3. **审计**: 所有访问拒绝都会被记录到日志
4. **管理员**: 超级管理员可能需要特殊处理（跳过检查）
