from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...shared.database import Base


class Application(Base):
    """
    Application registration model for multi-application quota management.
    
    Allows the quota system to support different applications (iDoctor, other medical apps, etc.)
    with their own specific quota types and configurations.
    """
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True, index=True)
    app_key = Column(String(50), unique=True, index=True, nullable=False, 
                     comment="Unique identifier for the application")
    app_name = Column(String(100), nullable=False,
                      comment="Human-readable application name")
    description = Column(Text,
                         comment="Application description and purpose")
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False,
                       comment="Whether the application is active")
    config = Column(JSON, default={},
                    comment="Application-specific configuration (quota types, limits, etc.)")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    quota_types = relationship("QuotaType", back_populates="application", cascade="all, delete-orphan")
    quota_limits = relationship("QuotaLimit", back_populates="application")

    def __repr__(self):
        return f"<Application(app_key='{self.app_key}', name='{self.app_name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'app_key': self.app_key,
            'app_name': self.app_name,
            'description': self.description,
            'is_active': self.is_active,
            'config': self.config,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }