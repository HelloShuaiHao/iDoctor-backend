from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models.application import Application
from ..models.quota_type import QuotaType, QuotaTimeWindow
from ...shared.exceptions import ValidationError, NotFoundError


class ApplicationManager:
    """
    Manages application registration and configuration for multi-application quota support.
    
    This allows the commercial module to support multiple applications (iDoctor, other medical apps)
    without duplicating authentication and payment infrastructure.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def register_application(
        self, 
        app_key: str, 
        app_name: str,
        description: str = None,
        config: Dict[str, Any] = None,
        quota_types: List[Dict[str, Any]] = None
    ) -> Application:
        """
        Register a new application with its quota types.
        
        Args:
            app_key: Unique application identifier
            app_name: Human-readable application name
            description: Application description
            config: Application-specific configuration
            quota_types: List of quota type definitions for this app
            
        Returns:
            Created Application instance
        """
        # Validate app_key uniqueness
        existing_app = self.db.query(Application).filter_by(app_key=app_key).first()
        if existing_app:
            raise ValidationError(f"Application with key '{app_key}' already exists")
        
        try:
            # Create application
            application = Application(
                app_key=app_key,
                app_name=app_name,
                description=description,
                config=config or {},
                is_active=True
            )
            self.db.add(application)
            self.db.flush()  # Get the ID
            
            # Create quota types for this application
            if quota_types:
                for quota_def in quota_types:
                    self._create_quota_type(application.id, quota_def)
            
            self.db.commit()
            return application
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Failed to register application: {str(e)}")

    def _create_quota_type(self, application_id: int, quota_def: Dict[str, Any]) -> QuotaType:
        """Create a quota type for an application"""
        quota_type = QuotaType(
            application_id=application_id,
            quota_key=quota_def['quota_key'],
            quota_name=quota_def['quota_name'],
            description=quota_def.get('description'),
            unit=quota_def.get('unit', 'count'),
            time_window=QuotaTimeWindow(quota_def.get('time_window', 'month')),
            is_cumulative=quota_def.get('is_cumulative', True),
            is_active=quota_def.get('is_active', True)
        )
        self.db.add(quota_type)
        return quota_type

    def get_application(self, app_key: str) -> Application:
        """Get application by key"""
        app = self.db.query(Application).filter_by(app_key=app_key, is_active=True).first()
        if not app:
            raise NotFoundError(f"Application '{app_key}' not found")
        return app

    def list_applications(self, include_inactive: bool = False) -> List[Application]:
        """List all registered applications"""
        query = self.db.query(Application)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.all()

    def update_application_config(self, app_key: str, config: Dict[str, Any]) -> Application:
        """Update application configuration"""
        app = self.get_application(app_key)
        app.config.update(config)
        self.db.commit()
        return app

    def add_quota_type(
        self, 
        app_key: str, 
        quota_key: str, 
        quota_name: str,
        **kwargs
    ) -> QuotaType:
        """Add a new quota type to an existing application"""
        app = self.get_application(app_key)
        
        # Check for duplicate quota_key within the application
        existing = (self.db.query(QuotaType)
                   .filter_by(application_id=app.id, quota_key=quota_key)
                   .first())
        if existing:
            raise ValidationError(f"Quota type '{quota_key}' already exists for application '{app_key}'")
        
        quota_def = {
            'quota_key': quota_key,
            'quota_name': quota_name,
            **kwargs
        }
        
        quota_type = self._create_quota_type(app.id, quota_def)
        self.db.commit()
        return quota_type

    def get_application_quota_types(self, app_key: str) -> List[QuotaType]:
        """Get all quota types for an application"""
        app = self.get_application(app_key)
        return (self.db.query(QuotaType)
               .filter_by(application_id=app.id, is_active=True)
               .all())

    def deactivate_application(self, app_key: str) -> Application:
        """Deactivate an application (soft delete)"""
        app = self.get_application(app_key)
        app.is_active = False
        self.db.commit()
        return app

    def get_app_config_template(self, app_type: str = "medical") -> Dict[str, Any]:
        """
        Get configuration template for different application types.
        
        This helps standardize quota types across similar applications.
        """
        templates = {
            "medical": {
                "quota_types": [
                    {
                        "quota_key": "api_calls",
                        "quota_name": "API Calls",
                        "description": "Number of API requests per month",
                        "unit": "count",
                        "time_window": "month",
                        "is_cumulative": True
                    },
                    {
                        "quota_key": "storage_gb", 
                        "quota_name": "Storage Space",
                        "description": "Storage space in gigabytes",
                        "unit": "gb",
                        "time_window": "lifetime",
                        "is_cumulative": True
                    },
                    {
                        "quota_key": "ai_analysis",
                        "quota_name": "AI Analysis",
                        "description": "AI-powered medical analysis requests",
                        "unit": "count", 
                        "time_window": "month",
                        "is_cumulative": True
                    },
                    {
                        "quota_key": "premium_features",
                        "quota_name": "Premium Features",
                        "description": "Access to premium features",
                        "unit": "boolean",
                        "time_window": "lifetime",
                        "is_cumulative": False
                    }
                ],
                "config": {
                    "billing_currency": "CNY",
                    "default_time_zone": "Asia/Shanghai",
                    "rate_limit_per_minute": 100
                }
            }
        }
        
        return templates.get(app_type, templates["medical"])