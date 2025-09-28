from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class JobBase(BaseModel):
    job_type: str
    parameters: Dict[str, Any]

class JobCreate(JobBase):
    user_id: int

class JobResponse(JobBase):
    id: int
    user_id: int
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ExternalDataRequest(BaseModel):
    data_sources: List[str] = Field(..., min_items=1, description="List of external API URLs or identifiers")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional filters for data processing")

class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    message: Optional[str] = None