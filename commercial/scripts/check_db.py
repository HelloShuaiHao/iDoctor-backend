"""检查数据库状态"""
import asyncio
import sys
import os

# /app/scripts/check_db.py -> /app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from commercial.shared.database import AsyncSessionLocal
from commercial.payment_service.models.plan import SubscriptionPlan


async def check_db():
    """检查数据库表和数据"""
    async with AsyncSessionLocal() as db:
        # 检查表是否存在
        result = await db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        print("\n📋 数据库表列表:")
        for table in tables:
            print(f"   - {table[0]}")

        # 检查订阅计划
        stmt = select(SubscriptionPlan)
        result = await db.execute(stmt)
        plans = result.scalars().all()

        print(f"\n💳 订阅计划数量: {len(plans)}")
        if plans:
            print("   计划列表:")
            for plan in plans:
                print(f"   - {plan.name}: ¥{plan.price}, 激活: {plan.is_active}")
        else:
            print("   ⚠️  没有找到任何订阅计划！")


if __name__ == "__main__":
    print("🔍 检查数据库状态...")
    asyncio.run(check_db())
    print("\n✅ 检查完成！")
