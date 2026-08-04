from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class UserLoginHistory(Base):
    __tablename__ = "user_login_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    location = Column(String, nullable=True)
    login_time = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="login_history")
