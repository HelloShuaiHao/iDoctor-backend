"""用户订阅模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from commercial.shared.database import Base


class UserSubscription(Base):
    """用户订阅表"""
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(String(20), default="active", nullable=False)  # active/cancelled/expired
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    quota_used = Column(Integer, default=0, nullable=False)  # 当前周期已使用配额
    quota_limit = Column(Integer, nullable=False)  # 配额上限（冗余存储，便于查询）
    auto_renew = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系（仅包含本服务内的关系）
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    transactions = relationship("PaymentTransaction", back_populates="subscription")
    usage_logs = relationship("UsageLog", back_populates="subscription")
    # 注意：user 关系由认证服务管理，这里仅通过 user_id 外键引用

    def __repr__(self):
        return f"<UserSubscription(id={self.id}, user_id={self.user_id}, status={self.status})>"
