from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SalaryProfile(Base):
    __tablename__ = "salary_profiles"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), unique=True)
    salary_type = Column(String)  # Monthly, DailyWage
    monthly_salary = Column(Float, nullable=True)
    daily_wage = Column(Float, nullable=True)
    ot_rate_per_hour = Column(Float, default=0.0)
    sunday_rate_per_hour = Column(Float, default=0.0)

    worker = relationship("User", back_populates="salary_profile", foreign_keys=[worker_id])
