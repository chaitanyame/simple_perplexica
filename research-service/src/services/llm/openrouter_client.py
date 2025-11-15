"""OpenRouter LLM client with retry logic.

OpenAI-compatible client with exponential backoff retry pattern.
Inspired by Alibaba-NLP/DeepResearch and bytedance/deer-flow.
"""

import asyncio
import logging
import random
from collections.abc import AsyncGenerator
from typing import Any

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from ...core.config import settings
from ...core.circuit_breaker import CircuitBreaker
from .langfuse_tracer import LangfuseTracer
from .schemas import LLMClientError

logger = logging.getLogger(__name__)

# LLM circuit breaker singleton
_llm_circuit_breaker: CircuitBreaker | None = None


def get_llm_circuit_breaker() -> CircuitBreaker:
    """Get or initialize a circuit breaker for LLM operations.

    Reuses Perplexity CB thresholds for simplicity until distinct
    LLM-specific settings are introduced.
    """
    global _llm_circuit_breaker
    if _llm_circuit_breaker is None:
        _llm_circuit_breaker = CircuitBreaker(
            failure_threshold=settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD,
            timeout=float(settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT),
        )
        logger.info(
            "✅ LLM circuit breaker initialized: threshold=%s, timeout=%ss",
            settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD,
            settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT,
        )
    return _llm_circuit_breaker


