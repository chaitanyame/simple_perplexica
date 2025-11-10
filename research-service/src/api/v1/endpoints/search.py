"""Search endpoint for fast web search using SearchAgent.

This module provides the /v1/search endpoint that integrates with SearchAgent
to perform query decomposition, parallel search, and result aggregation.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.search_agent import SearchAgent, SearchAgentDeps
from src.api.v1.schemas import (
    SearchRequest,
    SearchResponse,
    SearchSourceResponse,
    SubQueryResponse,
)
from src.core.config import settings
from src.database.models import ResearchSession
from src.database.session import get_db
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient

if TYPE_CHECKING:
    from src.agents.search_agent import SearchOutput

router = APIRouter(prefix="/v1", tags=["search"])


async def create_search_agent(
    db: AsyncSession,
    model: str | None = None,
    max_sources: int = 20,
    timeout: float = 60.0,
) -> SearchAgent:
    """Create SearchAgent with dependencies.

    Args:
        db: Database session
        model: Optional LLM model override
        max_sources: Maximum sources to retrieve
        timeout: Search timeout in seconds

    Returns:
        Configured SearchAgent instance
    """
    # Initialize LLM client
    llm_client = OpenRouterClient(
        api_key=settings.OPENROUTER_API_KEY,
        model=model or settings.LLM_MODEL,
    )

    # Initialize tracer
    tracer = LangfuseTracer(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
    )

    # Initialize SearxNG client
    searxng_client = httpx.AsyncClient(
        base_url=settings.SEARXNG_BASE_URL,
        timeout=timeout,
    )

    # Create agent dependencies
    deps = SearchAgentDeps(
        llm_client=llm_client,
        tracer=tracer,
        db=db,
        searxng_client=searxng_client,
        serperdev_api_key=settings.SERPER_API_KEY or "",
        max_sources=max_sources,
        timeout=timeout,
    )

    return SearchAgent(deps=deps)


async def store_search_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    query: str,
    result: dict,
) -> None:
    """Store search session in database.

    Args:
        db: Database session
        session_id: Session identifier
        query: Search query
        result: Search result data
    """
    session = ResearchSession(
        id=session_id,
        query=query,
        mode="search",
        result=result,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )

    db.add(session)
    await db.commit()


def convert_search_output_to_response(
    session_id: uuid.UUID,
    query: str,
    output: SearchOutput,
    model_used: str,
    trace_url: str | None = None,
) -> SearchResponse:
    """Convert SearchOutput to SearchResponse.

    Args:
        session_id: Session identifier
        query: Original query
        output: SearchAgent output
        model_used: LLM model used
        trace_url: Langfuse trace URL

    Returns:
        SearchResponse model
    """
    return SearchResponse(
        session_id=session_id,
        query=query,
        sub_queries=[
            SubQueryResponse(
                query=sq.query,
                intent=sq.intent,
                priority=sq.priority,
            )
            for sq in output.sub_queries
        ],
        sources=[
            SearchSourceResponse(
                title=src.title,
                url=src.url,
                snippet=src.snippet,
                relevance=src.relevance,
                source_type=src.source_type,
            )
            for src in output.sources
        ],
        execution_time=output.execution_time,
        confidence=output.confidence,
        model_used=model_used,
        trace_url=trace_url,
        created_at=datetime.utcnow(),
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute fast search",
    description="Perform fast web search with query decomposition and parallel execution",
    responses={
        200: {"description": "Search completed successfully"},
        422: {"description": "Validation error"},
        504: {"description": "Search timeout"},
        500: {"description": "Internal server error"},
    },
)
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Execute search query using SearchAgent.

    Args:
        request: Search request with query and parameters
        db: Database session

    Returns:
        SearchResponse with results

    Raises:
        HTTPException: On timeout or execution error
    """
    session_id = uuid.uuid4()

    try:
        # Create SearchAgent
        agent = await create_search_agent(
            db=db,
            model=request.model,
            max_sources=request.max_sources,
            timeout=float(request.timeout),
        )

        # Execute search with timeout
        try:
            output = await asyncio.wait_for(
                agent.run(request.query),
                timeout=float(request.timeout),
            )
        except TimeoutError:
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "search_timeout",
                    "message": f"Search exceeded timeout of {request.timeout}s",
                },
            )

        # Convert to response
        response = convert_search_output_to_response(
            session_id=session_id,
            query=request.query,
            output=output,
            model_used=request.model or settings.LLM_MODEL,
            trace_url=None,  # TODO: Get from tracer
        )

        # Store session in database
        await store_search_session(
            db=db,
            session_id=session_id,
            query=request.query,
            result=response.model_dump(mode="json"),
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Handle unexpected errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "search_execution_failed",
                "message": f"Search execution failed: {str(e)}",
            },
        )
