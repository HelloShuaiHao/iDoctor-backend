"""Alembic环境配置"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from commercial.shared.config import settings
from commercial.shared.database import Base

# 导入所有模型（必须导入才能生成迁移）
from commercial.auth_service.models.user import User
from commercial.auth_service.models.api_key import APIKey
from commercial.payment_service.models.plan import SubscriptionPlan
from commercial.payment_service.models.subscription import UserSubscription
from commercial.payment_service.models.transaction import PaymentTransaction
from commercial.payment_service.models.usage_log import UsageLog

# Alembic配置对象
config = context.config

# 设置数据库URL（从环境变量读取，移除asyncpg使用psycopg2）
database_url = settings.DATABASE_URL.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", database_url)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 元数据
target_metadata = Base.metadata


def run_migrations_offline():
    """离线模式迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """在线模式迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
