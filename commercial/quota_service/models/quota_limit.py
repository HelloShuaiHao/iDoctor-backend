from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...shared.database import Base


class QuotaLimit(Base):
    """
    Defines quota limits for users within specific applications and subscription plans.
    
    Links users, subscriptions, applications, and quota types to define
    how much of each resource a user can consume.
    """
    __tablename__ = 'quota_limits'

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, nullable=False, index=True,
                     comment="User ID from auth service")
    subscription_id = Column(Integer, nullable=True, index=True,
                             comment="Subscription plan ID (null for default/free limits)")
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False,
                            comment="Application this limit applies to")
    quota_type_id = Column(Integer, ForeignKey('quota_types.id'), nullable=False,
                           comment="Type of quota this limit defines")
    
    # Limit configuration
    limit_value = Column(Numeric(precision=15, scale=3), nullable=False, default=0,
                         comment="Maximum allowed usage for this quota")
    is_unlimited = Column(Boolean, default=False,
                          comment="Whether this quota has no limit")
    
    # Validity period
    valid_from = Column(DateTime(timezone=True), server_default=func.now(),
                        comment="When this limit becomes active")
    valid_until = Column(DateTime(timezone=True), nullable=True,
                         comment="When this limit expires (null = no expiration)")
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False,
                       comment="Whether this limit is currently active")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True,
                        comment="Who created this limit (system, admin, etc.)")
    
    # Relationships
    application = relationship("Application", back_populates="quota_limits")
    quota_type = relationship("QuotaType", back_populates="quota_limits")
    quota_usages = relationship("QuotaUsage", back_populates="quota_limit")
    
    def __repr__(self):
        return (f"<QuotaLimit(user={self.user_id}, app={self.application.app_key}, "
                f"quota={self.quota_type.quota_key}, limit={self.limit_value})>")

    @property
    def is_valid(self):
        """Check if this limit is currently valid"""
        now = func.now()
        return (self.is_active and 
                self.valid_from <= now and 
                (self.valid_until is None or self.valid_until > now))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'application_id': self.application_id,
            'quota_type_id': self.quota_type_id,
            'limit_value': float(self.limit_value) if self.limit_value else 0,
            'is_unlimited': self.is_unlimited,
            'valid_from': self.valid_from,
            'valid_until': self.valid_until,
            'is_active': self.is_active,
            'is_valid': self.is_valid,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            # Include related data
            'application': self.application.to_dict() if self.application else None,
            'quota_type': self.quota_type.to_dict() if self.quota_type else None
        }