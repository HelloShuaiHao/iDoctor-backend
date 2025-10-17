from typing import Optional, Dict, Any, Callable
from functools import wraps
from decimal import Decimal
import json
import time
from flask import request, g, current_app
from sqlalchemy.orm import Session
from .quota_manager import QuotaManager
from ...shared.exceptions import QuotaExceededError


class UsageTracker:
    """
    Usage tracking service with decorators and middleware for automatic quota enforcement.
    
    This provides easy integration patterns for applications to track and enforce quotas
    without complex boilerplate code.
    """
    
    def __init__(self, db: Session, quota_manager: QuotaManager = None):
        self.db = db
        self.quota_manager = quota_manager or QuotaManager(db)

    def quota_required(
        self, 
        app_key: str, 
        quota_key: str, 
        amount: Decimal = Decimal('1'),
        get_user_id: Callable = None,
        source_identifier: str = None,
        allow_overuse: bool = False,
        skip_if_unlimited: bool = True
    ):
        """
        Decorator for Flask routes to automatically enforce quota limits.
        
        Usage:
        @app.route('/api/analysis')
        @quota_required('idoctor', 'ai_analysis', amount=Decimal('1'))
        def analyze_medical_data():
            # Your API logic here
            pass
        
        Args:
            app_key: Application key
            quota_key: Quota type to check
            amount: Amount to consume (default 1)
            get_user_id: Function to get user_id from request context
            source_identifier: Identifier for the source (will use route if None)
            allow_overuse: Allow consumption even over limit
            skip_if_unlimited: Skip tracking for unlimited quotas
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get user ID from context or function
                user_id = self._get_user_id(get_user_id)
                if not user_id:
                    raise QuotaExceededError("User authentication required for quota tracking")
                
                # Get source identifier
                source = source_identifier or (
                    f"{request.method} {request.endpoint}" if request else f.__name__
                )
                
                # Check and consume quota
                try:
                    # Check availability first
                    availability = self.quota_manager.check_quota_availability(
                        user_id, app_key, quota_key, amount
                    )
                    
                    if not availability['available'] and not allow_overuse:
                        raise QuotaExceededError(
                            f"Quota exceeded for {quota_key}: {availability['reason']}"
                        )
                    
                    # Skip tracking for unlimited quotas if requested
                    if skip_if_unlimited and availability.get('limit_value') == -1:
                        return f(*args, **kwargs)
                    
                    # Record the usage
                    usage_record = self.quota_manager.consume_quota(
                        user_id=user_id,
                        app_key=app_key,
                        quota_key=quota_key,
                        amount=amount,
                        source_identifier=source,
                        metadata=self._build_metadata(request),
                        allow_overuse=allow_overuse
                    )
                    
                    # Store usage info in request context for potential use by the route
                    g.quota_usage = usage_record
                    g.quota_info = availability
                    
                    return f(*args, **kwargs)
                    
                except QuotaExceededError:
                    # Log the quota violation attempt
                    self._log_quota_violation(user_id, app_key, quota_key, amount, source)
                    raise
                    
            return decorated_function
        return decorator

    def track_usage(
        self,
        user_id: int,
        app_key: str,
        quota_key: str,
        amount: Decimal = Decimal('1'),
        source_identifier: str = None,
        metadata: Dict[str, Any] = None,
        allow_overuse: bool = False
    ):
        """
        Directly track usage without enforcement (for background tasks, etc.)
        """
        try:
            usage_record = self.quota_manager.consume_quota(
                user_id=user_id,
                app_key=app_key,
                quota_key=quota_key,
                amount=amount,
                source_identifier=source_identifier,
                metadata=json.dumps(metadata) if metadata else None,
                allow_overuse=allow_overuse
            )
            return usage_record
        except QuotaExceededError as e:
            self._log_quota_violation(user_id, app_key, quota_key, amount, source_identifier)
            if not allow_overuse:
                raise
            return None

    def check_quota(
        self,
        user_id: int,
        app_key: str,
        quota_key: str,
        requested_amount: Decimal = Decimal('1')
    ) -> Dict[str, Any]:
        """
        Check quota availability without consuming it.
        """
        return self.quota_manager.check_quota_availability(
            user_id, app_key, quota_key, requested_amount
        )

    def get_user_quotas(self, user_id: int, app_key: str = None) -> Dict[str, Any]:
        """
        Get all quotas for a user with current usage information.
        """
        quota_summary = self.quota_manager.get_user_quota_summary(user_id, app_key)
        
        return {
            'user_id': user_id,
            'application': app_key,
            'quotas': quota_summary,
            'total_quotas': len(quota_summary),
            'over_limit_quotas': len([q for q in quota_summary if q['is_over_limit']])
        }

    def rate_limit(
        self,
        app_key: str,
        requests_per_minute: int = 60,
        get_user_id: Callable = None,
        key_func: Callable = None
    ):
        """
        Rate limiting decorator using quota system.
        
        Args:
            app_key: Application key
            requests_per_minute: Number of requests allowed per minute
            get_user_id: Function to get user ID
            key_func: Function to generate rate limit key (default: user-based)
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Generate rate limit key
                if key_func:
                    rate_key = key_func()
                else:
                    user_id = self._get_user_id(get_user_id)
                    rate_key = f"rate_limit_user_{user_id}" if user_id else f"rate_limit_ip_{request.remote_addr}"
                
                # Use minute-based quota for rate limiting
                quota_key = f"rate_limit_{requests_per_minute}pm"
                
                # Create or update rate limit quota type if it doesn't exist
                self._ensure_rate_limit_quota(app_key, quota_key, requests_per_minute)
                
                # Check rate limit
                user_id = self._get_user_id(get_user_id) or 0  # Use 0 for anonymous users
                
                try:
                    availability = self.quota_manager.check_quota_availability(
                        user_id, app_key, quota_key, Decimal('1')
                    )
                    
                    if not availability['available']:
                        raise QuotaExceededError(f"Rate limit exceeded: {availability['reason']}")
                    
                    # Consume rate limit quota
                    self.quota_manager.consume_quota(
                        user_id=user_id,
                        app_key=app_key,
                        quota_key=quota_key,
                        amount=Decimal('1'),
                        source_identifier=f"rate_limit_{f.__name__}",
                        metadata=json.dumps({
                            'rate_limit_key': rate_key,
                            'endpoint': request.endpoint if request else f.__name__,
                            'method': request.method if request else 'UNKNOWN'
                        })
                    )
                    
                    return f(*args, **kwargs)
                    
                except QuotaExceededError:
                    # Could implement more sophisticated rate limit response here
                    raise
                    
            return decorated_function
        return decorator

    def _get_user_id(self, get_user_id_func: Callable = None) -> Optional[int]:
        """Extract user ID from request context"""
        if get_user_id_func:
            return get_user_id_func()
        
        # Try common patterns for user ID extraction
        if hasattr(g, 'current_user') and g.current_user:
            return getattr(g.current_user, 'id', None)
        
        if hasattr(g, 'user_id'):
            return g.user_id
            
        # Try JWT payload if available
        if hasattr(g, 'jwt_payload') and g.jwt_payload:
            return g.jwt_payload.get('user_id') or g.jwt_payload.get('sub')
        
        return None

    def _build_metadata(self, request) -> str:
        """Build metadata from request context"""
        if not request:
            return None
        
        metadata = {
            'endpoint': request.endpoint,
            'method': request.method,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'timestamp': time.time()
        }
        
        return json.dumps(metadata)

    def _log_quota_violation(
        self, 
        user_id: int, 
        app_key: str, 
        quota_key: str, 
        amount: Decimal, 
        source: str
    ):
        """Log quota violations for monitoring and analysis"""
        violation_data = {
            'user_id': user_id,
            'app_key': app_key,
            'quota_key': quota_key,
            'attempted_amount': float(amount),
            'source': source,
            'timestamp': time.time()
        }
        
        # Log to application logger
        if current_app:
            current_app.logger.warning(
                f"Quota violation: {json.dumps(violation_data)}"
            )

    def _ensure_rate_limit_quota(self, app_key: str, quota_key: str, requests_per_minute: int):
        """Ensure rate limit quota type exists"""
        try:
            # Try to get existing quota type
            self.quota_manager._get_quota_type(app_key, quota_key)
        except:
            # Create rate limit quota type if it doesn't exist
            from .application_manager import ApplicationManager
            app_manager = ApplicationManager(self.db)
            
            try:
                app_manager.add_quota_type(
                    app_key=app_key,
                    quota_key=quota_key,
                    quota_name=f"Rate Limit ({requests_per_minute}/min)",
                    description=f"Rate limiting: {requests_per_minute} requests per minute",
                    unit="count",
                    time_window="minute",
                    is_cumulative=True
                )
                
                # Set default rate limit for all users
                # This would typically be done during application setup
                
            except Exception as e:
                # Rate limit quota creation failed - log and continue
                if current_app:
                    current_app.logger.error(f"Failed to create rate limit quota: {e}")


