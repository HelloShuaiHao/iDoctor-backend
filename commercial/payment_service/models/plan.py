"""订阅计划模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from commercial.shared.database import Base


class SubscriptionPlan(Base):
    """订阅计划表"""
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)  # 例如: "免费版", "专业版", "企业版"
    description = Column(String(500), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)  # 价格
    currency = Column(String(10), default="CNY", nullable=False)  # 货币: CNY, USD
    billing_cycle = Column(String(20), nullable=False)  # monthly/yearly/lifetime
    quota_type = Column(String(50), nullable=False)  # 例如: "processing_count"
    quota_limit = Column(Integer, nullable=False)  # 配额限制（例如：每月处理次数）
    features = Column(JSON, nullable=True)  # 功能列表 JSON
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    subscriptions = relationship("UserSubscription", back_populates="plan")

    def __repr__(self):
        return f"<SubscriptionPlan(id={self.id}, name={self.name})>"
