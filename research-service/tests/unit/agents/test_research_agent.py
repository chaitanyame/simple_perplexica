"""Unit tests for ResearchAgent - RED phase (tests written FIRST).

Test Coverage:
- Agent initialization with SearchAgent delegation
- Research plan generation (simple/complex queries)
- Step dependency management
- Evidence gathering via SearchAgent
- Cross-source synthesis
- Citation extraction and deduplication
- Iterative refinement workflow
- Output validation
- Full research workflow
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.research_agent import (
    Citation,
    ResearchAgent,
    ResearchAgentDeps,
    ResearchOutput,
    ResearchPlan,
    ResearchStep,
)
from src.agents.search_agent import (
    SearchAgent,
    SearchOutput,
    SearchSource,
    SubQuery,
)
from src.rag.vector_store_repository import VectorStoreRepository
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.fixture
def mock_llm_client() -> OpenRouterClient:
    """Mock OpenRouter LLM client."""
    client = MagicMock(spec=OpenRouterClient)
    client.chat = AsyncMock()
    return client


@pytest.fixture
def mock_tracer() -> LangfuseTracer:
    """Mock Langfuse tracer."""
    tracer = MagicMock(spec=LangfuseTracer)
    tracer.trace_llm_call = AsyncMock()
    return tracer


@pytest.fixture
def mock_search_agent() -> SearchAgent:
    """Mock SearchAgent for delegation."""
    agent = MagicMock(spec=SearchAgent)
    agent.run = AsyncMock()
    return agent


@pytest.fixture
def mock_vector_store() -> VectorStoreRepository:
    """Mock vector store repository."""
    repo = MagicMock(spec=VectorStoreRepository)
    repo.search_similar = AsyncMock()
    return repo


@pytest.fixture
def research_agent_deps(
    mock_llm_client: OpenRouterClient,
    mock_tracer: LangfuseTracer,
    async_session: AsyncSession,
    mock_search_agent: SearchAgent,
    mock_vector_store: VectorStoreRepository,
) -> ResearchAgentDeps:
    """Create ResearchAgent dependencies for testing."""
    return ResearchAgentDeps(
        llm_client=mock_llm_client,
        tracer=mock_tracer,
        db=async_session,
        search_agent=mock_search_agent,
        vector_store=mock_vector_store,
        max_iterations=5,
        timeout=300.0,
    )


class TestResearchAgentInitialization:
    """Test ResearchAgent initialization and setup."""

    def test_research_agent_initialization(self, research_agent_deps: ResearchAgentDeps) -> None:
        """Test that ResearchAgent initializes with correct dependencies.

        Given: Valid ResearchAgentDeps with SearchAgent
        When: Creating a ResearchAgent instance
        Then: Agent is initialized with correct configuration
        """
        agent = ResearchAgent(deps=research_agent_deps)

        assert agent is not None
        assert agent.deps == research_agent_deps
        assert agent.max_iterations == 5
        assert agent.timeout == 300.0
        assert agent.search_agent is not None

    def test_research_agent_initialization_custom_params(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test ResearchAgent initialization with custom parameters.

        Given: ResearchAgentDeps with custom max_iterations and timeout
        When: Creating a ResearchAgent instance
        Then: Agent uses custom parameters
        """
        custom_deps = ResearchAgentDeps(
            llm_client=research_agent_deps.llm_client,
            tracer=research_agent_deps.tracer,
            db=research_agent_deps.db,
            search_agent=research_agent_deps.search_agent,
            vector_store=research_agent_deps.vector_store,
            max_iterations=10,
            timeout=600.0,
        )

        agent = ResearchAgent(deps=custom_deps)

        assert agent.max_iterations == 10
        assert agent.timeout == 600.0


