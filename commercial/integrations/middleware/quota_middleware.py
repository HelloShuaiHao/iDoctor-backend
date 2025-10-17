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
STORAGE_ENDPOINTS = {
    "/upload_dicom_zip": "storage_dicom",
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

    # 跳过免配额路径
    if path in EXEMPT_PATHS or any(path.startswith(p) for p in ["/docs", "/redoc", "/auth/"]):
        return await call_next(request)

    # 只检查 POST 请求（消耗性操作）
    if method != "POST":
        return await call_next(request)

    # 获取用户ID（由认证中间件注入）
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        # 未认证用户不需要配额检查（应该已被认证中间件拦截）
        return await call_next(request)

    # 匹配端点模板
    quota_config = _match_endpoint(path)

    if not quota_config:
        # 该端点不需要配额检查
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

    try:
        # 1. 检查配额
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

        # 2. 执行请求
        response = await call_next(request)

        # 3. 请求成功（2xx状态码）才扣除配额
        if 200 <= response.status_code < 300:
            await quota_manager.consume_quota(
                user_id=user_id,
                quota_type=quota_type,
                amount=required_amount,
                metadata={
                    "endpoint": path,
                    "method": method,
                    "description": description,
                    "patient_name": _extract_param(path, "patient_name") or _extract_param(path, "patient"),
                    "study_date": _extract_param(path, "study_date") or _extract_param(path, "date"),
                }
            )

            # 4. 添加配额信息到响应头
            remaining_after = await quota_manager.get_remaining_quota(user_id, quota_type)
            response.headers["X-Quota-Type"] = quota_type
            response.headers["X-Quota-Remaining"] = str(int(remaining_after))
            response.headers["X-Quota-Used"] = str(required_amount)

            logger.info(
                f"Quota consumed: user={user_id}, type={quota_type}, "
                f"amount={required_amount}, remaining={remaining_after}"
            )

        return response

    except Exception as e:
        logger.error(f"Error in quota middleware: {e}", exc_info=True)
        # 配额检查失败，为了系统可用性，允许通过（可配置策略）
        return await call_next(request)


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
