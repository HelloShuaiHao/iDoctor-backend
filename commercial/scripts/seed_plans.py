"""初始化订阅计划（直接写入 subscription_plans）"""
import asyncio
import sys
import os
import logging
import json
from decimal import Decimal
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLANS = [
    {
        "name": "免费版",
        "description": "适合个人试用，每月限量",
        "price": Decimal("0.00"),
        "currency": "CNY",
        "billing_cycle": "monthly",
        "quota_type": "processing_count",
        "quota_limit": 10,
        "features": {"max_concurrent": 1, "priority": "low", "support": "community"}
    },
    {
        "name": "专业版",
        "description": "团队使用，中等配额",
        "price": Decimal("99.00"),
        "currency": "CNY",
        "billing_cycle": "monthly",
        "quota_type": "processing_count",
        "quota_limit": 100,
        "features": {"max_concurrent": 3, "priority": "medium", "support": "email"}
    },
    {
        "name": "企业版",
        "description": "高并发与高级支持",
        "price": Decimal("999.00"),
        "currency": "CNY",
        "billing_cycle": "monthly",
        "quota_type": "processing_count",
        "quota_limit": 999999,
        "features": {"max_concurrent": 10, "priority": "high", "support": "dedicated", "custom_features": True}
    }
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    billing_cycle VARCHAR(50) DEFAULT 'monthly',
    quota_type VARCHAR(100),
    quota_limit DECIMAL(15,2),
    features JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
"""

INSERT_SQL = (
    text("""
        INSERT INTO subscription_plans
        (name, description, price, currency, billing_cycle, quota_type, quota_limit, features, is_active)
        VALUES
        (:name, :description, :price, :currency, :billing_cycle, :quota_type, :quota_limit, :features, TRUE)
        ON CONFLICT (name) DO NOTHING
    """).bindparams(bindparam("features", type_=JSONB))
)

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            # 1. 创建表
            await session.execute(text(CREATE_TABLE_SQL))

            # 2. 检查是否已有数据
            count = (await session.execute(text("SELECT COUNT(*) FROM subscription_plans"))).scalar()
            if count and count > 0:
                logger.info(f"subscription_plans 已有 {count} 条记录，跳过插入")
                await session.commit()
                return

            # 3. 插入默认计划
            for p in PLANS:
                await session.execute(
                    INSERT_SQL,
                    {
                        "name": p["name"],
                        "description": p["description"],
                        "price": float(p["price"]),
                        "currency": p["currency"],
                        "billing_cycle": p["billing_cycle"],
                        "quota_type": p["quota_type"],
                        "quota_limit": p["quota_limit"],
                        "features": json.loads(json.dumps(p["features"], ensure_ascii=False))
                    }
                )
                logger.info(f"插入: {p['name']}")
            await session.commit()

            final = (await session.execute(text("SELECT COUNT(*) FROM subscription_plans"))).scalar()
            logger.info(f"完成，subscription_plans 共 {final} 条")

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())