#!/usr/bin/env python3
"""
同步所有用户的存储使用情况到配额数据库

用法:
    python commercial/scripts/sync_storage_usage.py [--user-id USER_ID]

选项:
    --user-id    只同步指定用户（可选）
"""
import asyncio
import sys
import os
import argparse
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from commercial.integrations.quota_manager import QuotaManager
from commercial.integrations.storage_tracker import calculate_user_storage

try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_all_users(engine):
    """获取所有用户ID"""
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT id, username, email FROM users"))
        return result.fetchall()


async def sync_user_storage(quota_manager, user_id: str, data_root: str = "data"):
    """同步单个用户的存储使用情况"""
    try:
        # 计算实际存储使用
        storage_info = calculate_user_storage(user_id, data_root)

        logger.info(
            f"📊 用户 {user_id}: "
            f"DICOM={storage_info['dicom_gb']:.3f}GB, "
            f"结果={storage_info['results_gb']:.3f}GB, "
            f"总计={storage_info['total_gb']:.3f}GB, "
            f"病例数={storage_info['patient_count']}"
        )

        # 更新数据库
        async with quota_manager.async_session() as session:
            async with session.begin():
                # 更新 DICOM 存储
                result = await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'storage_dicom')
                """), {"user_id": str(user_id), "used_amount": storage_info['dicom_gb']})

                # 更新结果存储
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'storage_results')
                """), {"user_id": str(user_id), "used_amount": storage_info['results_gb']})

                # 更新总存储
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'storage_usage')
                """), {"user_id": str(user_id), "used_amount": storage_info['total_gb']})

                # 更新病例数量
                await session.execute(text("""
                    UPDATE quota_limits
                    SET used_amount = :used_amount, updated_at = NOW()
                    WHERE user_id = :user_id
                      AND quota_type_id = (SELECT id FROM quota_types WHERE type_key = 'patient_cases')
                """), {"user_id": str(user_id), "used_amount": storage_info['patient_count']})

        logger.info(f"✅ 已同步用户 {user_id} 的存储配额")
        return True

    except Exception as e:
        logger.error(f"❌ 同步用户 {user_id} 失败: {e}")
        return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="同步用户存储使用情况到配额数据库")
    parser.add_argument("--user-id", help="只同步指定用户ID")
    parser.add_argument("--data-root", default="data", help="数据根目录（默认: data）")
    args = parser.parse_args()

    logger.info("🚀 开始同步存储使用情况...")

    # 初始化
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    quota_manager = QuotaManager(settings.DATABASE_URL)

    try:
        if args.user_id:
            # 同步单个用户
            logger.info(f"📝 同步用户: {args.user_id}")
            success = await sync_user_storage(quota_manager, args.user_id, args.data_root)
            if success:
                logger.info("✅ 同步完成")
            else:
                logger.error("❌ 同步失败")
                sys.exit(1)
        else:
            # 同步所有用户
            users = await get_all_users(engine)
            logger.info(f"📝 找到 {len(users)} 个用户")

            success_count = 0
            fail_count = 0

            for user_id, username, email in users:
                logger.info(f"\n处理用户: {username} ({email})")
                success = await sync_user_storage(quota_manager, str(user_id), args.data_root)
                if success:
                    success_count += 1
                else:
                    fail_count += 1

            logger.info("\n" + "="*60)
            logger.info(f"📊 同步完成: 成功={success_count}, 失败={fail_count}")
            logger.info("="*60)

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()
        await quota_manager.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
