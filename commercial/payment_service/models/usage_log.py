"""使用记录模型"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from commercial.shared.database import Base


class UsageLog(Base):
    """使用记录表"""
    __tablename__ = "usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("user_subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # 例如: "dicom_processing"
    resource_id = Column(String(255), nullable=True)  # 例如: 任务ID
    quota_cost = Column(Integer, default=1, nullable=False)  # 消耗的配额数
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    extra_info = Column(JSON, nullable=True)  # 额外信息（如处理时长）

    # 关系（仅包含本服务内的关系）
    subscription = relationship("UserSubscription", back_populates="usage_logs")
    # 注意：user 关系由认证服务管理，这里仅通过 user_id 外键引用

    def __repr__(self):
        return f"<UsageLog(id={self.id}, resource_type={self.resource_type}, cost={self.quota_cost})>"
