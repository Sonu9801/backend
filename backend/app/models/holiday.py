from sqlalchemy import Column, Integer, String, Date
from app.database import Base

class Holiday(Base):
    __tablename__ = 'holidays'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    name = Column(String)
    type = Column(String)  # 'National', 'Optional', 'Festival', etc.
