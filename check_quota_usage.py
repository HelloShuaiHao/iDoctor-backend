#!/usr/bin/env python3
"""检查配额使用情况"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check_quotas():
    """检查数据库中的配额使用情况"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL 未配置")
        return

    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # 查询所有用户的配额
            query = text("""
            SELECT
                u.username,
                qt.type_key,
                qt.name,
                qt.unit,
                ql.limit_amount,
                ql.used_amount,
                (ql.limit_amount - ql.used_amount) AS remaining
            FROM quota_limits ql
            JOIN users u ON ql.user_id = u.id
            JOIN quota_types qt ON ql.quota_type_id = qt.id
            ORDER BY u.username, qt.type_key
            """)

            result = await conn.execute(query)
            rows = result.fetchall()

            if not rows:
                print("❌ 没有找到配额记录")
                return

            print("=" * 100)
            print(f"{'用户名':<15} {'配额类型':<30} {'配额名':<20} {'单位':<8} {'限制':<10} {'已用':<10} {'剩余':<10}")
            print("=" * 100)

            current_user = None
            for row in rows:
                username, type_key, name, unit, limit, used, remaining = row

                if username != current_user:
                    if current_user is not None:
                        print("-" * 100)
                    current_user = username

                print(f"{username:<15} {type_key:<30} {name:<20} {unit:<8} {limit:<10.2f} {used:<10.2f} {remaining:<10.2f}")

            print("=" * 100)

            # 检查 usage_logs
            print("\n查询最近的配额使用日志:")
            log_query = text("""
            SELECT
                u.username,
                qt.type_key,
                ul.amount,
                ul.endpoint,
                ul.created_at
            FROM usage_logs ul
            JOIN users u ON ul.user_id = u.id
            JOIN quota_types qt ON ul.quota_type_id = qt.id
            ORDER BY ul.created_at DESC
            LIMIT 10
            """)

            result = await conn.execute(log_query)
            log_rows = result.fetchall()

            if log_rows:
                print(f"\n{'用户名':<15} {'配额类型':<30} {'数量':<10} {'端点':<40} {'时间'}")
                print("-" * 120)
                for row in log_rows:
                    username, type_key, amount, endpoint, created_at = row
                    print(f"{username:<15} {type_key:<30} {amount:<10.2f} {endpoint:<40} {created_at}")
            else:
                print("⚠️  没有找到使用日志")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_quotas())
