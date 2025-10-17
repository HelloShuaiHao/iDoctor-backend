from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...shared.database import Base


class QuotaUsage(Base):
    """
    Tracks actual usage of quotas by users across different applications and time periods.
    
    This model handles both real-time usage tracking and historical usage data
    for analytics and billing purposes.
    """
    __tablename__ = 'quota_usages'

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, nullable=False, index=True,
                     comment="User ID from auth service")
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False,
                            comment="Application where usage occurred")
    quota_type_id = Column(Integer, ForeignKey('quota_types.id'), nullable=False,
                           comment="Type of quota being tracked")
    quota_limit_id = Column(Integer, ForeignKey('quota_limits.id'), nullable=True,
                            comment="Associated quota limit (for current usage)")
    
    # Usage data
    usage_amount = Column(Numeric(precision=15, scale=3), nullable=False, default=0,
                          comment="Amount of quota consumed in this record")
    cumulative_usage = Column(Numeric(precision=15, scale=3), nullable=False, default=0,
                              comment="Total usage within the current time window")
    
    # Time window tracking
    window_start = Column(DateTime(timezone=True), nullable=False,
                          comment="Start of the time window this usage belongs to")
    window_end = Column(DateTime(timezone=True), nullable=False,
                        comment="End of the time window this usage belongs to")
    
    # Context information
    source_identifier = Column(String(200), nullable=True,
                               comment="Identifier for the source of usage (API endpoint, feature, etc.)")
    metadata = Column(Text, nullable=True,
                      comment="Additional context about the usage (JSON or text)")
    
    # Tracking
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(),
                         comment="When this usage was recorded")
    is_billable = Column(Boolean, default=True,
                         comment="Whether this usage counts towards billing")
    is_processed = Column(Boolean, default=False,
                          comment="Whether this usage has been processed for billing/analytics")
    
    # Relationships
    application = relationship("Application")
    quota_type = relationship("QuotaType", back_populates="quota_usages")
    quota_limit = relationship("QuotaLimit", back_populates="quota_usages")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_usage_user_app_type', 'user_id', 'application_id', 'quota_type_id'),
        Index('idx_usage_window', 'window_start', 'window_end'),
        Index('idx_usage_recorded', 'recorded_at'),
        Index('idx_usage_processing', 'is_processed', 'is_billable'),
    )
    
    def __repr__(self):
        return (f"<QuotaUsage(user={self.user_id}, app={self.application.app_key}, "
                f"quota={self.quota_type.quota_key}, amount={self.usage_amount})>")

    @property
    def usage_percentage(self):
        """Calculate usage percentage if quota limit is available"""
        if not self.quota_limit or self.quota_limit.is_unlimited:
            return None
        if self.quota_limit.limit_value <= 0:
            return 100.0  # Over limit
        return float((self.cumulative_usage / self.quota_limit.limit_value) * 100)

    @property
    def is_over_limit(self):
        """Check if current usage exceeds the quota limit"""
        if not self.quota_limit or self.quota_limit.is_unlimited:
            return False
        return self.cumulative_usage > self.quota_limit.limit_value

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'application_id': self.application_id,
            'quota_type_id': self.quota_type_id,
            'quota_limit_id': self.quota_limit_id,
            'usage_amount': float(self.usage_amount) if self.usage_amount else 0,
            'cumulative_usage': float(self.cumulative_usage) if self.cumulative_usage else 0,
            'window_start': self.window_start,
            'window_end': self.window_end,
            'source_identifier': self.source_identifier,
            'metadata': self.metadata,
            'recorded_at': self.recorded_at,
            'is_billable': self.is_billable,
            'is_processed': self.is_processed,
            'usage_percentage': self.usage_percentage,
            'is_over_limit': self.is_over_limit,
            # Include related data
            'application': self.application.to_dict() if self.application else None,
            'quota_type': self.quota_type.to_dict() if self.quota_type else None,
            'quota_limit': self.quota_limit.to_dict() if self.quota_limit else None
        }