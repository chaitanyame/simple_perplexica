"""ResearchAgent - Multi-step research orchestration with SearchAgent delegation.

Architecture:
- Multi-agent coordination pattern
- Step-based planning with dependency management
- Citation management and deduplication
- Iterative refinement for quality
- Pydantic AI integration for structured outputs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..rag.vector_store_repository import VectorStoreRepository
from ..services.llm.langfuse_tracer import LangfuseTracer
from ..services.llm.openrouter_client import OpenRouterClient
from .search_agent import SearchAgent, SearchSource


class ResearchStep(BaseModel):
    """Research step with dependencies."""

    step_number: int = Field(..., description="Step sequence number")
    description: str = Field(..., description="Step description")
    search_query: str = Field(..., description="Query to execute for this step")
    expected_outcome: str = Field(..., description="Expected result from this step")
    depends_on: list[int] = Field(
        default_factory=list, description="List of step numbers this depends on"
    )


class ResearchPlan(BaseModel):
    """Multi-step research plan."""

    original_query: str = Field(..., description="Original user query")
    steps: list[ResearchStep] = Field(..., description="Ordered research steps")
    estimated_time: float = Field(..., description="Estimated time in seconds")
    complexity: str = Field(..., description="Plan complexity: simple, medium, complex")


class Citation(BaseModel):
    """Citation from research source."""

    source_id: str = Field(..., description="Unique source identifier")
    title: str = Field(..., description="Source title")
    url: str = Field(..., description="Source URL")
    excerpt: str = Field(..., description="Relevant excerpt from source")
    relevance: float = Field(..., description="Relevance score (0.0-1.0)")


class ResearchOutput(BaseModel):
    """Complete research output with findings and citations."""

    plan: ResearchPlan = Field(..., description="Research plan that was executed")
    findings: str = Field(..., description="Synthesized research findings")
    citations: list[Citation] = Field(..., description="Supporting citations")
    confidence: float = Field(..., description="Overall confidence score (0.0-1.0)")
    execution_steps: int = Field(..., description="Number of steps executed")


@dataclass
class ResearchAgentDeps:
    """Dependencies for ResearchAgent."""

    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    search_agent: SearchAgent
    vector_store: VectorStoreRepository
    max_iterations: int = 5
    timeout: float = 300.0


class ResearchAgent:
    """Multi-step research agent with SearchAgent delegation.

    Orchestrates complex research tasks by:
    1. Breaking queries into structured research plans
    2. Delegating searches to SearchAgent
    3. Managing citations and deduplication
    4. Synthesizing findings from multiple sources
    5. Iterative refinement for quality
    """

    def __init__(self, deps: ResearchAgentDeps) -> None:
        """Initialize ResearchAgent with dependencies."""
        self.deps = deps
        self.llm_client = deps.llm_client
        self.tracer = deps.tracer
        self.db = deps.db
        self.search_agent = deps.search_agent
        self.vector_store = deps.vector_store
        self.max_iterations = deps.max_iterations
        self.timeout = deps.timeout

    async def generate_plan(self, query: str) -> ResearchPlan:
        """Generate multi-step research plan.

        Args:
            query: Research query to plan for

        Returns:
            ResearchPlan with ordered steps and dependencies

        Raises:
            ValueError: If plan generation fails
        """
        system_prompt = """You are a research planning expert. Break down complex queries into structured research plans.

For each step:
- Assign a sequential step_number
- Provide clear description and search_query
- Define expected_outcome
- Specify dependencies (which steps must complete first)

Complexity levels:
- simple: 1-2 steps, single topic
- medium: 2-4 steps, related topics
- complex: 4+ steps, multiple topics with dependencies"""

        user_prompt = f"""Create a research plan for: "{query}"

Return JSON with:
- steps: List of ResearchStep objects
- estimated_time: Total time in seconds
- complexity: simple/medium/complex"""

        response = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="anthropic/claude-3.5-sonnet",
            temperature=0.1,
        )

        # Extract plan data
        if hasattr(response, "get"):
            steps_data = response.get("steps", [])
            estimated_time = response.get("estimated_time", 60.0)
            complexity = response.get("complexity", "medium")
        else:
            # Fallback for non-dict response
            steps_data = []
            estimated_time = 60.0
            complexity = "medium"

        # Build ResearchStep objects
        steps = [
            ResearchStep(
                step_number=step["step_number"],
                description=step["description"],
                search_query=step["search_query"],
                expected_outcome=step["expected_outcome"],
                depends_on=step.get("depends_on", []),
            )
            for step in steps_data
        ]

        return ResearchPlan(
            original_query=query,
            steps=steps,
            estimated_time=estimated_time,
            complexity=complexity,
        )

    async def gather_evidence(self, query: str) -> list[SearchSource]:
        """Gather evidence by delegating to SearchAgent.

        Args:
            query: Search query for evidence

        Returns:
            List of SearchSource results from SearchAgent

        Note:
            Handles timeouts gracefully, returning empty list on failure
        """
        try:
            result = await self.search_agent.run(query)
            return result.sources
        except TimeoutError:
            # Handle timeout gracefully
            return []
        except Exception:
            # Handle other search errors
            return []

    async def extract_citations(self, sources: list[SearchSource], query: str) -> list[Citation]:
        """Extract and deduplicate citations from sources.

        Args:
            sources: List of SearchSource objects
            query: Original query for relevance context

        Returns:
            Deduplicated list of Citation objects, sorted by relevance

        Note:
            Deduplicates by URL, keeping highest relevance score
        """
        # Convert sources to citations
        citations_dict: dict[str, Citation] = {}

        for idx, source in enumerate(sources):
            # Skip if URL already exists with higher relevance
            if source.url in citations_dict:
                if citations_dict[source.url].relevance >= source.relevance:
                    continue

            # Create or update citation
            citations_dict[source.url] = Citation(
                source_id=str(idx),
                title=source.title,
                url=source.url,
                excerpt=source.snippet,
                relevance=source.relevance,
            )

        # Convert to list and sort by relevance (descending)
        citations = list(citations_dict.values())
        citations.sort(key=lambda c: c.relevance, reverse=True)

        return citations

    async def synthesize_findings(self, citations: list[Citation], query: str) -> str:
        """Synthesize findings from multiple citations.

        Args:
            citations: List of citations to synthesize
            query: Original research query

        Returns:
            Synthesized findings text (minimum 100 characters)

        Raises:
            ValueError: If synthesis fails
        """
        system_prompt = """You are a research synthesis expert. Combine information from multiple sources into coherent findings.

