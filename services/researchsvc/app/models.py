from pydantic import BaseModel, Field
from typing import Optional


class GenerateContentRequest(BaseModel):
    """Request model for content generation"""

    topic: str = Field(
        ..., description="The topic to generate content about", min_length=3
    )
    temperature: Optional[float] = Field(
        default=0.7, ge=0.0, le=1.0, description="LLM temperature for creativity"
    )


class GenerateContentResponse(BaseModel):
    """Response model for content generation"""

    topic: str
    content: str
    raw_output: str
    status: str = "success"


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    version: str
