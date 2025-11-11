"""API request/response schemas for research service endpoints.

This module defines Pydantic models for API contracts, ensuring type safety
and validation for all endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Search Endpoint Schemas
# ============================================================================


class SearchRequest(BaseModel):
    """Request model for /v1/search endpoint.

    Attributes:
        query: Search query (1-1000 chars)
        max_sources: Maximum sources to retrieve (5-50, default 20)
        timeout: Timeout in seconds (10-300, default 60)
        model: LLM model to use (default from config)
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query",
        examples=["What is Pydantic AI?"],
    )
    max_sources: int = Field(
        20,
        ge=5,
        le=50,
        description="Maximum number of sources to retrieve",
    )
    timeout: int = Field(
        60,
        ge=10,
        le=300,
        description="Timeout in seconds",
    )
    model: str | None = Field(
        None,
        description="LLM model to use (e.g., 'anthropic/claude-3.5-sonnet')",
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace-only")
        return v.strip()


class SearchSourceResponse(BaseModel):
    """Individual search source in response.

    Attributes:
        title: Source title
        url: Source URL
        snippet: Content excerpt
        relevance: Relevance score (0-1)
        source_type: Source category
    """

    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    snippet: str = Field(..., description="Content excerpt")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source_type: Literal["web", "academic", "news"] = Field(..., description="Source category")


class SubQueryResponse(BaseModel):
    """Sub-query generated during decomposition.

    Attributes:
        query: The sub-query text
        intent: Query intent classification
        priority: Execution priority
    """

    query: str = Field(..., description="Sub-query text")
    intent: Literal["definition", "factual", "opinion"] = Field(..., description="Query intent")
    priority: int = Field(..., ge=1, le=10, description="Execution priority")


class SearchResponse(BaseModel):
    """Response model for /v1/search endpoint.

    Attributes:
        session_id: Unique session identifier
        query: Original search query
        answer: AI-generated answer based on sources
        sub_queries: Decomposed sub-queries
        sources: Retrieved sources
        execution_time: Total execution time (seconds)
        confidence: Result confidence (0-1)
        model_used: LLM model used
        trace_url: Langfuse trace URL (if available)
        created_at: Response timestamp
    """

    session_id: uuid.UUID = Field(..., description="Session identifier")
    query: str = Field(..., description="Original search query")
    answer: str = Field(..., description="AI-generated answer based on sources")
    sub_queries: list[SubQueryResponse] = Field(..., description="Decomposed sub-queries")
    sources: list[SearchSourceResponse] = Field(..., description="Retrieved sources")
    execution_time: float = Field(..., ge=0.0, description="Execution time (seconds)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Result confidence")
    model_used: str = Field(..., description="LLM model used")
    trace_url: str | None = Field(None, description="Langfuse trace URL")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# ============================================================================
# Research Endpoint Schemas
# ============================================================================


class ResearchRequest(BaseModel):
    """Request model for /v1/research endpoint.

    Attributes:
        query: Research question (1-1000 chars)
        max_iterations: Maximum research iterations (1-10, default 5)
        timeout: Timeout in seconds (60-600, default 300)
        model: LLM model to use (default from config)
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Research question",
        examples=["What are AI agents and how do they work?"],
    )
    max_iterations: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum research iterations",
    )
    timeout: int = Field(
        300,
        ge=60,
        le=600,
        description="Timeout in seconds",
    )
    model: str | None = Field(
        None,
        description="LLM model to use (e.g., 'anthropic/claude-3.5-sonnet')",
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace-only")
        return v.strip()


class ResearchStepResponse(BaseModel):
    """Individual research step in plan.

    Attributes:
        step_number: Step number (1-based)
        description: Step description
        search_query: Query for search agent
        expected_outcome: Expected result
        depends_on: Prerequisite step numbers
    """

    step_number: int = Field(..., ge=1, description="Step number")
    description: str = Field(..., description="Step description")
    search_query: str = Field(..., description="Search query")
    expected_outcome: str = Field(..., description="Expected result")
    depends_on: list[int] = Field(default_factory=list, description="Prerequisite steps")


class ResearchPlanResponse(BaseModel):
    """Research plan in response.

    Attributes:
        original_query: User's original query
        steps: Research steps
        estimated_time: Time estimate (seconds)
        complexity: Difficulty classification
    """

    original_query: str = Field(..., description="Original query")
    steps: list[ResearchStepResponse] = Field(..., description="Research steps")
    estimated_time: float = Field(..., ge=0.0, description="Time estimate (seconds)")
    complexity: Literal["simple", "moderate", "complex"] = Field(
        ..., description="Difficulty level"
    )


class CitationResponse(BaseModel):
    """Citation in research output.

    Attributes:
        source_id: Unique source identifier
        title: Source title
        url: Source URL
        excerpt: Relevant excerpt
        relevance: Relevance score (0-1)
    """

    source_id: str = Field(..., description="Source identifier")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    excerpt: str = Field(..., description="Relevant excerpt")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


class ResearchResponse(BaseModel):
    """Response model for /v1/research endpoint.

    Attributes:
        session_id: Unique session identifier
        query: Original research question
        plan: Execution plan
        findings: Synthesized research findings
        citations: Source citations
        confidence: Result confidence (0-1)
        execution_time: Total execution time (seconds)
        execution_steps: Detailed execution log
        model_used: LLM model used
        trace_url: Langfuse trace URL (if available)
        created_at: Response timestamp
    """

    session_id: uuid.UUID = Field(..., description="Session identifier")
    query: str = Field(..., description="Original research question")
    plan: ResearchPlanResponse = Field(..., description="Execution plan")
    findings: str = Field(..., min_length=100, description="Synthesized findings")
    citations: list[CitationResponse] = Field(..., min_length=3, description="Source citations")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Result confidence (0-1)")
    execution_time: float = Field(..., ge=0.0, description="Execution time (seconds)")
    execution_steps: list[dict[str, Any]] = Field(..., description="Execution log details")
    model_used: str = Field(..., description="LLM model used")
    trace_url: str | None = Field(None, description="Langfuse trace URL")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# ============================================================================
# Session Endpoint Schemas
# ============================================================================


class SessionResponse(BaseModel):
    """Response model for /v1/sessions/{id} endpoint.

    Attributes:
        session_id: Session identifier
        query: Original query
        mode: Search or research mode
        result: Session result (search or research)
        created_at: Session creation timestamp
        completed_at: Session completion timestamp
    """

    session_id: uuid.UUID = Field(..., description="Session identifier")
    query: str = Field(..., description="Original query")
    mode: Literal["search", "research"] = Field(..., description="Session mode")
    result: SearchResponse | ResearchResponse | None = Field(None, description="Session result")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")


# ============================================================================
# Error Response Schemas
# ============================================================================


class ErrorDetail(BaseModel):
    """Detailed error information.

    Attributes:
        field: Field that caused error (if applicable)
        message: Error message
        type: Error type
    """

    field: str | None = Field(None, description="Field with error")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response format.

    Attributes:
        error: Error type/code
        message: Human-readable error message
        details: Detailed error information
        trace_id: Request trace ID (for debugging)
    """

    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Error message")
    details: list[ErrorDetail] | None = Field(None, description="Error details")
    trace_id: str | None = Field(None, description="Request trace ID")


# ============================================================================
# Health Check Schemas
# ============================================================================


class HealthResponse(BaseModel):
    """Response model for /health endpoint.

    Attributes:
        status: Service status
        version: Service version
        timestamp: Check timestamp
    """

    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
