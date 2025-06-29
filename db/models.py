# karya/db/models.py

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.sql import func


Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    workflow_name = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    context = Column(MutableDict.as_mutable(JSON), nullable=True)
    steps = Column(MutableList.as_mutable(JSON), nullable=True)
    current_step_id = Column(
        String, nullable=True
    )  # 🔥 Needed to track which step is running
    step_retry_counts = Column(
        MutableDict.as_mutable(JSON), nullable=True
    )  # 🔥 Needed for max_retries tracking
    resume_at = Column(DateTime, nullable=True)  # ⏰ For resuming wait steps
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Action(Base):
    __tablename__ = "actions"

    name = Column(String(100), primary_key=True)
    type = Column(String(20), nullable=False)  # 'http' or 'lambda'
    config = Column(MutableDict.as_mutable(JSON), nullable=True)
