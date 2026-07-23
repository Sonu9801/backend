from sqlalchemy import Column, Integer, String
from app.database import Base

class Shift(Base):
    __tablename__ = 'shifts'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_time = Column(String)  # e.g., '09:00:00'
    end_time = Column(String)    # e.g., '18:00:00'
