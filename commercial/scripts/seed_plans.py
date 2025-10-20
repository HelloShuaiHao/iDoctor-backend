"""初始化订阅计划（直接写入 subscription_plans）"""
import asyncio, sys, os, logging, json, uuid
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PLANS = [
    {"name": "免费版", "description": "适合个人试用，每月限量", "price": Decimal("0.00"), "currency": "CNY",
     "billing_cycle": "monthly", "quota_type": "processing_count", "quota_limit": 10,
     "features": {"max_concurrent": 1, "priority": "low", "support": "community"}},
    {"name": "专业版", "description": "团队使用，中等配额", "price": Decimal("99.00"), "currency": "CNY",
     "billing_cycle": "monthly", "quota_type": "processing_count", "quota_limit": 100,
     "features": {"max_concurrent": 3, "priority": "medium", "support": "email"}},
    {"name": "企业版", "description": "高并发与高级支持", "price": Decimal("999.00"), "currency": "CNY",
     "billing_cycle": "monthly", "quota_type": "processing_count", "quota_limit": 999999,
     "features": {"max_concurrent": 10, "priority": "high", "support": "dedicated", "custom_features": True}}
]

CREATE_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
"""

ENSURE_TABLE = """
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY,
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
);
"""

# 若已有表但无默认，为安全显式设置 (若列已存在且无默认不会报错)
ALTER_ID_DEFAULT = """
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='subscription_plans' AND column_name='id' AND column_default IS NULL
  ) THEN
    -- 使用 gen_random_uuid 避免 uuid-ossp 依赖
    ALTER TABLE subscription_plans ALTER COLUMN id SET DEFAULT gen_random_uuid();
  END IF;
END$$;
"""

INSERT_SQL = text("""
INSERT INTO subscription_plans
(id, name, description, price, currency, billing_cycle, quota_type, quota_limit, features, is_active)
VALUES
(:id, :name, :description, :price, :currency, :billing_cycle, :quota_type, :quota_limit, :features::jsonb, TRUE)
ON CONFLICT (name) DO NOTHING
""")

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            await session.execute(text(CREATE_EXTENSIONS))
            await session.execute(text(ENSURE_TABLE))
            await session.execute(text(ALTER_ID_DEFAULT))

            count = (await session.execute(text("SELECT COUNT(*) FROM subscription_plans"))).scalar()
            if count and count > 0:
                logger.info(f"已存在 {count} 条订阅计划，跳过")
                await session.commit()
                return

            for p in PLANS:
                await session.execute(
                    INSERT_SQL,
                    {
                        "id": str(uuid.uuid4()),
                        "name": p["name"],
                        "description": p["description"],
                        "price": float(p["price"]),
                        "currency": p["currency"],
                        "billing_cycle": p["billing_cycle"],
                        "quota_type": p["quota_type"],
                        "quota_limit": p["quota_limit"],
                        "features": json.dumps(p["features"], ensure_ascii=False)
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