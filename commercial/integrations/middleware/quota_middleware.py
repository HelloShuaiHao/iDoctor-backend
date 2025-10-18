"""FastAPI配额检查中间件

自动检查和扣除用户配额，支持多种配额类型
"""
import logging
import re
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from integrations.quota_manager import QuotaManager
from shared.config import settings

logger = logging.getLogger(__name__)

# 端点路径模板与配额类型的映射
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
    "/continue_after_l3/{patient_name}/{study_date}": {
        "quota_type": "api_calls_continue",
        "amount": 1,
        "description": "L3后续处理"
    },
}

# 存储空间配额（需要特殊处理）
# 注意：/upload_dicom_zip 已改为按次数扣除（在 ENDPOINT_QUOTA_MAP 中）
STORAGE_ENDPOINTS = {
    "/upload_l3_mask/{patient}/{date}": "storage_results",
    "/upload_middle_manual_mask/{patient}/{date}": "storage_results"
}

# 无需配额检查的路径（查询类操作）
EXEMPT_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/list_patients",
    "/task_status",
    "/get_key_results",
    "/get_image",
    "/get_output_image",
    "/debug_log",
    "/generate_sagittal",  # 仅生成预览，不算配额
}

# 初始化配额管理器
quota_manager = None


def init_quota_manager(db_url: str):
    """初始化配额管理器（在应用启动时调用）"""
    global quota_manager
    quota_manager = QuotaManager(db_url)
    logger.info("Quota manager initialized")


async def quota_middleware(request: Request, call_next):
    """配额检查中间件

    功能:
    1. 检查请求是否需要配额验证
    2. 请求前检查配额是否充足
    3. 请求成功后扣除配额
    4. 添加响应头显示剩余配额
    """
    global quota_manager

    if quota_manager is None:
        # 配额管理器未初始化，跳过检查
        logger.warning("Quota manager not initialized, skipping quota check")
        return await call_next(request)

    path = request.url.path
    method = request.method

    logger.debug(f"Quota middleware: path={path}, method={method}")

    # 跳过免配额路径
    if path in EXEMPT_PATHS or any(path.startswith(p) for p in ["/docs", "/redoc", "/auth/"]):
        logger.debug(f"Skipping exempt path: {path}")
        return await call_next(request)

    # 只检查 POST 请求（消耗性操作）
    if method != "POST":
        logger.debug(f"Skipping non-POST method: {method}")
        return await call_next(request)

    # 获取用户ID（由认证中间件注入）
    user_id = getattr(request.state, "user_id", None)
    logger.debug(f"User ID from request.state: {user_id}")
    if not user_id:
        # 未认证用户不需要配额检查（应该已被认证中间件拦截）
        logger.warning(f"No user_id in request.state for {path}, skipping quota check")
        return await call_next(request)

    # 匹配端点模板
    quota_config = _match_endpoint(path)
    logger.debug(f"Quota config for {path}: {quota_config}")

    if not quota_config:
        # 该端点不需要配额检查
        logger.debug(f"No quota config found for {path}, skipping")
        return await call_next(request)

    quota_type = quota_config["quota_type"]
    required_amount = quota_config["amount"]
    description = quota_config["description"]

    # 存储空间配额特殊处理（需要从请求中获取文件大小）
    if quota_type.startswith("storage_"):
        required_amount = await _calculate_storage_amount(request)
        if required_amount is None:
            # 无法获取文件大小，允许通过（或根据策略拒绝）
            logger.warning(f"Cannot determine file size for {path}, skipping quota check")
            return await call_next(request)

    # 1. 检查配额
    try:
        has_quota = await quota_manager.check_quota(
            user_id=user_id,
            quota_type=quota_type,
            amount=required_amount
        )

        if not has_quota:
            remaining = await quota_manager.get_remaining_quota(user_id, quota_type)
            logger.warning(
                f"Quota exceeded: user={user_id}, type={quota_type}, "
                f"remaining={remaining}, required={required_amount}"
            )

            return JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={
                    "detail": "配额已用尽",
                    "message": f"{description}配额不足。剩余: {remaining:.2f}",
                    "quota_type": quota_type,
                    "remaining": remaining,
                    "required": required_amount,
                    "upgrade_url": "/subscription"  # 前端升级页面
                }
            )
    except Exception as e:
        logger.error(f"Error checking quota: {e}", exc_info=True)
        # 配额检查失败，为了系统可用性，允许通过
        return await call_next(request)

    # 2. 执行请求（无论成功失败都会扣配额，因为已经消耗了资源）
    response = None
    request_succeeded = False

    try:
        response = await call_next(request)
        request_succeeded = True
        logger.info(f"Request completed with status: {response.status_code}")
    except Exception as e:
        # 请求执行过程中发生异常，返回500错误
        logger.error(f"Error during request execution: {e}", exc_info=True)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "处理请求时发生错误",
                "message": str(e)
            }
        )

    # 3. 扣除配额（无论请求成功还是失败）
    # 原因：只要配额检查通过了，就说明资源已经被使用（模型加载、数据处理等）
    try:
        logger.info(f"Consuming quota: user={user_id}, type={quota_type}, amount={required_amount}")
        remaining_after = await quota_manager.consume_quota(
            user_id=user_id,
            quota_type=quota_type,
            amount=required_amount,
            metadata={
                "endpoint": path,
                "method": method,
                "description": description,
                "patient_name": _extract_param(path, "patient_name") or _extract_param(path, "patient"),
                "study_date": _extract_param(path, "study_date") or _extract_param(path, "date"),
                "status_code": response.status_code if response else 500,
                "success": request_succeeded
            }
        )

        # 4. 添加配额信息到响应头
        if remaining_after is not None:
            response.headers["X-Quota-Type"] = quota_type
            response.headers["X-Quota-Remaining"] = str(int(remaining_after))
            response.headers["X-Quota-Used"] = str(required_amount)

            logger.info(
                f"Quota consumed: user={user_id}, type={quota_type}, "
                f"amount={required_amount}, remaining={remaining_after}, "
                f"status={response.status_code}"
            )
        else:
            logger.error(f"Failed to consume quota, remaining=None")
    except Exception as e:
        logger.error(f"Error consuming quota: {e}", exc_info=True)
        # 配额扣除失败不影响响应返回

    return response


