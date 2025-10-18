#!/usr/bin/env python3
"""
初始化 iDoctor 应用的配额类型

为 iDoctor 医学影像处理应用定义专门的配额类型，包括：
- API 调用配额（L3检测、完整处理、续传处理等）
- 存储空间配额（DICOM文件、处理结果）
- AI 分析配额
"""
import asyncio
import sys
import os
import logging

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)
commercial_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, commercial_path)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 导入配置（兼容 Docker 和本地环境）
try:
    from shared.config import settings
except ImportError:
    from commercial.shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# iDoctor 应用的配额类型定义
IDOCTOR_QUOTA_TYPES = [
    {
        "type_key": "api_calls_l3_detect",
        "name": "L3椎骨检测次数",
        "description": "每月可调用 /l3_detect 端点的次数",
        "unit": "次",
        "default_limit": 10  # 免费版默认
    },
    {
        "type_key": "api_calls_full_process",
        "name": "完整处理次数",
        "description": "每月可调用 /process 端点的完整处理流程次数",
        "unit": "次",
        "default_limit": 5  # 免费版默认
    },
    {
        "type_key": "api_calls_continue",
        "name": "续传处理次数",
        "description": "每月可调用 /continue_after_l3 端点的次数",
        "unit": "次",
        "default_limit": 10
    },
    {
        "type_key": "storage_dicom",
        "name": "DICOM存储空间",
        "description": "可存储的DICOM文件总大小（不单独限制）",
        "unit": "MB",
        "default_limit": 99999  # 不单独限制，仅用于统计
    },
    {
        "type_key": "storage_results",
        "name": "结果存储空间",
        "description": "处理结果（图片+CSV）的存储空间（不单独限制）",
        "unit": "MB",
        "default_limit": 99999  # 不单独限制，仅用于统计
    },
    {
        "type_key": "storage_usage",
        "name": "存储使用量",
        "description": "DICOM文件和处理结果的总存储空间（免费版限制）",
        "unit": "MB",
        "default_limit": 80  # 免费版总存储限制 80MB
    },
    {
        "type_key": "patient_cases",
        "name": "患者案例数量",
        "description": "可处理的不同患者案例数量",
        "unit": "个",
        "default_limit": 10
    }
]


async def init_idoctor_quotas():
    """初始化 iDoctor 配额类型"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    logger.info("🚀 开始初始化 iDoctor 配额类型...")
    
    try:
        async with async_session() as session:
            for quota_type in IDOCTOR_QUOTA_TYPES:
                # 检查配额类型是否已存在
                result = await session.execute(
                    text("SELECT id FROM quota_types WHERE type_key = :type_key"),
                    {"type_key": quota_type["type_key"]}
                )
                
                existing = result.fetchone()
                
                if existing is None:
                    # 创建新的配额类型
                    insert_stmt = text("""
                        INSERT INTO quota_types (type_key, name, description, unit, default_limit)
                        VALUES (:type_key, :name, :description, :unit, :default_limit)
                    """)
                    await session.execute(insert_stmt, quota_type)
                    logger.info(f"✅ 创建配额类型: {quota_type['name']} ({quota_type['type_key']})")
                else:
                    # 更新现有配额类型
                    update_stmt = text("""
                        UPDATE quota_types 
                        SET name = :name,
                            description = :description,
                            unit = :unit,
                            default_limit = :default_limit,
                            updated_at = NOW()
                        WHERE type_key = :type_key
                    """)
                    await session.execute(update_stmt, quota_type)
                    logger.info(f"🔄 更新配额类型: {quota_type['name']} ({quota_type['type_key']})")
            
            await session.commit()
            logger.info("✅ iDoctor 配额类型初始化完成")
            
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        raise
    finally:
        await engine.dispose()


async def list_quota_types():
    """列出所有配额类型"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            result = await session.execute(
                text("""
                    SELECT type_key, name, unit, default_limit 
                    FROM quota_types 
                    WHERE is_active = true
                    ORDER BY type_key
                """)
            )
            
            quota_types = result.fetchall()
            
            if quota_types:
                print("\n" + "="*70)
                print("📋 当前配额类型列表:")
                print("="*70)
                for type_key, name, unit, default_limit in quota_types:
                    print(f"  • {name:30s} [{type_key}]")
                    print(f"    默认限额: {default_limit} {unit}")
                print("="*70)
            else:
                print("\n⚠️  未找到任何配额类型")
            
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
    finally:
        await engine.dispose()


async def main():
    """主函数"""
    logger.info("🏥 iDoctor 配额系统初始化工具")
    logger.info("="*70)
    
    try:
        # 1. 初始化配额类型
        await init_idoctor_quotas()
        
        # 2. 列出所有配额类型
        await list_quota_types()
        
        print("\n🎉 初始化完成！")
        print("\n💡 提示:")
        print("  • 新用户注册时会自动分配默认配额")
        print("  • 运行 'python commercial/scripts/init_database.py' 可创建测试用户")
        print("  • 测试用户: test@example.com / password123")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
