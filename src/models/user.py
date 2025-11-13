from sqlalchemy import Column, String, DateTime, Date
from sqlalchemy.sql import func

from ..core.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    firebase_uid = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)