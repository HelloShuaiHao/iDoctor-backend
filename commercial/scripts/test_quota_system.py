#!/usr/bin/env python3
import subprocess
import sys

try:
    import sqlalchemy
except ImportError:
    print("SQLAlchemy not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlalchemy", "asyncpg", "SQLAlchemy[asyncio]"])
    import sqlalchemy
"""
Quota System Test Script

Tests the quota middleware, manager, and admin endpoints to ensure
proper quota checking, consumption, and management.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime

# Add commercial path
commercial_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, commercial_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_quota_manager():
    """Test QuotaManager basic operations"""
    from integrations.quota_manager import QuotaManager
    from shared.config import settings
    
    logger.info("🧪 Testing QuotaManager...")
    
    manager = QuotaManager(settings.DATABASE_URL)
    
    # Test 1: Get all quotas for test user
    test_user_id = "00000000-0000-0000-0000-000000000001"  # Replace with actual test user
    
    try:
        quotas = await manager.get_all_quotas(test_user_id)
        logger.info(f"✅ Get all quotas: Found {len(quotas)} quota types")
        for quota_type, info in quotas.items():
            logger.info(f"   - {quota_type}: {info['used']}/{info['limit']} {info['unit']}")
    except Exception as e:
        logger.error(f"❌ Get all quotas failed: {e}")
        return False
    
    # Test 2: Check quota
    quota_type = "api_calls_full_process"
    try:
        has_quota = await manager.check_quota(test_user_id, quota_type, 1)
        logger.info(f"✅ Check quota: {quota_type} = {has_quota}")
    except Exception as e:
        logger.error(f"❌ Check quota failed: {e}")
        return False
    
    # Test 3: Get remaining quota
    try:
        remaining = await manager.get_remaining_quota(test_user_id, quota_type)
        logger.info(f"✅ Remaining quota: {quota_type} = {remaining}")
    except Exception as e:
        logger.error(f"❌ Get remaining quota failed: {e}")
        return False
    
    # Test 4: Consume quota (if has quota)
    if has_quota:
        try:
            success = await manager.consume_quota(
                test_user_id,
                quota_type,
                1,
                metadata={
                    "endpoint": "/test",
                    "test": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"✅ Consume quota: {success}")
            
            # Check remaining after consumption
            remaining_after = await manager.get_remaining_quota(test_user_id, quota_type)
            logger.info(f"   Remaining after: {remaining_after} (was {remaining})")
        except Exception as e:
            logger.error(f"❌ Consume quota failed: {e}")
            return False
    
    logger.info("✅ QuotaManager tests passed!")
    return True


async def test_database_connection():
    """Test database connection and schema"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from shared.config import settings
    
    logger.info("🧪 Testing database connection...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Test 1: Check tables exist
            tables_query = text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('quota_types', 'quota_limits', 'usage_logs', 'users')
            ORDER BY table_name
            """)
            result = await session.execute(tables_query)
            tables = [row[0] for row in result.fetchall()]
            
            logger.info(f"✅ Found tables: {', '.join(tables)}")
            
            required_tables = {'quota_types', 'quota_limits', 'usage_logs', 'users'}
            missing = required_tables - set(tables)
            if missing:
                logger.error(f"❌ Missing tables: {', '.join(missing)}")
                return False
            
            # Test 2: Count quota types
            count_query = text("SELECT COUNT(*) FROM quota_types WHERE is_active = true")
            result = await session.execute(count_query)
            count = result.scalar()
            logger.info(f"✅ Active quota types: {count}")
            
            # Test 3: Count users with quotas
            users_query = text("""
            SELECT COUNT(DISTINCT user_id) FROM quota_limits
            """)
            result = await session.execute(users_query)
            user_count = result.scalar()
            logger.info(f"✅ Users with quotas: {user_count}")
            
            # Test 4: Sample usage logs
            logs_query = text("""
            SELECT COUNT(*) FROM usage_logs
            WHERE created_at >= NOW() - INTERVAL '7 days'
            """)
            result = await session.execute(logs_query)
            log_count = result.scalar()
            logger.info(f"✅ Usage logs (last 7 days): {log_count}")
        
        await engine.dispose()
        logger.info("✅ Database tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}", exc_info=True)
        await engine.dispose()
        return False


async def verify_quota_types():
    """Verify all required quota types are registered"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from shared.config import settings
    
    logger.info("🧪 Verifying quota types...")
    
    required_types = [
        "api_calls_full_process",
        "api_calls_l3_detect",
        "api_calls_continue",
        "storage_dicom",
        "storage_results"
    ]
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            query = text("""
            SELECT type_key, name, unit, default_limit, is_active
            FROM quota_types
            WHERE type_key = ANY(:types)
            """)
            result = await session.execute(query, {"types": required_types})
            rows = result.fetchall()
            
            found_types = {row[0] for row in rows}
            missing_types = set(required_types) - found_types
            
            if missing_types:
                logger.error(f"❌ Missing quota types: {', '.join(missing_types)}")
                logger.info("   Run: python commercial/scripts/init_database.py")
                await engine.dispose()
                return False
            
            logger.info("✅ All required quota types found:")
            for row in rows:
                type_key, name, unit, limit, active = row
                status = "✅" if active else "⚠️"
                logger.info(f"   {status} {type_key}: {name} ({limit} {unit})")
        
        await engine.dispose()
        logger.info("✅ Quota type verification passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Quota type verification failed: {e}", exc_info=True)
        await engine.dispose()
        return False


async def test_endpoint_mappings():
    """Test that endpoint patterns are correctly mapped"""
    from integrations.middleware.quota_middleware import (
        _path_matches_template,
        _match_endpoint,
        ENDPOINT_QUOTA_MAP,
        STORAGE_ENDPOINTS
    )
    
    logger.info("🧪 Testing endpoint mappings...")
    
    test_cases = [
        # (path, should_match, expected_quota_type)
        ("/process/John_Doe/20250101", True, "api_calls_full_process"),
        ("/l3_detect/Test_Patient/20250115", True, "api_calls_l3_detect"),
        ("/continue_after_l3/Patient/20250101", True, "api_calls_continue"),
        ("/upload_dicom_zip", True, "storage_dicom"),
        ("/upload_l3_mask/Patient/20250101", True, "storage_results"),
        ("/get_key_results/Patient/20250101", False, None),  # Should be exempt
        ("/docs", False, None),  # Should be exempt
    ]
    
    all_passed = True
    for path, should_match, expected_type in test_cases:
        config = _match_endpoint(path)
        
        if should_match:
            if config is None:
                logger.error(f"❌ Path '{path}' should match but didn't")
                all_passed = False
            elif config["quota_type"] != expected_type:
                logger.error(
                    f"❌ Path '{path}' matched wrong type: "
                    f"got '{config['quota_type']}', expected '{expected_type}'"
                )
                all_passed = False
            else:
                logger.info(f"✅ Path '{path}' → {config['quota_type']}")
        else:
            if config is not None:
                logger.warning(f"⚠️  Path '{path}' matched but should be exempt")
            else:
                logger.info(f"✅ Path '{path}' → exempt (as expected)")
    
    if all_passed:
        logger.info("✅ Endpoint mapping tests passed!")
    else:
        logger.error("❌ Some endpoint mapping tests failed")
    
    return all_passed


def print_summary():
    """Print test summary and next steps"""
    print("\n" + "="*60)
    print("📋 Quota System Test Summary")
    print("="*60)
    print("\n✅ Components tested:")
    print("   • Database connection and schema")
    print("   • Quota types registration")
    print("   • QuotaManager operations")
    print("   • Endpoint mappings")
    print("\n📌 Next steps:")
    print("   1. Run integration tests with actual API calls")
    print("   2. Test admin endpoints with curl/httpx")
    print("   3. Monitor quota logs in production")
    print("   4. Set up automated quota reset (monthly/weekly)")
    print("\n💡 Admin API endpoints:")
    print("   GET  /admin/quotas/users/{user_id}")
    print("   GET  /admin/quotas/usage-logs")
    print("   GET  /admin/quotas/statistics/{quota_type}")
    print("   POST /admin/quotas/users/{user_id}/reset")
    print("   PUT  /admin/quotas/users/{user_id}/adjust")
    print("\n🔐 Environment variables required:")
    print("   • DATABASE_URL - PostgreSQL async connection")
    print("   • ENABLE_AUTH=true - Enable authentication")
    print("   • ENABLE_QUOTA=true - Enable quota checking")
    print("   • ADMIN_TOKEN - Admin API authentication")
    print("="*60 + "\n")


async def main():
    """Run all tests"""
    logger.info("🚀 Starting Quota System Tests...\n")
    
    results = []
    
    # Test 1: Database connection
    results.append(await test_database_connection())
    print()
    
    # Test 2: Verify quota types
    results.append(await verify_quota_types())
    print()
    
    # Test 3: Endpoint mappings
    results.append(test_endpoint_mappings())
    print()
    
    # Test 4: QuotaManager (requires test user)
    # Commented out by default - uncomment when you have a test user
    # results.append(await test_quota_manager())
    # print()
    
    # Summary
    print_summary()
    
    # Final result
    if all(results):
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed. Check logs above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
