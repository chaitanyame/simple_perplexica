"""Research endpoint for deep research using ResearchAgent.

This module provides the /v1/research endpoint that integrates with ResearchAgent
to perform iterative research with source synthesis.
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

from src.agents.research_agent import ResearchAgent, ResearchAgentDeps
from src.api.v1.schemas import (
    CitationResponse,
    ResearchPlanResponse,
    ResearchRequest,
    ResearchResponse,
)
from src.core.config import settings
from src.database.models import ResearchSession
from src.database.session import get_db
from src.services.embedding.embedding_service import EmbeddingService
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient

if TYPE_CHECKING:
    from src.agents.research_agent import ResearchOutput

router = APIRouter(prefix="/v1", tags=["research"])


async def create_research_agent(
    db: AsyncSession,
    model: str | None = None,
    max_iterations: int = 3,
    timeout: float = 300.0,
) -> ResearchAgent:
    """Create and configure a ResearchAgent instance.

    Args:
        db: Database session
        model: Optional LLM model override
        max_iterations: Maximum research iterations
        timeout: Operation timeout in seconds

    Returns:
        Configured ResearchAgent instance
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

    # Initialize embedding service
    embedding_service = EmbeddingService()

    # Initialize SearxNG client
    searxng_client = httpx.AsyncClient(
        base_url=settings.SEARXNG_BASE_URL,
        timeout=timeout,
    )

    # Create agent dependencies
    deps = ResearchAgentDeps(
        llm_client=llm_client,
        tracer=tracer,
        db=db,
        embedding_service=embedding_service,
        searxng_client=searxng_client,
        serperdev_api_key=settings.SERPER_API_KEY or "",
        max_iterations=max_iterations,
        timeout=timeout,
    )

    return ResearchAgent(deps=deps)


async def store_research_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    query: str,
    result: dict,
) -> None:
    """Store research session in database."""
    session = ResearchSession(
        id=session_id,
        query=query,
        mode="research",
        result=result,
        status="completed",
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()


def convert_research_output_to_response(
    session_id: uuid.UUID,
    query: str,
    output: ResearchOutput,
    model_used: str,
    trace_url: str | None,
) -> ResearchResponse:
    """Convert ResearchOutput to API response."""
    return ResearchResponse(
        session_id=session_id,
        query=query,
        research_plan=ResearchPlanResponse(
            queries=[q.query for q in output.research_plan.queries],
            focus_areas=output.research_plan.focus_areas,
            estimated_sources=output.research_plan.estimated_sources,
        ),
        findings=output.findings,
        synthesis=output.synthesis,
        citations=[
            CitationResponse(
                id=idx + 1,
                title=cite.title,
                url=cite.url,
                snippet=cite.snippet,
                relevance=cite.relevance,
                used_in_synthesis=cite.used_in_synthesis,
            )
            for idx, cite in enumerate(output.citations)
        ],
        execution_time=output.execution_time,
        confidence=output.confidence,
        model_used=model_used,
        trace_url=trace_url,
        created_at=datetime.utcnow(),
    )


@router.post("/research", response_model=ResearchResponse)
async def research(
    request: ResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchResponse:
    """Execute deep research query.

    Args:
        request: Research request with query and parameters
        db: Database session

    Returns:
        Research response with findings and synthesis
    """
    session_id = uuid.uuid4()

    try:
        # Create ResearchAgent
        agent = await create_research_agent(
            db=db,
            model=request.model,
            max_iterations=request.max_iterations,
            timeout=float(request.timeout),
        )

        # Execute research with timeout
        try:
            output = await asyncio.wait_for(
                agent.run(request.query),
                timeout=float(request.timeout),
            )
        except TimeoutError:
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "research_timeout",
                    "message": f"Research exceeded timeout of {request.timeout}s",
                },
            )

        # Convert to API response
        response = convert_research_output_to_response(
            session_id=session_id,
            query=request.query,
            output=output,
            model_used=request.model or settings.LLM_MODEL,
            trace_url=None,  # TODO: Get from tracer
        )

        # Store session in database
        await store_research_session(
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
                "error": "research_execution_failed",
                "message": f"Research execution failed: {str(e)}",
            },
        )
