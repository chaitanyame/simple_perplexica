"""Prompt strategy helpers for dynamic vs static prompt selection.

This module provides utilities to determine which prompt strategy to use
based on user preference, API parameters, and configuration.
"""
from __future__ import annotations

from typing import Literal

from ..core.config import settings


PromptStrategy = Literal["static", "dynamic", "auto"]


def resolve_prompt_strategy(
    strategy: PromptStrategy | None = None,
) -> Literal["static", "dynamic"]:
    """Resolve prompt strategy to concrete choice.
    
    Priority:
    1. Explicit user choice ("static" or "dynamic")
    2. "auto" → uses ENABLE_DYNAMIC_PROMPTS from config
    3. None → uses ENABLE_DYNAMIC_PROMPTS from config (default)
    
    Args:
        strategy: User-selected strategy or None
        
    Returns:
        "static" or "dynamic" (never "auto")
        
    Example:
        >>> resolve_prompt_strategy("static")
        "static"
        >>> resolve_prompt_strategy("auto")  # Uses config
        "dynamic"  # if ENABLE_DYNAMIC_PROMPTS=True
    """
    if strategy == "static":
        return "static"
    elif strategy == "dynamic":
        return "dynamic"
    else:  # "auto" or None
        # Use configuration default
        return "dynamic" if settings.ENABLE_DYNAMIC_PROMPTS else "static"


def should_use_dynamic_prompts(strategy: PromptStrategy | None = None) -> bool:
    """Check if dynamic prompts should be used.
    
    Args:
        strategy: User-selected strategy or None
        
    Returns:
        True if dynamic prompts should be used
        
    Example:
        >>> should_use_dynamic_prompts("dynamic")
        True
        >>> should_use_dynamic_prompts("static")
        False
    """
    return resolve_prompt_strategy(strategy) == "dynamic"


def get_prompt_strategy_description(strategy: PromptStrategy) -> str:
    """Get human-readable description of prompt strategy.
    
    Args:
        strategy: Prompt strategy
        
    Returns:
        Description string
    """
    descriptions = {
        "static": "Using fixed system prompts (fast, predictable)",
        "dynamic": "Using query-aware dynamic prompts (context-optimized)",
        "auto": f"Auto-selecting based on config (currently: {'dynamic' if settings.ENABLE_DYNAMIC_PROMPTS else 'static'})"
    }
    return descriptions.get(strategy, "Unknown strategy")


def get_planning_prompt(
    query: str,
    strategy: PromptStrategy | None = "auto",
    mode: str = "balanced"
) -> str:
    """Get system prompt for research planning.
    
    Args:
        query: User query for context
        strategy: Prompt strategy selection
        mode: Search mode (speed/balanced/deep)
        
    Returns:
        System prompt string
    """
    if should_use_dynamic_prompts(strategy):
        # Dynamic prompt - query-aware
        from .system_prompt_generator import SystemPromptGenerator
        return SystemPromptGenerator.generate(query=query, mode=mode)
    else:
        # Static prompt - original ResearchAgent prompt
        return """You are a research planning expert. Break down complex queries into structured research plans.

For each step:
- Assign a sequential step_number
- Provide clear description and search_query
- Define expected_outcome
- Specify dependencies (which steps must complete first)

Complexity levels:
- simple: 1-2 steps, single topic
- medium: 2-4 steps, related topics
- complex: 4+ steps, multiple topics with dependencies"""


def get_synthesis_prompt(
    query: str,
    strategy: PromptStrategy | None = "auto",
    mode: str = "balanced"
) -> str:
    """Get system prompt for findings synthesis.
    
    Args:
        query: User query for context
        strategy: Prompt strategy selection
        mode: Search mode (speed/balanced/deep)
        
    Returns:
        System prompt string
    """
    if should_use_dynamic_prompts(strategy):
        # Dynamic prompt - query-aware
        from .system_prompt_generator import SystemPromptGenerator
        return SystemPromptGenerator.generate(query=query, mode=mode)
    else:
        # Static prompt - original ResearchAgent prompt
        return """You are a research synthesis expert. Your job is to:

1. Analyze all provided sources and findings
2. Synthesize a comprehensive answer to the query
3. Support ALL claims with inline citations [Source N]
4. Maintain accuracy and avoid speculation
5. Structure the response clearly

CRITICAL: Every factual statement must have a citation. Use [Source N] format referring to the numbered sources."""


def get_search_prompt(
    query: str,
    strategy: PromptStrategy | None = "auto",
    mode: str = "balanced"
) -> str:
    """Get system prompt for search operations.
    
    Args:
        query: User query for context
        strategy: Prompt strategy selection
        mode: Search mode (speed/balanced/deep)
        
    Returns:
        System prompt string
    """
    if should_use_dynamic_prompts(strategy):
        # Dynamic prompt - query-aware
        from .system_prompt_generator import SystemPromptGenerator
        return SystemPromptGenerator.generate(query=query, mode=mode)
    else:
        # Static prompt - simple search assistant
        return """You are a helpful search assistant. Provide accurate, concise answers based on the search results provided. Always cite your sources using [Source N] format."""
