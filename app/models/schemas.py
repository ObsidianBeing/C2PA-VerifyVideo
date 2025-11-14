from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from datetime import datetime
import re

class VideoSignRequest(BaseModel):
    """Request model for video signing"""
    organization: str = Field(
        ..., 
        min_length=1, 
        max_length=200, 
        description="Organization name",
        example="Acme AI Corporation"
    )
    ai_tool: str = Field(
        ..., 
        min_length=1, 
        max_length=200, 
        description="AI tool/model used to generate the video",
        example="Runway Gen-3"
    )
    title: Optional[str] = Field(
        None, 
        max_length=300, 
        description="Video title",
        example="AI Generated Landscape Video"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Video description",
        example="A beautiful AI-generated landscape scene"
    )
    
    @validator('organization', 'ai_tool', 'title', 'description')
    def sanitize_strings(cls, v):
        """Remove potentially dangerous characters"""
        if v:
            return re.sub(r'[<>"\'&]', '', v)
        return v

class SigningResponse(BaseModel):
    """Response model for successful signing"""
    status: Literal["ok", "failed"] = Field(
        ..., 
        description="Status of the signing operation"
    )
    message: str = Field(
        ..., 
        description="Human-readable message"
    )
    job_id: str = Field(
        ..., 
        description="Unique job identifier"
    )
    links: dict = Field(
        ..., 
        description="Download links for signed video and manifest"
    )
    metadata: Optional[dict] = Field(
        None, 
        description="Additional metadata about the operation"
    )

class ErrorResponse(BaseModel):
    """Error response model"""
    status: Literal["error"]
    message: str
    detail: Optional[str] = None