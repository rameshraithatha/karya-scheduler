# karya/db/schemas.py

from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Literal


class JobRequest(BaseModel):
    workflow_name: str
    parameters: Dict[str, Any]
    steps: List[Dict[str, Any]]


class JobStatus(BaseModel):
    job_id: str
    status: str
    context: Optional[Dict[str, Any]] = None


class ActionSchema(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]


class ActionUpdateSchema(BaseModel):
    type: str
    config: Dict[str, Any]
