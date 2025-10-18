#!/usr/bin/env python3
"""
同步所有用户的实际存储使用量

遍历所有用户，计算实际磁盘使用量并更新到数据库
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
from integrations.storage_tracker import sync_storage_quota_to_db
from integrations.quota_manager import QuotaManager
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_all_users():
    """同步所有用户的存储使用量"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL 未配置")
        sys.exit(1)

    data_root = os.getenv("DATA_ROOT", "data")
    engine = create_async_engine(db_url, echo=False)
    quota_manager = QuotaManager(db_url)

    try:
        # 获取所有用户
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT id, username FROM users ORDER BY username"))
            users = result.fetchall()

        if not users:
            logger.warning("⚠️  没有找到用户")
            return

        logger.info(f"找到 {len(users)} 个用户，开始同步存储使用量...\n")

        success_count = 0
        failed_count = 0

        for user_id, username in users:
            try:
                logger.info(f"同步用户: {username} ({user_id})")
                success = await sync_storage_quota_to_db(str(user_id), quota_manager, data_root)

                if success:
                    success_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"  ❌ 失败: {e}")
                failed_count += 1

        logger.info("\n" + "=" * 60)
        logger.info(f"同步完成: 成功 {success_count}, 失败 {failed_count}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("同步所有用户存储使用量")
    logger.info("=" * 60)
    asyncio.run(sync_all_users())
