"""支付交易模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from commercial.shared.database import Base


class PaymentTransaction(Base):
    """支付交易表"""
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("user_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)  # 金额
    currency = Column(String(10), default="CNY", nullable=False)  # 货币
    payment_method = Column(String(20), nullable=False)  # alipay/wechat/stripe
    payment_provider_id = Column(String(255), nullable=True, index=True)  # 第三方交易ID
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending/completed/failed/refunded
    extra_data = Column(JSON, nullable=True)  # 额外信息
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="transactions")
    subscription = relationship("UserSubscription", back_populates="transactions")

    def __repr__(self):
        return f"<PaymentTransaction(id={self.id}, amount={self.amount}, status={self.status})>"
