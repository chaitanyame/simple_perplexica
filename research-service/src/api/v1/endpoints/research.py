"""Research endpoint for deep research using ResearchAgent.

This module provides the /v1/research endpoint that integrates with ResearchAgent
to perform iterative research with source synthesis.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.research_agent import ResearchAgent, ResearchAgentDeps
from src.agents.search_agent import SearchAgent, SearchAgentDeps
from src.api.v1.schemas import (
    CitationResponse,
    ResearchPlanResponse,
    ResearchRequest,
    ResearchResponse,
    ResearchStepResponse,
)
from src.core.config import settings
from src.database.models import ResearchSession
from src.database.session import get_db
from src.rag.vector_store_repository import VectorStoreRepository
from src.services.crawl.crawl4ai_client import Crawl4AIClient
from src.services.document.dockling_processor import DocklingProcessor
from src.services.embedding.embedding_service import EmbeddingService
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.search.searxng_client import SearxNGClient
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
    # Initialize tracer first (needed by LLM client)
    tracer = LangfuseTracer(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL,
    )

    # Initialize LLM client with DeepSeek R1 for research
    llm_client = OpenRouterClient(
        api_key=settings.OPENROUTER_API_KEY,
        model=model or settings.RESEARCH_LLM_MODEL,  # Use DeepSeek R1 for research
        tracer=tracer,
    )

    # Initialize SearxNG client
    searxng_client = SearxNGClient(
        base_url=settings.SEARXNG_BASE_URL,
        timeout=timeout,
    )

    # Initialize crawling client
    crawl_client = Crawl4AIClient()

    # Initialize document processor
    document_processor = DocklingProcessor()

    # Initialize embedding service
    embedding_service = EmbeddingService(
        model_name="all-MiniLM-L6-v2",
        reranker_model_name=settings.RERANKER_MODEL,
        device="cpu",
    )

    # Initialize vector store
    vector_store = VectorStoreRepository(
        db=db,
        dimension=384,  # all-MiniLM-L6-v2 embedding dimension
    )

    # Create SearchAgent (used by ResearchAgent)
    search_deps = SearchAgentDeps(
        llm_client=llm_client,
        tracer=tracer,
        db=db,
        searxng_client=searxng_client,
        serperdev_api_key=settings.SERPER_API_KEY or "",
        crawl_client=crawl_client,
        document_processor=document_processor,
        embedding_service=embedding_service,
        max_sources=20,  # Research mode uses more sources
        timeout=timeout,
        min_sources=5,
        min_confidence=0.4,
        enable_crawling=True,
        max_crawl_urls=5,
        enable_reranking=settings.ENABLE_RERANKING,
        rerank_weight=settings.RERANK_WEIGHT,
    )
    search_agent = SearchAgent(deps=search_deps)

    # Create ResearchAgent dependencies
    deps = ResearchAgentDeps(
        llm_client=llm_client,
        tracer=tracer,
        db=db,
        search_agent=search_agent,
        vector_store=vector_store,
        embedding_service=embedding_service,
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


def normalize_complexity(complexity: str) -> str:
    """Normalize complexity value to match schema requirements.

    Args:
        complexity: Raw complexity value from LLM (e.g., 'medium', 'moderate', 'simple')

    Returns:
        Normalized complexity: 'simple', 'moderate', or 'complex'
    """
    complexity_lower = complexity.lower().strip()

    # Map variations to valid values
    complexity_map = {
        "easy": "simple",
        "basic": "simple",
        "simple": "simple",
        "medium": "moderate",
        "moderate": "moderate",
        "average": "moderate",
        "hard": "complex",
        "difficult": "complex",
        "complex": "complex",
        "advanced": "complex",
    }

    return complexity_map.get(complexity_lower, "moderate")  # Default to moderate


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
        plan=ResearchPlanResponse(
            original_query=output.plan.original_query,
            steps=[
                ResearchStepResponse(
                    step_number=step.step_number,
                    description=step.description,
                    search_query=step.search_query,
                    expected_outcome=step.expected_outcome,
                    depends_on=step.depends_on,
                )
                for step in output.plan.steps
            ],
            estimated_time=output.plan.estimated_time,
            complexity=normalize_complexity(output.plan.complexity),
        ),
        findings=output.findings,
        citations=[
            CitationResponse(
                source_id=cite.source_id,
                title=cite.title,
                url=cite.url,
                excerpt=cite.excerpt,
                relevance=cite.relevance,
            )
            for cite in output.citations
        ],
        execution_time=output.plan.estimated_time,  # Use plan estimate
        execution_steps=[],  # TODO: Add execution step tracking
        confidence=output.confidence,
        model_used=model_used,
        trace_url=trace_url,
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
        # Get mode configuration
        from src.core.search_modes import get_mode_from_string

        search_mode = get_mode_from_string(request.mode)
        config = search_mode.config

        # Use request parameter or mode default for timeout
        timeout = request.timeout if request.timeout is not None else config.timeout

        # Ensure timeout is a valid number (default to 300s if still None)
        if timeout is None:
            timeout = 300.0
        timeout = float(timeout)

        # Create ResearchAgent
        agent = await create_research_agent(
            db=db,
            model=request.model,
            max_iterations=request.max_iterations,
            timeout=timeout,
        )

        # Execute research with timeout, mode, and prompt strategy, traced in Langfuse
        trace = None
        try:
            with agent.deps.tracer.trace_context(
                name="research",
                session_id=str(session_id),
                metadata={
                    "mode": request.mode or "balanced",
                    "max_iterations": request.max_iterations,
                    "timeout": float(timeout),
                },
            ) as _trace:
                trace = _trace
                output = await asyncio.wait_for(
                    agent.run(
                        request.query,
                        mode=search_mode,
                        prompt_strategy=request.prompt_strategy,
                    ),
                    timeout=timeout,
                )
        except TimeoutError:
            try:
                agent.deps.tracer.track_error(TimeoutError(f"research timeout {timeout}s"))
                agent.deps.tracer.flush()
            except Exception:
                pass
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "research_timeout",
                    "message": f"Research exceeded timeout of {timeout}s",
                    "trace_id": agent.deps.tracer.get_trace_id(trace)
                    if agent.deps.tracer
                    else None,
                },
            )

        # Convert to API response
        response = convert_research_output_to_response(
            session_id=session_id,
            query=request.query,
            output=output,
            model_used=request.model or settings.LLM_MODEL,
            trace_url=(agent.deps.tracer.get_trace_url(trace) if agent.deps.tracer else None),
        )

        # Store session in database
        await store_research_session(
            db=db,
            session_id=session_id,
            query=request.query,
            result=response.model_dump(mode="json"),
        )

        # Flush traces to Langfuse before returning
        if agent.deps.tracer:
            agent.deps.tracer.flush()

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Handle unexpected errors and flush any pending traces
        try:
            if "agent" in locals() and agent.deps.tracer:
                agent.deps.tracer.track_error(e)
                agent.deps.tracer.flush()
        except Exception:
            pass
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "research_execution_failed",
                "message": f"Research execution failed: {str(e)}",
                "trace_id": (
                    agent.deps.tracer.get_trace_id()
                    if "agent" in locals() and agent.deps.tracer
                    else None
                ),
            },
        )
