from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()


def gen_id():
    return str(uuid.uuid4())


def now_utc():
    return datetime.now(timezone.utc)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    role_applied = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="new", index=True)  # new/reviewed/hired/rejected/archived
    skills = Column(JSON, default=list)          # stored as JSON array
    internal_notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    scores = relationship("Score", back_populates="candidate", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"

    id = Column(String, primary_key=True, default=gen_id)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    score = Column(Integer, nullable=False)   # 1–5
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    candidate = relationship("Candidate", back_populates="scores")
    reviewer = relationship("User", back_populates="scores")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="reviewer")  # reviewer | admin
    created_at = Column(DateTime(timezone=True), default=now_utc)

    scores = relationship("Score", back_populates="reviewer")
