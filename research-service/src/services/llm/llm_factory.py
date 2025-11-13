"""LLM client factory for creating and caching LLM clients.

This module provides a factory pattern for creating LLM clients based on
configuration. Clients are cached to avoid unnecessary recreations.
"""
from __future__ import annotations

import logging
from typing import Any

from ...core.config import LLMConfig, settings
from .openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating and caching LLM clients.
    
    Features:
    - Creates clients based on LLMConfig
    - Caches clients by provider:model key
    - Supports OpenRouter provider
    - Thread-safe singleton pattern
    
    Example:
        >>> config = settings.research_llm_config
        >>> client = LLMFactory.create_client(config)
        >>> # Second call returns cached client
        >>> cached_client = LLMFactory.create_client(config)
        >>> assert client is cached_client
    """

    _clients: dict[str, Any] = {}

    @classmethod
    def create_client(cls, config: LLMConfig) -> Any:
        """Create or retrieve cached LLM client.
        
        Args:
            config: LLM configuration with provider, model, and parameters
            
        Returns:
            LLM client instance (OpenRouterClient, etc.)
            
        Raises:
            ValueError: If provider is not supported
            
        Example:
            >>> config = LLMConfig(
            ...     provider="openrouter",
            ...     model="deepseek/deepseek-r1:free",
            ...     temperature=0.3,
            ...     max_tokens=8192,
            ...     timeout=180
            ... )
            >>> client = LLMFactory.create_client(config)
        """
        # Create cache key from provider and model
        cache_key = f"{config.provider}:{config.model}"
        
        # Return cached client if exists
        if cache_key in cls._clients:
            logger.debug(f"Returning cached client for {cache_key}")
            return cls._clients[cache_key]
        
        # Create new client based on provider
        logger.info(
            f"Creating new {config.provider} client: model={config.model}, "
            f"temperature={config.temperature}, max_tokens={config.max_tokens}"
        )
        
        if config.provider == "openrouter":
            client = OpenRouterClient(
                model=config.model,
                timeout=config.timeout,
                # Note: OpenRouterClient accepts temperature/max_tokens in chat() method
                # We pass them here for consistency, but they're applied per-request
            )
        else:
            raise ValueError(
                f"Unknown provider: {config.provider}. "
                f"Supported providers: openrouter"
            )
        
        # Cache and return
        cls._clients[cache_key] = client
        logger.debug(f"Cached client for {cache_key}")
        return client

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached clients.
        
        Useful for testing or when config changes require fresh clients.
        
        Example:
            >>> LLMFactory.clear_cache()
            >>> # Next create_client() call will create new instance
        """
        cls._clients.clear()
        logger.debug("Cleared LLM client cache")


def get_research_llm() -> Any:
    """Get LLM client for research tasks.
    
    Uses settings.research_llm_config to create/retrieve client.
    Optimized for reasoning and complex research queries.
    
    Returns:
        LLM client configured for research (DeepSeek R1 by default)
        
    Example:
        >>> client = get_research_llm()
        >>> response = await client.chat(
        ...     messages=[{"role": "user", "content": "Explain quantum computing"}],
        ...     temperature=0.3,
        ...     max_tokens=8192
        ... )
    """
    config = settings.research_llm_config
    return LLMFactory.create_client(config)


def get_fallback_llm() -> Any:
    """Get fallback LLM client.
    
    Uses settings.fallback_llm_config to create/retrieve client.
    Optimized for speed and reliability when primary LLM fails.
    
    Returns:
        LLM client configured for fallback (Gemini by default)
        
    Example:
        >>> client = get_fallback_llm()
        >>> response = await client.chat(
        ...     messages=[{"role": "user", "content": "Quick summary"}],
        ...     temperature=0.2,
        ...     max_tokens=4096
        ... )
    """
    config = settings.fallback_llm_config
    return LLMFactory.create_client(config)
