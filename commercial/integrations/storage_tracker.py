#!/usr/bin/env python3
"""
存储空间追踪和配额管理

功能：
1. 计算用户实际使用的存储空间
2. 按类型统计（DICOM、结果文件、总用量）
3. 同步配额数据库
"""
import os
import logging
from typing import Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def get_directory_size(directory: str) -> int:
    """递归计算目录大小（字节）

    Args:
        directory: 目录路径

    Returns:
        目录总大小（字节）
    """
    total_size = 0
    try:
        for entry in os.scandir(directory):
            if entry.is_file(follow_symlinks=False):
                try:
                    total_size += entry.stat().st_size
                except OSError as e:
                    logger.warning(f"Cannot stat file {entry.path}: {e}")
            elif entry.is_dir(follow_symlinks=False):
                total_size += get_directory_size(entry.path)
    except PermissionError as e:
        logger.warning(f"Permission denied: {directory}")
    except Exception as e:
        logger.error(f"Error calculating directory size for {directory}: {e}")

    return total_size


def bytes_to_gb(bytes_size: int) -> float:
    """将字节转换为GB"""
    return bytes_size / (1024 ** 3)


def bytes_to_mb(bytes_size: int) -> float:
    """将字节转换为MB"""
    return bytes_size / (1024 ** 2)


def calculate_user_storage(user_id: str, data_root: str = "data") -> Dict[str, float]:
    """计算单个用户的存储使用情况

    Args:
        user_id: 用户ID
        data_root: 数据根目录

    Returns:
        字典包含:
        - dicom_mb: DICOM文件大小（MB）
        - results_mb: 处理结果大小（MB）
        - total_mb: 总大小（MB）
        - patient_count: 患者病例数
    """
    user_dir = os.path.join(data_root, str(user_id))

    if not os.path.exists(user_dir):
        logger.info(f"User directory not found: {user_dir}")
        return {
            "dicom_mb": 0.0,
            "results_mb": 0.0,
            "total_mb": 0.0,
            "patient_count": 0
        }

    dicom_bytes = 0
    results_bytes = 0
    patient_count = 0

    try:
        # 遍历用户的所有患者目录
        for patient_folder in os.listdir(user_dir):
            patient_path = os.path.join(user_dir, patient_folder)
            if not os.path.isdir(patient_path):
                continue

            patient_count += 1

            # 计算 input 目录（DICOM文件）
            input_dir = os.path.join(patient_path, "input")
            if os.path.exists(input_dir):
                dicom_bytes += get_directory_size(input_dir)

            # 计算 output 目录（处理结果）
            output_dir = os.path.join(patient_path, "output")
            if os.path.exists(output_dir):
                results_bytes += get_directory_size(output_dir)

    except Exception as e:
        logger.error(f"Error calculating storage for user {user_id}: {e}")

    return {
        "dicom_mb": bytes_to_mb(dicom_bytes),
        "results_mb": bytes_to_mb(results_bytes),
        "total_mb": bytes_to_mb(dicom_bytes + results_bytes),
        "patient_count": patient_count
    }


async def sync_storage_quota_to_db(user_id: str, quota_manager, data_root: str = "data"):
    """同步用户实际存储使用到配额数据库

    Args:
        user_id: 用户ID
        quota_manager: QuotaManager实例
        data_root: 数据根目录
    """
    storage_info = calculate_user_storage(user_id, data_root)

    logger.info(
        f"User {user_id} storage: DICOM={storage_info['dicom_mb']:.2f}MB, "
        f"Results={storage_info['results_mb']:.2f}MB, "
        f"Total={storage_info['total_mb']:.2f}MB, "
        f"Cases={storage_info['patient_count']}"
    )

    # 同步各类存储配额的已用量
    # 这个函数用于在上传后实时更新实际使用量到数据库

    try:
        # 更新存储配额
        from sqlalchemy import text
        async with quota_manager.async_session() as session:
            async with session.begin():
                # 更新 DICOM 存储
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'storage_dicom')
                """), {"user_id": str(user_id), "used_amount": storage_info['dicom_mb']})

                # 更新结果存储
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'storage_results')
                """), {"user_id": str(user_id), "used_amount": storage_info['results_mb']})

                # 更新总存储
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'storage_usage')
                """), {"user_id": str(user_id), "used_amount": storage_info['total_mb']})

                # 更新病例数量
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'patient_cases')
                """), {"user_id": str(user_id), "used_amount": storage_info['patient_count']})

        logger.info(f"✅ Synced storage quota to database for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to sync storage quota for user {user_id}: {e}")
        return False


def calculate_file_size_from_upload(file) -> float:
    """从 UploadFile 对象计算文件大小（MB）

    Args:
        file: FastAPI UploadFile 对象

    Returns:
        文件大小（MB）
    """
    try:
        # 方法1：如果文件有 size 属性
        if hasattr(file, 'size') and file.size:
            return bytes_to_mb(file.size)

        # 方法2：读取文件内容
        content = file.file.read()
        file.file.seek(0)  # 重置文件指针
        return bytes_to_mb(len(content))

    except Exception as e:
        logger.error(f"Error calculating file size: {e}")
        return 0.0


async def check_storage_quota_before_upload(
    user_id: str,
    file_size_mb: float,
    quota_manager,
    quota_type: str = "storage_usage"
) -> Tuple[bool, str]:
    """上传前检查存储配额

    Args:
        user_id: 用户ID
        file_size_mb: 文件大小（MB）
        quota_manager: QuotaManager实例
        quota_type: 配额类型（storage_dicom, storage_results, storage_usage）

    Returns:
        (是否有足够配额, 错误消息)
    """
    try:
        has_quota = await quota_manager.check_quota(
            user_id=user_id,
            quota_type=quota_type,
            amount=file_size_mb
        )

        if not has_quota:
            remaining = await quota_manager.get_remaining_quota(user_id, quota_type)
            message = (
                f"存储空间不足。需要: {file_size_mb:.2f}MB, "
                f"剩余: {remaining:.2f}MB。请升级套餐或删除旧数据。"
            )
            return False, message

        return True, ""

    except Exception as e:
        logger.error(f"Error checking storage quota: {e}")
        # 检查失败时允许上传（可配置策略）
        return True, ""
