"""初始化订阅计划"""
import asyncio
import sys
import os
import logging
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_plans():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    plans = [
        {
            "name": "免费版",
            "description": "适合个人用户试用，每月10次处理",
            "price": Decimal("0.00"),
            "currency": "CNY",
            "billing_cycle": "monthly",
            "quota_type": "processing_count",
            "quota_limit": 10,
            "features": {
                "max_concurrent": 1,
                "priority": "low",
                "support": "community"
            }
        },
        {
            "name": "专业版",
            "description": "适合小型团队，每月100次处理",
            "price": Decimal("99.00"),
            "currency": "CNY",
            "billing_cycle": "monthly",
            "quota_type": "processing_count",
            "quota_limit": 100,
            "features": {
                "max_concurrent": 3,
                "priority": "medium",
                "support": "email"
            }
        },
        {
            "name": "企业版",
            "description": "大型医院使用，无限次处理",
            "price": Decimal("999.00"),
            "currency": "CNY",
            "billing_cycle": "monthly",
            "quota_type": "processing_count",
            "quota_limit": 999999,
            "features": {
                "max_concurrent": 10,
                "priority": "high",
                "support": "dedicated",
                "custom_features": True
            }
        }
    ]

    try:
        async with async_session() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS plans (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) NOT NULL,
                    currency VARCHAR(10) DEFAULT 'CNY',
                    billing_cycle VARCHAR(50) DEFAULT 'monthly',
                    quota_type VARCHAR(100),
                    quota_limit DECIMAL(15,2),
                    features JSONB,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))

            result = await session.execute(text("SELECT COUNT(*) FROM plans"))
            if result.scalar() > 0:
                logger.info("已存在订阅计划，跳过初始化")
                await session.commit()
                return

            insert_sql = text("""
                INSERT INTO plans
                (name, description, price, currency, billing_cycle, quota_type, quota_limit, features)
                VALUES
                (:name, :description, :price, :currency, :billing_cycle, :quota_type, :quota_limit, :features)
            """)

            for p in plans:
                await session.execute(
                    insert_sql,
                    {
                        "name": p["name"],
                        "description": p["description"],
                        "price": float(p["price"]),
                        "currency": p["currency"],
                        "billing_cycle": p["billing_cycle"],
                        "quota_type": p["quota_type"],
                        "quota_limit": p["quota_limit"],
                        "features": p["features"]  # 直接传 dict
                    }
                )
                logger.info(f"创建计划: {p['name']}")

            await session.commit()
            logger.info(f"成功创建 {len(plans)} 个订阅计划")

    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


async def main():
    logger.info("开始初始化订阅计划...")
    try:
        await seed_plans()
        logger.info("完成")
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())