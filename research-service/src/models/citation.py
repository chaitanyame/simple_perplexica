"""Shared Citation model used across agents and utilities.

This module provides the Citation model to avoid circular imports
between research_agent.py and claim_grounder.py.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation from research source."""

    source_id: str = Field(..., description="Unique source identifier")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    excerpt: str = Field(..., description="Relevant excerpt from source")
    relevance: float = Field(..., description="Relevance score (0.0-1.0)")
    # Phase 3: Citation quality enhancement
    authority_level: str = Field(
        default="secondary",
        description="Citation authority: primary (official), secondary (reputable), tertiary (general)"
    )
    freshness_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Freshness score (0.0-1.0), higher for recent sources"
    )
    is_direct_quote: bool = Field(
        default=False,
        description="Whether citation is direct quote vs paraphrase"
    )
