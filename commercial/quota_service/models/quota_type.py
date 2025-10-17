from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...shared.database import Base


class QuotaTimeWindow(str, Enum):
    """Time windows for quota limits"""
    MINUTE = "minute"
    HOUR = "hour" 
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    LIFETIME = "lifetime"


class QuotaType(Base):
    """
    Defines different types of quotas that can be applied across applications.
    
    Examples:
    - API calls per day/month
    - Storage space in GB
    - Feature access (boolean)
    - Processing time in minutes
    - Number of users/projects
    """
    __tablename__ = 'quota_types'

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False,
                            comment="Application this quota type belongs to")
    
    # Quota definition
    quota_key = Column(String(100), nullable=False, index=True,
                       comment="Unique key within application (e.g., 'api_calls', 'storage_gb')")
    quota_name = Column(String(100), nullable=False,
                        comment="Human-readable name")
    description = Column(Text,
                         comment="Description of what this quota measures")
    
    # Configuration
    unit = Column(String(20), default="count",
                  comment="Unit of measurement (count, gb, minutes, etc.)")
    time_window = Column(SQLEnum(QuotaTimeWindow), default=QuotaTimeWindow.MONTH,
                         comment="Time window for quota reset")
    is_cumulative = Column(Boolean, default=True,
                           comment="Whether usage accumulates or resets per window")
    is_active = Column(Boolean, default=True, nullable=False,
                       comment="Whether this quota type is active")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="quota_types")
    quota_limits = relationship("QuotaLimit", back_populates="quota_type")
    quota_usages = relationship("QuotaUsage", back_populates="quota_type")
    
    def __repr__(self):
        return f"<QuotaType(app={self.application.app_key}, key='{self.quota_key}')>"

    @property
    def full_key(self):
        """Returns application.quota_key for unique identification"""
        return f"{self.application.app_key}.{self.quota_key}"

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'quota_key': self.quota_key,
            'quota_name': self.quota_name,
            'description': self.description,
            'unit': self.unit,
            'time_window': self.time_window.value if self.time_window else None,
            'is_cumulative': self.is_cumulative,
            'is_active': self.is_active,
            'full_key': self.full_key,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }