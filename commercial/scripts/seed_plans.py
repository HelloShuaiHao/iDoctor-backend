"""初始化订阅计划"""
import asyncio
import sys
import os
import logging
from decimal import Decimal

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 导入不要用 commercial.shared.database
try:
    from shared.config import settings
except ImportError:
    try:
        from commercial.shared.config import settings
    except ImportError:
        raise ImportError("无法导入 settings，请检查路径配置")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_plans():
    """创建默认订阅计划"""
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
            # 创建 plans 表
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
            
            # 检查是否已存在计划
            result = await session.execute(text("SELECT COUNT(*) FROM plans"))
            count = result.scalar()
            
            if count > 0:
                logger.info(f"⚠️  已存在 {count} 个订阅计划，跳过初始化")
                await session.commit()
                return
            
            # 创建计划
            for plan_data in plans:
                await session.execute(
                    text("""
                        INSERT INTO plans 
                        (name, description, price, currency, billing_cycle, quota_type, quota_limit, features)
                        VALUES 
                        (:name, :description, :price, :currency, :billing_cycle, :quota_type, :quota_limit, :features::jsonb)
                    """),
                    {
                        "name": plan_data["name"],
                        "description": plan_data["description"],
                        "price": plan_data["price"],
                        "currency": plan_data["currency"],
                        "billing_cycle": plan_data["billing_cycle"],
                        "quota_type": plan_data["quota_type"],
                        "quota_limit": plan_data["quota_limit"],
                        "features": str(plan_data["features"]).replace("'", '"')  # JSON 格式
                    }
                )
            
            await session.commit()
            logger.info(f"✅ 成功创建 {len(plans)} 个订阅计划")
            for plan_data in plans:
                logger.info(f"   - {plan_data['name']}: ¥{plan_data['price']}/月, {plan_data['quota_limit']}次")
                
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


async def main():
    logger.info("🚀 开始初始化订阅计划...")
    try:
        await seed_plans()
        logger.info("✨ 完成！")
    except Exception as e:
        logger.error(f"❌ 失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())