def _match_endpoint(path: str) -> Optional[Dict[str, Any]]:
    """匹配路径到配额配置

    将实际路径（如 /process/John_Doe/20250101）匹配到模板
    （如 /process/{patient_name}/{study_date}）
    """
    for template, config in ENDPOINT_QUOTA_MAP.items():
        if _path_matches_template(path, template):
            return config

    # 检查存储端点
    for template, quota_type in STORAGE_ENDPOINTS.items():
        if _path_matches_template(path, template):
            return {
                "quota_type": quota_type,
                "amount": 0,  # 需要动态计算
                "description": "文件存储"
            }

    return None


def _path_matches_template(path: str, template: str) -> bool:
    """检查路径是否匹配模板

    Examples:
        /process/John_Doe/20250101 matches /process/{patient_name}/{study_date}
        /l3_detect/John/20250101 matches /l3_detect/{patient_name}/{study_date}
    """
    # 将模板转换为正则表达式
    pattern = re.sub(r'\{[^}]+\}', r'[^/]+', template)
    pattern = f"^{pattern}$"
    return re.match(pattern, path) is not None


def _extract_param(path: str, param_name: str) -> Optional[str]:
    """从路径中提取参数值

    Examples:
        path="/process/John_Doe/20250101", param="patient_name" -> "John_Doe"
    """
    # 简化实现：按顺序提取
    parts = path.split("/")
    if "patient_name" in param_name or param_name == "patient":
        return parts[2] if len(parts) > 2 else None
    if "study_date" in param_name or param_name == "date":
        return parts[3] if len(parts) > 3 else None
    return None


async def _calculate_storage_amount(request: Request) -> Optional[float]:
    """计算存储空间消耗（GB）

    从请求中提取文件大小
    """
    try:
        # 方法1: 从 Content-Length header
        content_length = request.headers.get("Content-Length")
        if content_length:
            bytes_size = int(content_length)
            gb_size = bytes_size / (1024 ** 3)
            return gb_size

        # 方法2: 从表单数据 (file_size字段)
        if request.method == "POST":
            form = await request.form()
            file_size = form.get("file_size")
            if file_size:
                bytes_size = int(file_size)
                gb_size = bytes_size / (1024 ** 3)
                return gb_size

        return None

    except Exception as e:
        logger.error(f"Error calculating storage amount: {e}")
        return None


def add_endpoint_quota(template: str, quota_type: str, amount: float = 1, description: str = ""):
    """动态添加端点配额映射"""
    ENDPOINT_QUOTA_MAP[template] = {
        "quota_type": quota_type,
        "amount": amount,
        "description": description
    }
    logger.info(f"Added endpoint quota mapping: {template} -> {quota_type}")
