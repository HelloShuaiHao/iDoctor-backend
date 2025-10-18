#!/usr/bin/env python3
"""
用户数据访问控制

确保用户只能访问自己的数据
"""
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def verify_user_owns_patient_data(user_id: str, patient_name: str, study_date: str, data_root: str = "data") -> bool:
    """验证用户是否拥有指定的患者数据

    Args:
        user_id: 用户ID
        patient_name: 患者名称
        study_date: 研究日期
        data_root: 数据根目录

    Returns:
        True if user owns the data, False otherwise
    """
    import os

    # 构建预期的路径
    expected_path = os.path.join(data_root, str(user_id), f"{patient_name}_{study_date}")

    # 检查目录是否存在
    if not os.path.exists(expected_path):
        logger.warning(f"Patient data not found: {expected_path}")
        return False

    logger.debug(f"✅ User {user_id} owns patient data: {patient_name}_{study_date}")
    return True


def require_data_ownership(user_id: str, patient_name: str, study_date: str, data_root: str = "data"):
    """要求用户拥有数据，否则抛出 HTTP 异常

    Args:
        user_id: 用户ID
        patient_name: 患者名称
        study_date: 研究日期
        data_root: 数据根目录

    Raises:
        HTTPException: 403 if user doesn't own the data
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要身份验证"
        )

    if not verify_user_owns_patient_data(user_id, patient_name, study_date, data_root):
        logger.warning(f"❌ 访问拒绝: 用户 {user_id} 试图访问 {patient_name}_{study_date}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有权限访问此数据"
        )

    logger.debug(f"✅ 访问授权: 用户 {user_id} 访问 {patient_name}_{study_date}")


def list_user_patients(user_id: str, data_root: str = "data") -> list:
    """列出用户的所有患者病例

    Args:
        user_id: 用户ID
        data_root: 数据根目录

    Returns:
        患者病例列表 [(patient_name, study_date, path), ...]
    """
    import os

    user_dir = os.path.join(data_root, str(user_id))

    if not os.path.exists(user_dir):
        return []

    patients = []
    try:
        for folder in os.listdir(user_dir):
            folder_path = os.path.join(user_dir, folder)
            if not os.path.isdir(folder_path):
                continue

            # 解析文件夹名称 (格式: patient_name_study_date)
            parts = folder.rsplit("_", 1)
            if len(parts) == 2:
                patient_name, study_date = parts
                patients.append({
                    "patient_name": patient_name,
                    "study_date": study_date,
                    "folder_name": folder,
                    "path": folder_path
                })

    except Exception as e:
        logger.error(f"Error listing patients for user {user_id}: {e}")

    return patients


async def cleanup_orphaned_data(data_root: str = "data", dry_run: bool = True):
    """清理没有对应用户的数据

    Args:
        data_root: 数据根目录
        dry_run: 如果为True，只报告不删除

    Returns:
        清理的目录列表
    """
    import os
    import shutil
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    try:
        from shared.config import settings
    except ImportError:
        from commercial.shared.config import settings

    orphaned = []

    # 获取所有用户ID
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id FROM users"))
        valid_user_ids = {str(row[0]) for row in result.fetchall()}

    await engine.dispose()

    # 扫描数据目录
    if not os.path.exists(data_root):
        return orphaned

    for dir_name in os.listdir(data_root):
        dir_path = os.path.join(data_root, dir_name)

        if not os.path.isdir(dir_path):
            continue

        # 检查是否是有效的用户ID
        if dir_name not in valid_user_ids:
            orphaned.append(dir_path)
            logger.warning(f"发现孤立数据: {dir_path}")

            if not dry_run:
                shutil.rmtree(dir_path)
                logger.info(f"🗑️  已删除: {dir_path}")

    if dry_run and orphaned:
        logger.info(f"⚠️  DRY RUN: 发现 {len(orphaned)} 个孤立目录（未删除）")

    return orphaned
