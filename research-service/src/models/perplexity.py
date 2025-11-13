"""Perplexity API response models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PerplexityUsage(BaseModel):
    """Token usage for Perplexity request."""
    prompt_tokens: int = Field(default=0, description="Number of prompt tokens used")
    completion_tokens: int = Field(default=0, description="Number of completion tokens used")
    total_tokens: int = Field(default=0, description="Total tokens used")


class PerplexityResponse(BaseModel):
    """Parsed Perplexity API response.

    Perplexity returns a complete answer with citations already formatted.
    We map this directly to our Citation model without additional processing.
    """
    content: str = Field(..., description="Complete answer from Perplexity")
    citations: List[str] = Field(default_factory=list, description="Citation URLs from Perplexity")
    model: str = Field(..., description="Model used")
    usage: PerplexityUsage = Field(default_factory=PerplexityUsage)


class PerplexitySearchResult(BaseModel):
    """Complete search result from Perplexity (ready to consume).

    Since Perplexity returns a complete answer with citations,
    this result needs no additional LLM processing.
    """
    answer: str = Field(..., description="Complete, ready-to-consume answer from Perplexity")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Citation objects")
    source: str = Field(default="perplexity", description="Source identifier")
    is_final: bool = Field(default=True, description="No further LLM processing needed")
    usage: Dict[str, Any] = Field(default_factory=dict, description="Token usage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