class TestResearchPlanGeneration:
    """Test research plan generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_plan_simple_query(self, research_agent_deps: ResearchAgentDeps) -> None:
        """Test plan generation for a simple query.

        Given: A ResearchAgent with mocked LLM
        When: Generating plan for simple query
        Then: Returns a ResearchPlan with 1-2 steps
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Mock LLM response
        research_agent_deps.llm_client.chat.return_value = {
            "steps": [
                {
                    "step_number": 1,
                    "description": "Define artificial intelligence",
                    "search_query": "what is artificial intelligence",
                    "expected_outcome": "Clear definition of AI",
                    "depends_on": [],
                }
            ],
            "estimated_time": 30.0,
            "complexity": "simple",
        }

        result = await agent.generate_plan("What is artificial intelligence?")

        assert isinstance(result, ResearchPlan)
        assert result.complexity == "simple"
        assert len(result.steps) <= 2
        assert result.steps[0].step_number == 1

    @pytest.mark.asyncio
    async def test_generate_plan_complex_query(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test plan generation for a complex multi-part query.

        Given: A ResearchAgent with mocked LLM
        When: Generating plan for complex query
        Then: Returns a ResearchPlan with 3+ steps
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Mock LLM response with multiple steps
        research_agent_deps.llm_client.chat.return_value = {
            "steps": [
                {
                    "step_number": 1,
                    "description": "Define AI agents",
                    "search_query": "what are AI agents",
                    "expected_outcome": "Clear definition",
                    "depends_on": [],
                },
                {
                    "step_number": 2,
                    "description": "Research agent architectures",
                    "search_query": "AI agent architectures",
                    "expected_outcome": "Architecture patterns",
                    "depends_on": [1],
                },
                {
                    "step_number": 3,
                    "description": "Find use cases",
                    "search_query": "AI agent applications",
                    "expected_outcome": "Real-world examples",
                    "depends_on": [1, 2],
                },
            ],
            "estimated_time": 120.0,
            "complexity": "complex",
        }

        result = await agent.generate_plan(
            "What are AI agents, how do they work, and what are their use cases?"
        )

        assert isinstance(result, ResearchPlan)
        assert result.complexity == "complex"
        assert len(result.steps) >= 3
        assert result.steps[2].depends_on == [1, 2]

    @pytest.mark.asyncio
    async def test_plan_step_dependencies(self, research_agent_deps: ResearchAgentDeps) -> None:
        """Test that plan steps have correct dependency relationships.

        Given: A ResearchAgent generating a multi-step plan
        When: Analyzing step dependencies
        Then: Steps have valid dependency chains
        """
        agent = ResearchAgent(deps=research_agent_deps)

        research_agent_deps.llm_client.chat.return_value = {
            "steps": [
                {
                    "step_number": 1,
                    "description": "Step 1",
                    "search_query": "query 1",
                    "expected_outcome": "outcome 1",
                    "depends_on": [],
                },
                {
                    "step_number": 2,
                    "description": "Step 2",
                    "search_query": "query 2",
                    "expected_outcome": "outcome 2",
                    "depends_on": [1],
                },
            ],
            "estimated_time": 60.0,
            "complexity": "medium",
        }

        result = await agent.generate_plan("Complex query")

        # Check dependency chain
        assert result.steps[0].depends_on == []
        assert result.steps[1].depends_on == [1]
        # Step 2 depends on Step 1, so it must come after
        assert result.steps[1].step_number > result.steps[0].step_number


class TestEvidenceGathering:
    """Test evidence gathering via SearchAgent delegation."""

    @pytest.mark.asyncio
    async def test_gather_evidence_via_search_agent(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test evidence gathering by delegating to SearchAgent.

        Given: A ResearchAgent with SearchAgent
        When: Gathering evidence for a query
        Then: SearchAgent is called and results returned
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Mock SearchAgent response
        mock_search_output = SearchOutput(
            sub_queries=[SubQuery(query="AI agents", intent="definition", priority=1)],
            sources=[
                SearchSource(
                    title="AI Overview",
                    url="https://example.com/ai",
                    snippet="AI agents are...",
                    relevance=0.9,
                    source_type="academic",
                )
            ],
            execution_time=1.5,
            confidence=0.8,
        )
        research_agent_deps.search_agent.run.return_value = mock_search_output

        results = await agent.gather_evidence("What are AI agents?")

        assert len(results) > 0
        assert all(isinstance(r, SearchSource) for r in results)
        research_agent_deps.search_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_gather_evidence_timeout_handling(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test graceful timeout handling in evidence gathering.

        Given: A ResearchAgent with SearchAgent that times out
        When: Gathering evidence
        Then: Returns empty results without raising exception
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Mock timeout
        research_agent_deps.search_agent.run.side_effect = TimeoutError("Search timeout")

        results = await agent.gather_evidence("test query")

        assert isinstance(results, list)
        # Timeout handled gracefully


class TestCitationManagement:
    """Test citation extraction and management."""

    @pytest.mark.asyncio
    async def test_extract_citations_from_sources(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test citation extraction from search sources.

        Given: A ResearchAgent with search sources
        When: Extracting citations
        Then: Returns list of Citation objects
        """
        agent = ResearchAgent(deps=research_agent_deps)

        sources = [
            SearchSource(
                title="AI Research Paper",
                url="https://example.com/paper1",
                snippet="Detailed research on AI agents...",
                relevance=0.9,
                source_type="academic",
            ),
            SearchSource(
                title="AI Tutorial",
                url="https://example.com/tutorial",
                snippet="Tutorial on building AI agents...",
                relevance=0.7,
                source_type="web",
            ),
        ]

        citations = await agent.extract_citations(sources, "AI agents")

        assert len(citations) == 2
        assert all(isinstance(c, Citation) for c in citations)
        assert citations[0].relevance >= citations[1].relevance

    @pytest.mark.asyncio
    async def test_citation_deduplication(self, research_agent_deps: ResearchAgentDeps) -> None:
        """Test deduplication of citations by URL.

        Given: A ResearchAgent with duplicate sources
        When: Extracting citations
        Then: Duplicate URLs are removed
        """
        agent = ResearchAgent(deps=research_agent_deps)

        sources = [
            SearchSource(
                title="AI Paper 1",
                url="https://example.com/paper",  # Duplicate URL
                snippet="Content 1",
                relevance=0.9,
                source_type="academic",
            ),
            SearchSource(
                title="AI Paper 2",
                url="https://example.com/paper",  # Duplicate URL
                snippet="Content 2",
                relevance=0.8,
                source_type="academic",
            ),
            SearchSource(
                title="AI Tutorial",
                url="https://example.com/tutorial",  # Unique URL
                snippet="Tutorial content",
                relevance=0.7,
                source_type="web",
            ),
        ]

        citations = await agent.extract_citations(sources, "AI")

        # Check deduplication (should keep highest relevance)
        urls = [c.url for c in citations]
        assert len(urls) == len(set(urls))
        assert "https://example.com/paper" in urls
        assert "https://example.com/tutorial" in urls


class TestSynthesisAndRefinement:
    """Test cross-source synthesis and iterative refinement."""

    @pytest.mark.asyncio
    async def test_synthesize_findings_from_sources(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test synthesis of findings from multiple sources.

        Given: A ResearchAgent with multiple citations
        When: Synthesizing findings
        Then: Returns coherent synthesized text
        """
        agent = ResearchAgent(deps=research_agent_deps)

        citations = [
            Citation(
                source_id="1",
                title="Source 1",
                url="https://example.com/1",
                excerpt="AI agents are autonomous...",
                relevance=0.9,
            ),
            Citation(
                source_id="2",
                title="Source 2",
                url="https://example.com/2",
                excerpt="AI agents use learning algorithms...",
                relevance=0.8,
            ),
        ]

        # Mock LLM synthesis (>= 100 chars)
        research_agent_deps.llm_client.chat.return_value = {
            "synthesis": "AI agents are autonomous systems that use learning algorithms to perform tasks and make decisions. They can adapt to changing environments and learn from experience to improve their performance over time."
        }

        result = await agent.synthesize_findings(citations, "What are AI agents?")

        assert isinstance(result, str)
        assert len(result) >= 100  # Minimum findings length
        research_agent_deps.llm_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_iterative_refinement_workflow(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test iterative refinement of research findings.

        Given: A ResearchAgent with initial findings
        When: Refining findings based on gaps
        Then: Generates additional search queries and improves findings
        """
        agent = ResearchAgent(deps=research_agent_deps)

        initial_findings = "AI agents are autonomous systems..."

        # Mock LLM refinement suggestion
        research_agent_deps.llm_client.chat.return_value = {
            "needs_refinement": True,
            "gaps": ["Missing: how agents learn", "Missing: real-world examples"],
            "additional_queries": ["AI agent learning methods", "AI agent use cases"],
        }

        refinement_plan = await agent.identify_gaps(initial_findings, "AI agents")

        assert refinement_plan["needs_refinement"] is True
        assert len(refinement_plan["gaps"]) > 0
        assert len(refinement_plan["additional_queries"]) > 0


class TestOutputValidation:
    """Test ResearchAgent output validation."""

    @pytest.mark.asyncio
    async def test_output_validation_min_citations(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test validation of minimum citation count.

        Given: A ResearchAgent with output
        When: Output has fewer citations than minimum
        Then: Validation raises ModelRetry
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Output with insufficient citations (< 3 minimum)
        output = ResearchOutput(
            plan=ResearchPlan(
                original_query="test",
                steps=[
                    ResearchStep(
                        step_number=1,
                        description="step",
                        search_query="query",
                        expected_outcome="outcome",
                        depends_on=[],
                    )
                ],
                estimated_time=30.0,
                complexity="simple",
            ),
            findings="Some findings here...",
            citations=[
                Citation(
                    source_id="1",
                    title="Source 1",
                    url="https://example.com/1",
                    excerpt="excerpt",
                    relevance=0.8,
                )
            ],  # Only 1 citation
            confidence=0.7,
            execution_steps=1,
        )

        # Should raise exception for insufficient citations
        with pytest.raises(Exception):
            await agent.validate_output(output)

    @pytest.mark.asyncio
    async def test_output_validation_findings_length(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test validation of findings minimum length.

        Given: A ResearchAgent with output
        When: Findings are too short
        Then: Validation raises ModelRetry
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Output with short findings (< 100 chars minimum)
        output = ResearchOutput(
            plan=ResearchPlan(
                original_query="test",
                steps=[
                    ResearchStep(
                        step_number=1,
                        description="step",
                        search_query="query",
                        expected_outcome="outcome",
                        depends_on=[],
                    )
                ],
                estimated_time=30.0,
                complexity="simple",
            ),
            findings="Short.",  # Too short
            citations=[
                Citation(
                    source_id=str(i),
                    title=f"Source {i}",
                    url=f"https://example.com/{i}",
                    excerpt="excerpt",
                    relevance=0.8,
                )
                for i in range(5)
            ],  # Sufficient citations
            confidence=0.7,
            execution_steps=1,
        )

        # Should raise exception for short findings
        with pytest.raises(Exception):
            await agent.validate_output(output)


class TestResearchAgentFullWorkflow:
    """Test full ResearchAgent workflow end-to-end."""

    @pytest.mark.asyncio
    async def test_research_agent_full_workflow(
        self, research_agent_deps: ResearchAgentDeps
    ) -> None:
        """Test complete research workflow from query to output.

        Given: A ResearchAgent with all dependencies
        When: Running a complete research query
        Then: Returns ResearchOutput with plan, findings, and citations
        """
        agent = ResearchAgent(deps=research_agent_deps)

        # Mock LLM responses (plan generation, then synthesis)
        research_agent_deps.llm_client.chat.side_effect = [
            # First call: plan generation
            {
                "steps": [
                    {
                        "step_number": 1,
                        "description": "Research AI agents",
                        "search_query": "what are AI agents",
                        "expected_outcome": "Understanding of AI agents",
                        "depends_on": [],
                    }
                ],
                "estimated_time": 60.0,
                "complexity": "simple",
            },
            # Second call: synthesis
            {
                "synthesis": "AI agents are autonomous systems that can perceive their environment, make decisions, and take actions to achieve specific goals. They use various techniques including machine learning, natural language processing, and reasoning to perform complex tasks efficiently."
            },
        ]

        # Mock SearchAgent response
        mock_search_output = SearchOutput(
            sub_queries=[SubQuery(query="AI agents", intent="definition", priority=1)],
            sources=[
                SearchSource(
                    title=f"AI Source {i}",
                    url=f"https://example.com/{i}",
                    snippet=f"AI agents content {i}with detailed information about autonomous systems and their capabilities",
                    relevance=0.8,
                    source_type="academic",
                )
                for i in range(5)
            ],
            execution_time=1.5,
            confidence=0.8,
        )
        research_agent_deps.search_agent.run.return_value = mock_search_output

        # Execute full workflow
        result = await agent.run("What are AI agents?")

        assert isinstance(result, ResearchOutput)
        assert isinstance(result.plan, ResearchPlan)
        assert len(result.citations) >= 3
        assert len(result.findings) >= 100
        assert result.confidence >= 0.5
        assert result.execution_steps > 0
