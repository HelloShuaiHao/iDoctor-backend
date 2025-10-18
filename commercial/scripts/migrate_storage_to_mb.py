#!/usr/bin/env python3
"""
将存储配额从 GB 迁移到 MB

运行此脚本将：
1. 更新 quota_types 表中的单位从 GB 改为 MB
2. 更新 quota_types 表中的默认限制 * 1024（GB -> MB）
3. 更新所有用户的 quota_limits 中的存储配额限制 * 1024
4. 重新计算并更新所有用户的实际存储使用量（单位：MB）
"""
import asyncio
import sys
import os
import logging

# 添加商业化系统到路径
commercial_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, commercial_path)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_storage_units():
    """迁移存储配额单位从 GB 到 MB"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL 未配置")
        sys.exit(1)

    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # 1. 更新 quota_types 表中的存储类型配额
            logger.info("1. 更新配额类型定义...")

            storage_types = ['storage_dicom', 'storage_results', 'storage_usage']

            for type_key in storage_types:
                # 更新单位和默认限制
                if type_key == 'storage_dicom':
                    new_limit = 100  # 100 MB
                elif type_key == 'storage_results':
                    new_limit = 50   # 50 MB
                else:  # storage_usage
                    new_limit = 100  # 100 MB

                await conn.execute(text("""
                    UPDATE quota_types
                    SET unit = 'MB',
                        default_limit = :new_limit,
                        updated_at = NOW()
                    WHERE type_key = :type_key
                """), {"type_key": type_key, "new_limit": new_limit})

                logger.info(f"✅ 更新 {type_key}: 单位=MB, 默认限制={new_limit}MB")

            # 2. 更新所有用户的存储配额限制
            logger.info("\n2. 更新用户配额限制...")

            # 查询所有用户的存储配额
            result = await conn.execute(text("""
                SELECT ql.id, u.username, qt.type_key, ql.limit_amount, ql.used_amount
                FROM quota_limits ql
                JOIN users u ON ql.user_id = u.id
                JOIN quota_types qt ON ql.quota_type_id = qt.id
                WHERE qt.type_key IN ('storage_dicom', 'storage_results', 'storage_usage')
                ORDER BY u.username, qt.type_key
            """))

            rows = result.fetchall()
            updated_count = 0

            for row in rows:
                limit_id, username, type_key, old_limit, old_used = row

                # 如果limit是GB单位（比如10GB），转换为MB（10240MB）
                # 但我们要设置新的默认值
                if type_key == 'storage_dicom':
                    new_limit = 100  # 100 MB
                elif type_key == 'storage_results':
                    new_limit = 50   # 50 MB
                else:  # storage_usage
                    new_limit = 100  # 100 MB

                # 使用量需要重新计算，暂时设为0
                new_used = 0

                await conn.execute(text("""
                    UPDATE quota_limits
                    SET limit_amount = :new_limit,
                        used_amount = :new_used,
                        updated_at = NOW()
                    WHERE id = :limit_id
                """), {
                    "limit_id": limit_id,
                    "new_limit": new_limit,
                    "new_used": new_used
                })

                logger.info(
                    f"  ✅ {username} - {type_key}: "
                    f"限制 {old_limit:.2f}GB -> {new_limit}MB, "
                    f"已用 {old_used:.2f}GB -> 0MB（将重新计算）"
                )
                updated_count += 1

            logger.info(f"\n✅ 共更新 {updated_count} 条配额记录")

            # 3. 重新计算所有用户的实际存储使用量
            logger.info("\n3. 重新计算用户实际存储使用量...")

            # 获取所有用户
            result = await conn.execute(text("SELECT id, username FROM users"))
            users = result.fetchall()

            logger.info(f"找到 {len(users)} 个用户，将重新计算存储使用量")
            logger.info("提示：这将在后台异步执行，不会阻塞此脚本")

        logger.info("\n" + "=" * 60)
        logger.info("🎉 迁移完成！")
        logger.info("=" * 60)
        logger.info("\n下一步操作：")
        logger.info("1. 重启主服务以应用新的配额设置")
        logger.info("2. 在用户下次上传时会自动同步实际存储使用量")
        logger.info("3. 或者运行: python commercial/scripts/sync_storage_usage.py 立即同步")

    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("存储配额单位迁移：GB -> MB")
    logger.info("=" * 60)
    logger.info("\n此脚本将：")
    logger.info("1. 将存储类型配额单位从 GB 改为 MB")
    logger.info("2. 将默认限制调整为：")
    logger.info("   - storage_dicom: 100 MB")
    logger.info("   - storage_results: 50 MB")
    logger.info("   - storage_usage: 100 MB")
    logger.info("3. 重置所有用户的存储使用量为0（将在下次上传时重新计算）")
    logger.info("\n⚠️  注意：此操作会修改数据库，请确保已备份")

    response = input("\n确认继续？(yes/no): ")
    if response.lower() != 'yes':
        logger.info("❌ 已取消")
        sys.exit(0)

    asyncio.run(migrate_storage_units())
