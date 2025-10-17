"""Admin API routes for quota monitoring and management

These endpoints provide quota statistics, usage logs, and administrative
controls for the quota system.
"""
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/quotas", tags=["admin-quotas"])


# ==================== Response Models ====================
class QuotaInfo(BaseModel):
    """Quota information for a user"""
    type_key: str
    name: str
    unit: str
    limit: float
    used: float
    remaining: float
    usage_percent: float


class UserQuotaSummary(BaseModel):
    """Summary of all quotas for a user"""
    user_id: str
    total_quotas: int
    quotas: List[QuotaInfo]


class UsageLogEntry(BaseModel):
    """Single usage log entry"""
    id: str
    user_id: str
    quota_type: str
    amount: float
    endpoint: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime


class UsageStatistics(BaseModel):
    """Usage statistics for a quota type"""
    quota_type: str
    total_usage: float
    total_calls: int
    unique_users: int
    avg_usage_per_call: float
    peak_usage_date: Optional[str]


# ==================== Dependency: Get DB Session ====================
async def get_db_session():
    """Get database session for admin operations
    
    Note: In production, this should be properly injected from the app
    """
    # This will be injected by the main application
    # For now, we'll rely on the quota_manager's engine
    from commercial.integrations.quota_manager import QuotaManager
    import os
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not configured"
        )
    
    manager = QuotaManager(db_url)
    async with manager.async_session() as session:
        yield session


