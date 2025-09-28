from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, TimestampMixin

class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_type = Column(String, nullable=False, index=True)
    status = Column(String, default="queued", nullable=False, index=True)  # queued, processing, completed, failed, cancelled
    parameters = Column(Text)  # JSON parameters
    result = Column(Text)  # JSON result
    error_message = Column(Text)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationship with user
    user = relationship("User", back_populates="jobs")