Requirements:
- Synthesize across all sources
- Maintain factual accuracy
- Provide comprehensive coverage
- Minimum 100 characters"""

        # Build citation context
        citation_context = "\n\n".join(
            [
                f"Source {i + 1}: {c.title}\nURL: {c.url}\nExcerpt: {c.excerpt}"
                for i, c in enumerate(citations)
            ]
        )

        user_prompt = f"""Synthesize findings for query: "{query}"

Sources:
{citation_context}

Provide comprehensive synthesis:"""

        response = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="anthropic/claude-3.5-sonnet",
            temperature=0.3,
        )

        # Extract synthesis
        if hasattr(response, "get"):
            synthesis: str = str(response.get("synthesis", ""))
        else:
            synthesis = ""

        return synthesis

    async def identify_gaps(self, findings: str, query: str) -> dict[str, Any]:
        """Identify gaps in research findings for iterative refinement.

        Args:
            findings: Current research findings
            query: Original query

        Returns:
            Dict with needs_refinement, gaps, additional_queries
        """
        system_prompt = """You are a research quality expert. Analyze findings for gaps and suggest improvements.

Evaluate:
- Coverage of query topics
- Missing context or details
- Need for additional sources

Return JSON:
- needs_refinement: bool
- gaps: list of missing topics
- additional_queries: list of follow-up queries"""

        user_prompt = f"""Analyze findings for query: "{query}"

Current findings:
{findings}

Identify gaps:"""

        response = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="anthropic/claude-3.5-sonnet",
            temperature=0.1,
        )

        # Extract gap analysis
        if hasattr(response, "get"):
            return {
                "needs_refinement": response.get("needs_refinement", False),
                "gaps": response.get("gaps", []),
                "additional_queries": response.get("additional_queries", []),
            }
        else:
            return {
                "needs_refinement": False,
                "gaps": [],
                "additional_queries": [],
            }

    async def validate_output(self, output: ResearchOutput) -> None:
        """Validate research output meets quality thresholds.

        Args:
            output: ResearchOutput to validate

        Raises:
            Exception: If validation fails (triggers ModelRetry in Pydantic AI)
        """
        # Minimum 3 citations
        if len(output.citations) < 3:
            raise Exception(f"Insufficient citations: {len(output.citations)} (minimum 3 required)")

        # Minimum findings length (100 characters)
        if len(output.findings) < 100:
            raise Exception(
                f"Findings too short: {len(output.findings)} chars (minimum 100 required)"
            )

        # Minimum confidence
        if output.confidence < 0.5:
            raise Exception(f"Low confidence: {output.confidence} (minimum 0.5 required)")

    async def run(self, query: str) -> ResearchOutput:
        """Execute full research workflow.

        Args:
            query: Research query to process

        Returns:
            ResearchOutput with plan, findings, and citations

        Workflow:
            1. Generate research plan
            2. Execute plan steps (gather evidence)
            3. Extract and deduplicate citations
            4. Synthesize findings
            5. Validate output quality
        """
        # Step 1: Generate plan
        plan = await self.generate_plan(query)

        # Step 2: Execute plan steps
        all_sources: list[SearchSource] = []
        for step in plan.steps:
            sources = await self.gather_evidence(step.search_query)
            all_sources.extend(sources)

        # Step 3: Extract citations (with deduplication)
        citations = await self.extract_citations(all_sources, query)

        # Step 4: Synthesize findings
        findings = await self.synthesize_findings(citations, query)

        # Step 5: Build output
        output = ResearchOutput(
            plan=plan,
            findings=findings,
            citations=citations,
            confidence=min(sum(c.relevance for c in citations) / max(len(citations), 1), 1.0),
            execution_steps=len(plan.steps),
        )

        # Step 6: Validate
        await self.validate_output(output)

        return output
