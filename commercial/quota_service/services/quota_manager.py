from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from ..models.application import Application
from ..models.quota_type import QuotaType, QuotaTimeWindow
from ..models.quota_limit import QuotaLimit
from ..models.quota_usage import QuotaUsage
from ...shared.exceptions import ValidationError, NotFoundError, QuotaExceededError


class QuotaManager:
    """
    Core quota management service that handles quota limits, enforcement, and validation
    across multiple applications.
    
    This is the main service that applications will interact with for quota operations.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def check_quota_availability(
        self, 
        user_id: int, 
        app_key: str, 
        quota_key: str,
        requested_amount: Decimal = Decimal('1')
    ) -> Dict[str, Any]:
        """
        Check if a user can consume a certain amount of quota.
        
        Returns detailed information about quota status and availability.
        """
        # Get quota type and current limit
        quota_type = self._get_quota_type(app_key, quota_key)
        quota_limit = self._get_user_quota_limit(user_id, quota_type.id)
        
        if not quota_limit:
            # No quota limit found - deny by default for security
            return {
                'available': False,
                'reason': 'No quota limit configured for user',
                'limit_value': 0,
                'current_usage': 0,
                'remaining': 0,
                'percentage_used': 100.0
            }
        
        # Check if quota is unlimited
        if quota_limit.is_unlimited:
            return {
                'available': True,
                'reason': 'Unlimited quota',
                'limit_value': -1,  # -1 indicates unlimited
                'current_usage': 0,
                'remaining': -1,
                'percentage_used': 0.0
            }
        
        # Get current usage within the time window
        current_usage = self._get_current_usage(user_id, quota_type, quota_limit)
        remaining = quota_limit.limit_value - current_usage
        percentage_used = float((current_usage / quota_limit.limit_value) * 100) if quota_limit.limit_value > 0 else 100.0
        
        available = remaining >= requested_amount
        
        return {
            'available': available,
            'reason': 'Sufficient quota' if available else f'Insufficient quota (need {requested_amount}, have {remaining})',
            'limit_value': float(quota_limit.limit_value),
            'current_usage': float(current_usage),
            'remaining': float(remaining),
            'percentage_used': percentage_used,
            'quota_type': quota_type.to_dict(),
            'quota_limit': quota_limit.to_dict()
        }

    def consume_quota(
        self, 
        user_id: int, 
        app_key: str, 
        quota_key: str,
        amount: Decimal = Decimal('1'),
        source_identifier: str = None,
        metadata: str = None,
        allow_overuse: bool = False
    ) -> QuotaUsage:
        """
        Consume quota for a user. This is the main method applications use to track usage.
        
        Args:
            user_id: User consuming the quota
            app_key: Application key
            quota_key: Quota type key
            amount: Amount to consume
            source_identifier: Source of the consumption (API endpoint, feature, etc.)
            metadata: Additional context
            allow_overuse: Whether to allow consumption even if over limit
            
        Returns:
            QuotaUsage record
        """
        # Check availability first
        availability = self.check_quota_availability(user_id, app_key, quota_key, amount)
        
        if not availability['available'] and not allow_overuse:
            raise QuotaExceededError(f"Quota exceeded: {availability['reason']}")
        
        # Get quota type and limit
        quota_type = self._get_quota_type(app_key, quota_key)
        quota_limit = self._get_user_quota_limit(user_id, quota_type.id)
        
        # Calculate time window for this usage
        window_start, window_end = self._calculate_time_window(quota_type.time_window)
        
        # Get or create current usage record for this window
        current_usage_record = (
            self.db.query(QuotaUsage)
            .filter(and_(
                QuotaUsage.user_id == user_id,
                QuotaUsage.quota_type_id == quota_type.id,
                QuotaUsage.window_start == window_start,
                QuotaUsage.window_end == window_end
            ))
            .first()
        )
        
        if current_usage_record:
            # Update existing usage
            current_usage_record.usage_amount += amount
            current_usage_record.cumulative_usage += amount
            current_usage_record.recorded_at = func.now()
            if source_identifier:
                current_usage_record.source_identifier = source_identifier
            if metadata:
                current_usage_record.metadata = metadata
            usage_record = current_usage_record
        else:
            # Create new usage record
            usage_record = QuotaUsage(
                user_id=user_id,
                application_id=quota_type.application_id,
                quota_type_id=quota_type.id,
                quota_limit_id=quota_limit.id if quota_limit else None,
                usage_amount=amount,
                cumulative_usage=amount,
                window_start=window_start,
                window_end=window_end,
                source_identifier=source_identifier,
                metadata=metadata,
                is_billable=True,
                is_processed=False
            )
            self.db.add(usage_record)
        
        self.db.commit()
        return usage_record

    def set_user_quota_limit(
        self,
        user_id: int,
        app_key: str,
        quota_key: str,
        limit_value: Decimal,
        subscription_id: int = None,
        valid_until: datetime = None,
        is_unlimited: bool = False,
        created_by: str = None
    ) -> QuotaLimit:
        """
        Set or update a quota limit for a user.
        
        This is typically called when a user subscribes to a plan or when an admin
        manually adjusts quotas.
        """
        quota_type = self._get_quota_type(app_key, quota_key)
        
        # Check for existing limit
        existing_limit = self._get_user_quota_limit(user_id, quota_type.id)
        
        if existing_limit:
            # Update existing limit
            existing_limit.limit_value = limit_value
            existing_limit.subscription_id = subscription_id
            existing_limit.valid_until = valid_until
            existing_limit.is_unlimited = is_unlimited
            existing_limit.updated_at = func.now()
            if created_by:
                existing_limit.created_by = created_by
            self.db.commit()
            return existing_limit
        else:
            # Create new limit
            quota_limit = QuotaLimit(
                user_id=user_id,
                subscription_id=subscription_id,
                application_id=quota_type.application_id,
                quota_type_id=quota_type.id,
                limit_value=limit_value,
                is_unlimited=is_unlimited,
                valid_until=valid_until,
                is_active=True,
                created_by=created_by or 'system'
            )
            self.db.add(quota_limit)
            self.db.commit()
            return quota_limit

    def get_user_quota_summary(self, user_id: int, app_key: str = None) -> List[Dict[str, Any]]:
        """
        Get comprehensive quota summary for a user across all applications or a specific app.
        """
        query = (
            self.db.query(QuotaLimit)
            .join(QuotaType)
            .join(Application)
            .filter(QuotaLimit.user_id == user_id)
            .filter(QuotaLimit.is_active == True)
            .filter(Application.is_active == True)
        )
        
        if app_key:
            query = query.filter(Application.app_key == app_key)
        
        quota_limits = query.all()
        summary = []
        
        for limit in quota_limits:
            current_usage = self._get_current_usage(user_id, limit.quota_type, limit)
            remaining = limit.limit_value - current_usage if not limit.is_unlimited else -1
            percentage_used = (
                float((current_usage / limit.limit_value) * 100) 
                if not limit.is_unlimited and limit.limit_value > 0 
                else 0.0
            )
            
            summary.append({
                'application': limit.application.to_dict(),
                'quota_type': limit.quota_type.to_dict(),
                'limit': limit.to_dict(),
                'current_usage': float(current_usage),
                'remaining': float(remaining) if remaining != -1 else -1,
                'percentage_used': percentage_used,
                'is_over_limit': current_usage > limit.limit_value if not limit.is_unlimited else False
            })
        
        return summary

    def _get_quota_type(self, app_key: str, quota_key: str) -> QuotaType:
        """Get quota type by application and quota keys"""
        quota_type = (
            self.db.query(QuotaType)
            .join(Application)
            .filter(and_(
                Application.app_key == app_key,
                Application.is_active == True,
                QuotaType.quota_key == quota_key,
                QuotaType.is_active == True
            ))
            .first()
        )
        
        if not quota_type:
            raise NotFoundError(f"Quota type '{quota_key}' not found for application '{app_key}'")
        
        return quota_type

    def _get_user_quota_limit(self, user_id: int, quota_type_id: int) -> Optional[QuotaLimit]:
        """Get active quota limit for a user and quota type"""
        now = datetime.utcnow()
        
        return (
            self.db.query(QuotaLimit)
            .filter(and_(
                QuotaLimit.user_id == user_id,
                QuotaLimit.quota_type_id == quota_type_id,
                QuotaLimit.is_active == True,
                QuotaLimit.valid_from <= now,
                or_(
                    QuotaLimit.valid_until.is_(None),
                    QuotaLimit.valid_until > now
                )
            ))
            .order_by(QuotaLimit.created_at.desc())
            .first()
        )

    def _get_current_usage(self, user_id: int, quota_type: QuotaType, quota_limit: QuotaLimit) -> Decimal:
        """Get current usage amount within the quota's time window"""
        window_start, window_end = self._calculate_time_window(quota_type.time_window)
        
        usage_sum = (
            self.db.query(func.sum(QuotaUsage.usage_amount))
            .filter(and_(
                QuotaUsage.user_id == user_id,
                QuotaUsage.quota_type_id == quota_type.id,
                QuotaUsage.window_start >= window_start,
                QuotaUsage.window_end <= window_end,
                QuotaUsage.is_billable == True
            ))
            .scalar()
        )
        
        return usage_sum or Decimal('0')

    def _calculate_time_window(self, time_window: QuotaTimeWindow) -> Tuple[datetime, datetime]:
        """Calculate the start and end of the time window for quota tracking"""
        now = datetime.utcnow()
        
        if time_window == QuotaTimeWindow.MINUTE:
            start = now.replace(second=0, microsecond=0)
            end = start + timedelta(minutes=1)
        elif time_window == QuotaTimeWindow.HOUR:
            start = now.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
        elif time_window == QuotaTimeWindow.DAY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif time_window == QuotaTimeWindow.WEEK:
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(weeks=1)
        elif time_window == QuotaTimeWindow.MONTH:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        elif time_window == QuotaTimeWindow.YEAR:
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1)
        else:  # LIFETIME
            start = datetime(1970, 1, 1)  # Unix epoch
            end = datetime(2099, 12, 31)  # Far future
        
        return start, end