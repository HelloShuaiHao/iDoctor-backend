#!/usr/bin/env python3
"""
usage_logs 表结构迁移脚本

检查 usage_logs 表结构，如果是旧版本则自动迁移到新版本
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

try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_and_migrate():
    """检查并迁移 usage_logs 表"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # 1. 检查表是否存在
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'usage_logs'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                logger.info("✅ usage_logs 表不存在，将由 init_database.py 创建")
                return

            # 2. 检查表结构
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'usage_logs'
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result.fetchall()]

            logger.info(f"📋 当前 usage_logs 表字段: {columns}")

            # 3. 判断是否需要迁移
            has_quota_type_id = 'quota_type_id' in columns
            has_subscription_id = 'subscription_id' in columns

            if has_quota_type_id and not has_subscription_id:
                logger.info("✅ usage_logs 表结构已是最新版本，无需迁移")
                return

            if has_subscription_id and not has_quota_type_id:
                logger.warning("⚠️  检测到旧版本 usage_logs 表结构，开始迁移...")
                await migrate_table(conn)
            else:
                logger.error(f"❌ 未知的表结构: {columns}")
                raise Exception("Unexpected table structure")

    except Exception as e:
        logger.error(f"❌ 迁移检查失败: {e}")
        raise
    finally:
        await engine.dispose()


async def migrate_table(conn):
    """执行表迁移"""
    try:
        # 1. 检查是否有数据需要备份
        result = await conn.execute(text("SELECT COUNT(*) FROM usage_logs"))
        count = result.scalar()
        logger.info(f"📊 当前有 {count} 条记录")

        if count > 0:
            logger.info("💾 创建备份表...")
            await conn.execute(text("""
                DROP TABLE IF EXISTS usage_logs_backup_old CASCADE
            """))
            await conn.execute(text("""
                CREATE TABLE usage_logs_backup_old AS
                SELECT * FROM usage_logs
            """))
            logger.info("✅ 已备份到 usage_logs_backup_old")

        # 2. 删除旧表
        logger.info("🗑️  删除旧表...")
        await conn.execute(text("DROP TABLE IF EXISTS usage_logs CASCADE"))

        # 3. 创建新表
        logger.info("🏗️  创建新表结构...")
        await conn.execute(text("""
            CREATE TABLE usage_logs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                quota_type_id UUID NOT NULL REFERENCES quota_types(id) ON DELETE CASCADE,
                amount DECIMAL(15,2) NOT NULL,
                endpoint VARCHAR(200),
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))

        # 4. 创建索引
        logger.info("📇 创建索引...")
        await conn.execute(text("""
            CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id)
        """))
        await conn.execute(text("""
            CREATE INDEX idx_usage_logs_quota_type_id ON usage_logs(quota_type_id)
        """))
        await conn.execute(text("""
            CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at)
        """))

        logger.info("✅ usage_logs 表迁移完成！")
        logger.info("📋 新表结构:")
        logger.info("   - id (UUID)")
        logger.info("   - user_id (UUID -> users)")
        logger.info("   - quota_type_id (UUID -> quota_types)")
        logger.info("   - amount (DECIMAL)")
        logger.info("   - endpoint (VARCHAR)")
        logger.info("   - metadata (JSONB)")
        logger.info("   - created_at (TIMESTAMP)")

    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        raise


async def main():
    """主函数"""
    logger.info("🔍 检查 usage_logs 表结构...")
    try:
        await check_and_migrate()
        logger.info("✅ 迁移检查完成")
    except Exception as e:
        logger.error(f"❌ 失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
