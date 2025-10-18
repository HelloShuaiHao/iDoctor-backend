#!/usr/bin/env python3
"""
数据库初始化脚本

创建配额系统所需的表结构和默认数据
"""
import asyncio
import sys
import os
import logging
from decimal import Decimal
from datetime import datetime, timezone

# 添加商业化系统到路径
commercial_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, commercial_path)
print(f"DEBUG: Added {commercial_path} to sys.path")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 直接导入配置
try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """创建数据库表"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    try:
        async with engine.begin() as conn:
            # 创建扩展
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            
            # 创建配额类型表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS quota_types (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    type_key VARCHAR(100) UNIQUE NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    unit VARCHAR(50) DEFAULT 'times',
                    default_limit DECIMAL(15,2) DEFAULT 0,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # 创建用户表（如果不存在） - 注意：字段名可能是hashed_password
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    username VARCHAR(50) UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    hashed_password VARCHAR(255),
                    is_active BOOLEAN DEFAULT true,
                    is_superuser BOOLEAN DEFAULT false,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # 创建配额限制表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS quota_limits (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    quota_type_id UUID NOT NULL REFERENCES quota_types(id) ON DELETE CASCADE,
                    limit_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                    used_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                    reset_date TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, quota_type_id)
                )
            """))
            
            # 创建使用日志表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    quota_type_id UUID NOT NULL REFERENCES quota_types(id) ON DELETE CASCADE,
                    amount DECIMAL(15,2) NOT NULL,
                    endpoint VARCHAR(200),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # 创建索引
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_quota_limits_user_id ON quota_limits(user_id)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at)
            """))
            
        logger.info("✅ 数据库表创建完成")
        
    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        raise
    finally:
        await engine.dispose()


async def insert_default_quota_types():
    """插入默认配额类型"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    default_quota_types = [
        {
            "type_key": "api_calls_full_process",
            "name": "完整处理流程",
            "description": "执行完整的医学影像处理流程",
            "unit": "次",
            "default_limit": 100
        },
        {
            "type_key": "api_calls_l3_detect",
            "name": "L3椎骨检测",
            "description": "检测L3椎骨位置",
            "unit": "次",
            "default_limit": 200
        },
        {
            "type_key": "api_calls_continue",
            "name": "L3后续处理",
            "description": "L3检测后的继续处理",
            "unit": "次",
            "default_limit": 200
        },
        {
            "type_key": "api_calls_preview",
            "name": "预览生成",
            "description": "生成医学影像预览",
            "unit": "次", 
            "default_limit": 1000
        },
        {
            "type_key": "api_calls_download",
            "name": "文件下载",
            "description": "下载处理结果文件",
            "unit": "次",
            "default_limit": 500
        },
        {
            "type_key": "storage_dicom",
            "name": "DICOM存储",
            "description": "DICOM文件存储空间",
            "unit": "MB",
            "default_limit": 100
        },
        {
            "type_key": "storage_results",
            "name": "结果存储",
            "description": "处理结果存储空间",
            "unit": "MB",
            "default_limit": 50
        },
        {
            "type_key": "storage_usage",
            "name": "存储使用量",
            "description": "用户数据存储空间",
            "unit": "MB",
            "default_limit": 100
        },
        {
            "type_key": "api_calls_image_analysis",
            "name": "图像分析",
            "description": "AI图像分析服务",
            "unit": "次",
            "default_limit": 50
        }
    ]
    
    try:
        async with async_session() as session:
            for quota_type in default_quota_types:
                # 检查是否已存在
                result = await session.execute(
                    text("SELECT id FROM quota_types WHERE type_key = :type_key"),
                    {"type_key": quota_type["type_key"]}
                )
                
                if result.fetchone() is None:
                    insert_stmt = text("""
                        INSERT INTO quota_types (type_key, name, description, unit, default_limit)
                        VALUES (:type_key, :name, :description, :unit, :default_limit)
                    """)
                    await session.execute(insert_stmt, quota_type)
                    logger.info(f"✅ 创建配额类型: {quota_type['name']}")
                else:
                    logger.info(f"⏯️  配额类型已存在: {quota_type['name']}")
            
            await session.commit()
            
        logger.info("✅ 默认配额类型设置完成")
        
    except Exception as e:
        logger.error(f"❌ 设置配额类型失败: {e}")
        raise
    finally:
        await engine.dispose()


