"""初始化订阅计划"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from decimal import Decimal
from commercial.shared.database import AsyncSessionLocal
from commercial.payment_service.models.plan import SubscriptionPlan


async def seed_plans():
    """创建默认订阅计划"""
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

    async with AsyncSessionLocal() as db:
        # 检查是否已存在计划
        from sqlalchemy import select
        stmt = select(SubscriptionPlan)
        result = await db.execute(stmt)
        existing_plans = result.scalars().all()

        if existing_plans:
            print(f"⚠️  已存在 {len(existing_plans)} 个订阅计划，跳过初始化")
            return

        # 创建计划
        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)

        await db.commit()
        print(f"✅ 成功创建 {len(plans)} 个订阅计划：")
        for plan_data in plans:
            print(f"   - {plan_data['name']}: ¥{plan_data['price']}/月, {plan_data['quota_limit']}次")


if __name__ == "__main__":
    print("🚀 开始初始化订阅计划...")
    asyncio.run(seed_plans())
    print("✨ 完成！")
