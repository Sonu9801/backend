from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

component_worker_association = Table(
    'component_worker_association', Base.metadata,
    Column('component_task_id', Integer, ForeignKey('component_tasks.id')),
    Column('worker_id', Integer, ForeignKey('users.id'))
)

class ComponentTask(Base):
    __tablename__ = "component_tasks"

    id = Column(Integer, primary_key=True, index=True)
    component_type = Column(String, nullable=False) # Platform, Gate, Aircutter, Paint
    component_number = Column(String, nullable=False, index=True)
    status = Column(String, default="in_progress") # in_progress, completed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    photo_proof_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    workers = relationship("User", secondary=component_worker_association, backref="component_tasks")
