from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    password = Column(String(50))


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True)
    filename = Column(String(100))
    result = Column(String(50))
    confidence = Column(Float)
    time = Column(DateTime, default=datetime.now)