class OpenRouterClient:
    """OpenRouter LLM client with OpenAI-compatible interface.

    Features:
    - Async chat completion with streaming support
    - Exponential backoff retry (max 10 retries, up to 300s delay)
    - Jitter to avoid thundering herd
    - Token usage tracking
    - Comprehensive error handling

    Retry pattern inspired by Alibaba-NLP/DeepResearch:
        jitter = 1.0 + random.random()
        delay = min(delay * exponential_base, max_delay) * jitter

    Example:
        >>> client = OpenRouterClient()
        >>> response = await client.chat(
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
        >>> print(response["content"])
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str | None = None,  # Model comes from settings, not hardcoded
        max_retries: int = 10,
        max_delay: float = 300.0,
        exponential_base: float = 2.0,
        timeout: float = 60.0,
        tracer: LangfuseTracer | None = None,
    ):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (defaults to settings.OPENROUTER_API_KEY)
            base_url: Base URL for OpenRouter API
            model: Default model to use
            max_retries: Maximum number of retry attempts
            max_delay: Maximum delay between retries (seconds)
            exponential_base: Base for exponential backoff calculation
            timeout: Request timeout (seconds)
            tracer: Optional Langfuse tracer for monitoring

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError(
                "API key is required. Set OPENROUTER_API_KEY or pass api_key parameter."
            )

        self.base_url = base_url
        # Load model from settings if not provided
        self.model = model if model is not None else settings.RESEARCH_LLM_MODEL
        self.max_retries = max_retries
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.timeout = timeout
        self.tracer = tracer

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[dict[str, Any], None]:
        """Execute chat completion.

        Args:
            messages: List of chat messages with 'role' and 'content'
            stream: Whether to stream the response
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters for OpenAI API

        Returns:
            dict with keys: content, role, usage, model, finish_reason (non-streaming)
            AsyncGenerator yielding dicts with: content, finish_reason (streaming)

        Raises:
            LLMClientError: If request fails after all retries
        """
        logger.info(
            f"🤖 LLM REQUEST START: model={self.model}, temp={temperature}, max_tokens={max_tokens}, messages={len(messages)}"
        )

        if stream:
            # Return async generator directly
            return self._chat_stream(messages, temperature, max_tokens, top_p, **kwargs)
        else:
            return await self._chat_non_stream(messages, temperature, max_tokens, top_p, **kwargs)

    async def _chat_non_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
        top_p: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute non-streaming chat completion with retry logic and CB fallback."""

        async def _execute() -> dict[str, Any]:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=False,
                **kwargs,
            )
            # OpenAI SDK returns union type, but we know it's ChatCompletion when stream=False
            result: dict[str, Any] = {
                "content": response.choices[0].message.content or "",  # type: ignore[union-attr]
                "role": response.choices[0].message.role,  # type: ignore[union-attr]
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,  # type: ignore[union-attr]
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,  # type: ignore[union-attr]
                    "total_tokens": response.usage.total_tokens if response.usage else 0,  # type: ignore[union-attr]
                },
                "model": response.model,  # type: ignore[union-attr]
                "finish_reason": response.choices[0].finish_reason,  # type: ignore[union-attr]
            }
            logger.info(
                f"✅ LLM RESPONSE SUCCESS: tokens={result['usage']['total_tokens']} "
                f"(input={result['usage']['prompt_tokens']}, output={result['usage']['completion_tokens']})"
            )

            # Track generation if tracer available
            if self.tracer:
                self.tracer.track_generation(
                    name="chat_completion",
                    model=self.model,
                    input_messages=messages,
                    output=result["content"],
                    prompt_tokens=result["usage"]["prompt_tokens"],
                    completion_tokens=result["usage"]["completion_tokens"],
                    total_tokens=result["usage"]["total_tokens"],
                    metadata={
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p,
                        "finish_reason": result["finish_reason"],
                    },
                )

            return result

        async def _op() -> dict[str, Any]:
            return await self._retry_with_backoff(_execute)

        def _fallback() -> dict[str, Any]:
            # Only return fallback if enabled; otherwise allow exception to propagate
            if not settings.ENABLE_LLM_FALLBACK:
                raise LLMClientError("LLM fallback disabled")
            return {
                "content": "",
                "role": "assistant",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "model": self.model,
                "finish_reason": "fallback",
            }

        breaker = get_llm_circuit_breaker()
        result_dict: dict[str, Any] = await breaker.call_with_retries(
            _op,
            retries=3,
            backoff_base=0.5,
            backoff_factor=2.0,
            fallback=_fallback,
        )
        return result_dict

    async def _chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
        top_p: float,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute streaming chat completion with retry logic and CB fallback."""

        async def _execute() -> Any:
            return await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=True,
                **kwargs,
            )

        async def _empty_stream():
            if False:
                yield  # pragma: no cover

        async def _op() -> Any:
            return await self._retry_with_backoff(_execute)

        def _fallback_stream() -> Any:
            # If fallback disabled, raise so callers get error behavior
            if not settings.ENABLE_LLM_FALLBACK:
                raise LLMClientError("LLM fallback disabled")
            return _empty_stream()

        breaker = get_llm_circuit_breaker()
        stream = await breaker.call_with_retries(
            _op,
            retries=3,
            backoff_base=0.5,
            backoff_factor=2.0,
            fallback=_fallback_stream,
        )

        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                yield {
                    "content": choice.delta.content or "",
                    "role": choice.delta.role if choice.delta.role else None,
                    "finish_reason": choice.finish_reason,
                }

    async def _retry_with_backoff(self, fn: Any) -> Any:
        """Execute function with exponential backoff retry.

        Retry pattern inspired by Alibaba-NLP/DeepResearch:
        - Exponential backoff with jitter
        - Max retries: 10 (configurable)
        - Max delay: 300 seconds
        - Don't retry on 400 Bad Request

        Args:
            fn: Async function to execute

        Returns:
            Result from fn

        Raises:
            LLMClientError: If all retries exhausted or non-retriable error
        """
        delay = 1.0
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                return await fn()

            # IMPORTANT: Handle specific exceptions BEFORE general APIError
            # RateLimitError and APITimeoutError are subclasses of APIError
            except RateLimitError as e:
                last_error = e
                logger.error(
                    f"⚠️ RATE LIMIT ERROR: model={self.model}, attempt={attempt + 1}/{self.max_retries + 1}"
                )
                # After 2 rate limit retries, switch to fallback model from settings
                from src.core.config import settings

                fallback_model = settings.FALLBACK_LLM_MODEL

                if attempt >= 2 and self.model != fallback_model:
                    logger.warning(
                        f"🔄 FALLBACK: Switching model: {self.model} -> {fallback_model}"
                    )
                    original_model = self.model
                    self.model = fallback_model
                    try:
                        result = await fn()
                        logger.info(
                            f"✅ FALLBACK SUCCESS: {fallback_model} worked, restoring {original_model}"
                        )
                        self.model = original_model
                        return result
                    except Exception as fallback_error:
                        self.model = original_model
                        logger.error(
                            f"❌ FALLBACK FAILED: {fallback_model} also failed, error={str(fallback_error)[:200]}"
                        )
                        # Continue with normal retry logic

                if attempt < self.max_retries:
                    logger.warning(
                        f"Rate limit hit on attempt {attempt + 1}/{self.max_retries}, backing off..."
                    )
                    await self._sleep_with_backoff(delay, attempt)
                    delay = min(delay * self.exponential_base, self.max_delay)
                else:
                    raise LLMClientError(
                        f"Rate limit exceeded after {self.max_retries} retries"
                    ) from e

            except APITimeoutError as e:
                last_error = e
                logger.error(
                    f"⏱️ TIMEOUT ERROR: model={self.model}, timeout={self.timeout}s, attempt={attempt + 1}/{self.max_retries + 1}"
                )
                if attempt < self.max_retries:
                    logger.warning(
                        f"🔄 RETRY: attempt {attempt + 1}/{self.max_retries}, backing off..."
                    )
                    await self._sleep_with_backoff(delay, attempt)
                    delay = min(delay * self.exponential_base, self.max_delay)
                else:
                    raise LLMClientError(f"Request timeout after {self.max_retries} retries") from e

            except APIError as e:
                last_error = e
                # Don't retry on 400 Bad Request
                if hasattr(e, "status_code") and e.status_code == 400:
                    logger.error(f"Bad request error: {e}")
                    raise LLMClientError(f"Bad request: {e}") from e

                if attempt < self.max_retries:
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.max_retries} after error: {e}"
                    )
                    await self._sleep_with_backoff(delay, attempt)
                    delay = min(delay * self.exponential_base, self.max_delay)

        # If we get here, all retries exhausted
        raise LLMClientError(
            f"Maximum number of retries ({self.max_retries}) exceeded. Last error: {last_error}"
        ) from last_error

    async def _sleep_with_backoff(self, delay: float, attempt: int) -> None:
        """Sleep with exponential backoff and jitter.

        Jitter formula from DeepResearch:
            jitter = 1.0 + random.random()
            actual_delay = min(delay * exponential_base^attempt, max_delay) * jitter
        """
        jitter = 1.0 + random.random()
        actual_delay = min(delay, self.max_delay) * jitter
        logger.debug(f"Sleeping for {actual_delay:.2f}s (base={delay:.2f}s, jitter={jitter:.2f})")
        await asyncio.sleep(actual_delay)

    def estimate_tokens(self, messages: list[dict[str, str]]) -> int:
        """Estimate token count for messages.

        Simple estimation: ~4 characters per token
        This is a rough estimate, actual tokenization depends on the model.

        Args:
            messages: List of chat messages

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4