async def create_test_user_with_quota():
    """创建测试用户并分配配额"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # •  test@example.com / password123
    # •  demo@example.com / password123
    test_users = [
        {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LnYbyEjt.W6qvh5YS"  # password123
        },
        {
            "username": "demo",
            "email": "demo@example.com", 
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LnYbyEjt.W6qvh5YS"  # password123
        }
    ]
    
    try:
        async with async_session() as session:
            for user_data in test_users:
                # 检查用户是否已存在
                result = await session.execute(
                    text("SELECT id FROM users WHERE email = :email"),
                    {"email": user_data["email"]}
                )
                user_row = result.fetchone()
                
                if user_row is None:
                    # 创建用户
                    insert_user = text("""
                        INSERT INTO users (username, email, hashed_password)
                        VALUES (:username, :email, :hashed_password)
                        RETURNING id
                    """)
                    result = await session.execute(insert_user, user_data)
                    user_id = result.fetchone()[0]
                    logger.info(f"✅ 创建测试用户: {user_data['email']}")
                else:
                    user_id = user_row[0]
                    logger.info(f"⏭️  测试用户已存在: {user_data['email']}")
                
                # 为用户分配默认配额
                await assign_default_quota_to_user(session, user_id)
            
            await session.commit()
            
        logger.info("✅ 测试用户和配额设置完成")
        
    except Exception as e:
        logger.error(f"❌ 创建测试用户失败: {e}")
        raise
    finally:
        await engine.dispose()


async def assign_default_quota_to_user(session: AsyncSession, user_id: str):
    """为用户分配默认配额"""
    # 获取所有配额类型
    result = await session.execute(
        text("SELECT id, type_key, default_limit FROM quota_types WHERE is_active = true")
    )
    quota_types = result.fetchall()
    
    for quota_type_id, type_key, default_limit in quota_types:
        # 检查用户是否已有此配额
        result = await session.execute(
            text("""
                SELECT id FROM quota_limits 
                WHERE user_id = :user_id AND quota_type_id = :quota_type_id
            """),
            {"user_id": user_id, "quota_type_id": quota_type_id}
        )
        
        if result.fetchone() is None:
            # 创建配额限制
            await session.execute(
                text("""
                    INSERT INTO quota_limits (user_id, quota_type_id, limit_amount, used_amount)
                    VALUES (:user_id, :quota_type_id, :limit_amount, 0)
                """),
                {
                    "user_id": user_id,
                    "quota_type_id": quota_type_id, 
                    "limit_amount": default_limit
                }
            )
            logger.info(f"  ✅ 分配配额: {type_key} = {default_limit}")
        else:
            logger.info(f"  ⏭️  配额已存在: {type_key}")


async def main():
    """主函数"""
    logger.info("🚀 开始初始化数据库...")
    
    try:
        # 1. 创建表结构
        await create_tables()
        
        # 2. 插入默认配额类型
        await insert_default_quota_types()
        
        # 3. 创建测试用户并分配配额（可选）
        try:
            await create_test_user_with_quota()
        except Exception as e:
            logger.warning(f"⚠️  跳过测试用户创建: {e}")
            logger.info("💡 请使用认证服务注册用户，然后会自动分配配额")
        
        logger.info("🎉 数据库初始化完成！")
        
        print("\n" + "="*50)
        print("📋 测试用户信息:")
        print("用户名: testuser, 邮箱: test@example.com, 密码: password123")
        print("用户名: demo, 邮箱: demo@example.com, 密码: password123")
        print("="*50)
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())