# ==================== Admin Auth Dependency ====================
async def verify_admin(request) -> str:
    """Verify admin privileges
    
    In production, this should check JWT token for admin role
    For now, we'll use a simple header check
    """
    # TODO: Implement proper admin authentication
    # For now, check for X-Admin-Token header
    admin_token = request.headers.get("X-Admin-Token")
    if not admin_token or admin_token != os.getenv("ADMIN_TOKEN", "admin-secret"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return "admin"


# ==================== Endpoints ====================

@router.get("/users/{user_id}", response_model=UserQuotaSummary)
async def get_user_quotas(
    user_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get all quota information for a specific user
    
    Returns current quota limits, usage, and remaining amounts for all quota types.
    """
    try:
        query = text("""
        SELECT
            qt.type_key,
            qt.name,
            qt.unit,
            ql.limit_amount,
            ql.used_amount,
            CASE 
                WHEN ql.limit_amount = -1 THEN -1
                ELSE ql.limit_amount - ql.used_amount
            END AS remaining,
            CASE
                WHEN ql.limit_amount = -1 THEN 0
                WHEN ql.limit_amount = 0 THEN 0
                ELSE (ql.used_amount / ql.limit_amount * 100)
            END AS usage_percent
        FROM quota_limits ql
        JOIN quota_types qt ON ql.quota_type_id = qt.id
        WHERE ql.user_id = :user_id
        ORDER BY qt.type_key
        """)
        
        result = await session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No quotas found for user {user_id}"
            )
        
        quotas = []
        for row in rows:
            type_key, name, unit, limit, used, remaining, usage_percent = row
            quotas.append(QuotaInfo(
                type_key=type_key,
                name=name,
                unit=unit,
                limit=float(limit) if limit != -1 else -1,
                used=float(used),
                remaining=float(remaining) if remaining != -1 else -1,
                usage_percent=float(usage_percent)
            ))
        
        return UserQuotaSummary(
            user_id=user_id,
            total_quotas=len(quotas),
            quotas=quotas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user quotas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user quotas"
        )


@router.get("/usage-logs", response_model=List[UsageLogEntry])
async def get_usage_logs(
    user_id: Optional[str] = None,
    quota_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
):
    """Get usage logs with optional filters
    
    Supports filtering by user_id, quota_type, and date range.
    Results are paginated.
    """
    try:
        # Build dynamic query based on filters
        where_clauses = []
        params = {"limit": limit, "offset": offset}
        
        if user_id:
            where_clauses.append("ul.user_id = :user_id")
            params["user_id"] = user_id
        
        if quota_type:
            where_clauses.append("qt.type_key = :quota_type")
            params["quota_type"] = quota_type
        
        if start_date:
            where_clauses.append("ul.created_at >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            where_clauses.append("ul.created_at <= :end_date")
            params["end_date"] = end_date
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = text(f"""
        SELECT
            ul.id,
            ul.user_id,
            qt.type_key,
            ul.amount,
            ul.endpoint,
            ul.metadata,
            ul.created_at
        FROM usage_logs ul
        JOIN quota_types qt ON ul.quota_type_id = qt.id
        WHERE {where_sql}
        ORDER BY ul.created_at DESC
        LIMIT :limit OFFSET :offset
        """)
        
        result = await session.execute(query, params)
        rows = result.fetchall()
        
        logs = []
        for row in rows:
            log_id, user_id, type_key, amount, endpoint, metadata, created_at = row
            logs.append(UsageLogEntry(
                id=str(log_id),
                user_id=str(user_id),
                quota_type=type_key,
                amount=float(amount),
                endpoint=endpoint,
                metadata=metadata,
                created_at=created_at
            ))
        
        return logs
        
    except Exception as e:
        logger.error(f"Error fetching usage logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch usage logs"
        )


@router.get("/statistics/{quota_type}", response_model=UsageStatistics)
async def get_quota_statistics(
    quota_type: str,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session)
):
    """Get aggregated statistics for a quota type
    
    Provides insights like total usage, number of calls, unique users, etc.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = text("""
        SELECT
            qt.type_key,
            COALESCE(SUM(ul.amount), 0) AS total_usage,
            COUNT(ul.id) AS total_calls,
            COUNT(DISTINCT ul.user_id) AS unique_users,
            CASE 
                WHEN COUNT(ul.id) > 0 THEN SUM(ul.amount) / COUNT(ul.id)
                ELSE 0
            END AS avg_usage_per_call,
            (
                SELECT DATE(ul2.created_at)
                FROM usage_logs ul2
                WHERE ul2.quota_type_id = qt.id
                  AND ul2.created_at >= :cutoff_date
                GROUP BY DATE(ul2.created_at)
                ORDER BY SUM(ul2.amount) DESC
                LIMIT 1
            ) AS peak_usage_date
        FROM quota_types qt
        LEFT JOIN usage_logs ul ON qt.id = ul.quota_type_id
          AND ul.created_at >= :cutoff_date
        WHERE qt.type_key = :quota_type
        GROUP BY qt.type_key, qt.id
        """)
        
        result = await session.execute(query, {
            "quota_type": quota_type,
            "cutoff_date": cutoff_date
        })
        row = result.fetchone()
        
        if not row or row[0] is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quota type '{quota_type}' not found"
            )
        
        type_key, total_usage, total_calls, unique_users, avg_usage, peak_date = row
        
        return UsageStatistics(
            quota_type=type_key,
            total_usage=float(total_usage),
            total_calls=int(total_calls),
            unique_users=int(unique_users),
            avg_usage_per_call=float(avg_usage),
            peak_usage_date=str(peak_date) if peak_date else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quota statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch quota statistics"
        )


@router.post("/users/{user_id}/reset")
async def reset_user_quota(
    user_id: str,
    quota_type: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """Reset quota usage for a user
    
    If quota_type is specified, resets only that quota.
    Otherwise, resets all quotas for the user.
    """
    try:
        if quota_type:
            # Reset specific quota
            query = text("""
            UPDATE quota_limits ql
            SET used_amount = 0,
                updated_at = NOW()
            FROM quota_types qt
            WHERE ql.quota_type_id = qt.id
              AND ql.user_id = :user_id
              AND qt.type_key = :quota_type
            """)
            result = await session.execute(query, {
                "user_id": user_id,
                "quota_type": quota_type
            })
        else:
            # Reset all quotas
            query = text("""
            UPDATE quota_limits
            SET used_amount = 0,
                updated_at = NOW()
            WHERE user_id = :user_id
            """)
            result = await session.execute(query, {"user_id": user_id})
        
        await session.commit()
        
        affected_rows = result.rowcount
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quotas found to reset"
            )
        
        logger.info(f"Reset quotas for user {user_id}: {affected_rows} quota(s) reset")
        
        return {
            "message": "Quotas reset successfully",
            "user_id": user_id,
            "quotas_reset": affected_rows,
            "quota_type": quota_type or "all"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting user quotas: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset quotas"
        )


@router.put("/users/{user_id}/adjust")
async def adjust_user_quota(
    user_id: str,
    quota_type: str,
    new_limit: float = Query(..., description="New quota limit (-1 for unlimited)"),
    session: AsyncSession = Depends(get_db_session)
):
    """Adjust quota limit for a user
    
    Set new_limit to -1 for unlimited quota.
    """
    try:
        query = text("""
        UPDATE quota_limits ql
        SET limit_amount = :new_limit,
            updated_at = NOW()
        FROM quota_types qt
        WHERE ql.quota_type_id = qt.id
          AND ql.user_id = :user_id
          AND qt.type_key = :quota_type
        RETURNING ql.limit_amount, ql.used_amount
        """)
        
        result = await session.execute(query, {
            "user_id": user_id,
            "quota_type": quota_type,
            "new_limit": new_limit
        })
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quota '{quota_type}' not found for user {user_id}"
            )
        
        await session.commit()
        
        limit, used = row
        logger.info(f"Adjusted quota for user {user_id}: {quota_type} = {new_limit}")
        
        return {
            "message": "Quota adjusted successfully",
            "user_id": user_id,
            "quota_type": quota_type,
            "new_limit": float(limit) if limit != -1 else "unlimited",
            "current_usage": float(used),
            "remaining": float(limit - used) if limit != -1 else "unlimited"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adjusting user quota: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to adjust quota"
        )


@router.get("/health")
async def quota_admin_health():
    """Health check for admin quota endpoints"""
    return {
        "status": "healthy",
        "service": "quota-admin",
        "timestamp": datetime.utcnow().isoformat()
    }
