from sqlalchemy import Table, Column, Integer, ForeignKey
from app.database import Base

vehicle_user_association = Table(
    "vehicle_user_association",
    Base.metadata,
    Column("vehicle_id", Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

job_user_association = Table(
    "job_user_association",
    Base.metadata,
    Column("job_id", Integer, ForeignKey("production_jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)
