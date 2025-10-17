"""简化的配额管理器 - 用于主应用集成

这是一个轻量级的配额检查和扣除模块，直接操作数据库。
"""
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from uuid import UUID

logger = logging.getLogger(__name__)


class QuotaManager:
    """配额管理器"""

    def __init__(self, db_url: str):
        """初始化配额管理器

        Args:
            db_url: 异步数据库连接URL
        """
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def check_quota(
        self,
        user_id: str,
        quota_type: str,
        amount: float = 1.0
    ) -> bool:
        """检查用户是否有足够的配额

        Args:
            user_id: 用户ID
            quota_type: 配额类型（如 'api_calls_full_process'）
            amount: 需要消耗的数量

        Returns:
            True if has enough quota, False otherwise
        """
        try:
            async with self.async_session() as session:
                # 简化查询：直接查quota_limits表
                # 在真实环境中，这里会join quota_types表
                query = f"""
                SELECT ql.limit_amount, ql.used_amount
                FROM quota_limits ql
                JOIN quota_types qt ON ql.quota_type_id = qt.id
                WHERE ql.user_id = :user_id AND qt.type_key = :quota_type
                """

                result = await session.execute(
                    query,
                    {"user_id": user_id, "quota_type": quota_type}
                )
                row = result.fetchone()

                if not row:
                    logger.warning(f"No quota limit found for user {user_id}, quota_type {quota_type}")
                    # 未找到配额记录，默认拒绝
                    return False

                limit_amount, used_amount = row
                remaining = limit_amount - used_amount

                # -1 表示无限制
                if limit_amount == -1:
                    return True

                has_quota = remaining >= amount
                logger.info(
                    f"Quota check: user={user_id}, type={quota_type}, "
                    f"limit={limit_amount}, used={used_amount}, "
                    f"remaining={remaining}, required={amount}, "
                    f"result={'OK' if has_quota else 'INSUFFICIENT'}"
                )

                return has_quota

        except Exception as e:
            logger.error(f"Error checking quota: {e}", exc_info=True)
            # 查询失败时，为了系统可用性，允许通过（可配置策略）
            return True

    async def consume_quota(
        self,
        user_id: str,
        quota_type: str,
        amount: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """消耗用户配额并记录使用日志

        Args:
            user_id: 用户ID
            quota_type: 配额类型
            amount: 消耗数量
            metadata: 元数据（如endpoint, patient_name等）

        Returns:
            True if consumed successfully, False otherwise
        """
        try:
            async with self.async_session() as session:
                async with session.begin():
                    # 1. 更新 quota_limits 表
                    update_query = """
                    UPDATE quota_limits ql
                    SET used_amount = used_amount + :amount
                    FROM quota_types qt
                    WHERE ql.quota_type_id = qt.id
                      AND ql.user_id = :user_id
                      AND qt.type_key = :quota_type
                    """

                    await session.execute(
                        update_query,
                        {"user_id": user_id, "quota_type": quota_type, "amount": amount}
                    )

                    # 2. 记录使用日志（usage_logs表）
                    log_query = """
                    INSERT INTO usage_logs (user_id, quota_type_id, amount, endpoint, metadata, created_at)
                    SELECT :user_id, qt.id, :amount, :endpoint, :metadata, NOW()
                    FROM quota_types qt
                    WHERE qt.type_key = :quota_type
                    """

                    endpoint = metadata.get("endpoint") if metadata else None
                    await session.execute(
                        log_query,
                        {
                            "user_id": user_id,
                            "quota_type": quota_type,
                            "amount": amount,
                            "endpoint": endpoint,
                            "metadata": metadata
                        }
                    )

                await session.commit()
                logger.info(f"Consumed quota: user={user_id}, type={quota_type}, amount={amount}")
                return True

        except Exception as e:
            logger.error(f"Error consuming quota: {e}", exc_info=True)
            return False

    async def get_remaining_quota(
        self,
        user_id: str,
        quota_type: str
    ) -> float:
        """获取剩余配额"""
        try:
            async with self.async_session() as session:
                query = """
                SELECT ql.limit_amount - ql.used_amount AS remaining
                FROM quota_limits ql
                JOIN quota_types qt ON ql.quota_type_id = qt.id
                WHERE ql.user_id = :user_id AND qt.type_key = :quota_type
                """

                result = await session.execute(
                    query,
                    {"user_id": user_id, "quota_type": quota_type}
                )
                row = result.fetchone()

                if not row:
                    return 0.0

                remaining = row[0]
                # -1 表示无限制
                if remaining < 0:
                    return float('inf')

                return float(remaining)

        except Exception as e:
            logger.error(f"Error getting remaining quota: {e}", exc_info=True)
            return 0.0

    async def get_all_quotas(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """获取用户所有配额信息"""
        try:
            async with self.async_session() as session:
                query = """
                SELECT
                    qt.type_key,
                    qt.name,
                    qt.unit,
                    ql.limit_amount,
                    ql.used_amount,
                    (ql.limit_amount - ql.used_amount) AS remaining
                FROM quota_limits ql
                JOIN quota_types qt ON ql.quota_type_id = qt.id
                WHERE ql.user_id = :user_id
                ORDER BY qt.type_key
                """

                result = await session.execute(query, {"user_id": user_id})
                rows = result.fetchall()

                quotas = {}
                for row in rows:
                    type_key, name, unit, limit, used, remaining = row
                    quotas[type_key] = {
                        "name": name,
                        "unit": unit,
                        "limit": float(limit) if limit != -1 else "unlimited",
                        "used": float(used),
                        "remaining": float(remaining) if limit != -1 else "unlimited"
                    }

                return quotas

        except Exception as e:
            logger.error(f"Error getting all quotas: {e}", exc_info=True)
            return {}