class QuotaMiddleware:
    """
    Flask middleware for automatic quota tracking on all requests.
    
    This can be used to track general API usage across all endpoints.
    """
    
    def __init__(self, app=None, db_session_factory=None, app_key=None):
        self.app = app
        self.db_session_factory = db_session_factory
        self.app_key = app_key
        
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """Check quotas before processing request"""
        # Skip non-API endpoints
        if not request.endpoint or not request.endpoint.startswith('api.'):
            return
        
        # Skip if no app key configured
        if not self.app_key:
            return
            
        # Get user ID
        user_id = self._get_user_id()
        if not user_id:
            return  # Skip anonymous requests or handle differently
        
        # Check general API quota
        db = self.db_session_factory()
        try:
            usage_tracker = UsageTracker(db)
            
            # Check API calls quota
            availability = usage_tracker.check_quota(
                user_id=user_id,
                app_key=self.app_key,
                quota_key='api_calls',
                requested_amount=Decimal('1')
            )
            
            if not availability['available']:
                raise QuotaExceededError(f"API quota exceeded: {availability['reason']}")
            
            # Store quota info for after_request
            g.quota_tracker = usage_tracker
            g.api_quota_user_id = user_id
            
        finally:
            db.close()

    def after_request(self, response):
        """Track usage after successful request"""
        # Only track successful API requests
        if (hasattr(g, 'quota_tracker') and 
            hasattr(g, 'api_quota_user_id') and 
            200 <= response.status_code < 300):
            
            try:
                g.quota_tracker.track_usage(
                    user_id=g.api_quota_user_id,
                    app_key=self.app_key,
                    quota_key='api_calls',
                    amount=Decimal('1'),
                    source_identifier=f"{request.method} {request.endpoint}",
                    metadata={
                        'status_code': response.status_code,
                        'content_length': response.content_length
                    },
                    allow_overuse=False
                )
            except Exception as e:
                # Log error but don't fail the request
                current_app.logger.error(f"Failed to track quota usage: {e}")
        
        return response

    def _get_user_id(self) -> Optional[int]:
        """Extract user ID from request context"""
        # Same logic as UsageTracker._get_user_id
        if hasattr(g, 'current_user') and g.current_user:
            return getattr(g.current_user, 'id', None)
        
        if hasattr(g, 'user_id'):
            return g.user_id
            
        if hasattr(g, 'jwt_payload') and g.jwt_payload:
            return g.jwt_payload.get('user_id') or g.jwt_payload.get('sub')
        
        return None