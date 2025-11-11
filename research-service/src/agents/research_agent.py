"""ResearchAgent - Multi-step research orchestration with SearchAgent delegation.

Architecture:
- Multi-agent coordination pattern
- Step-based planning with dependency management
- Citation management and deduplication
- Iterative refinement for quality
- Pydantic AI integration for structured outputs
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.search_modes import SearchMode, get_mode_from_string
from ..rag.vector_store_repository import VectorStoreRepository
from ..services.llm.langfuse_tracer import LangfuseTracer
from ..services.llm.openrouter_client import OpenRouterClient
from .search_agent import SearchAgent, SearchSource

logger = structlog.get_logger(__name__)


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

    async def gather_evidence(
        self,
        query: str,
        mode: SearchMode | str | None = None,
    ) -> list[SearchSource]:
        """Gather evidence by delegating to SearchAgent with mode.

        Args:
            query: Search query for evidence
            mode: Search mode to pass to SearchAgent (SPEED/BALANCED/DEEP)

        Returns:
            List of SearchSource results from SearchAgent

        Note:
            Handles timeouts gracefully, returning empty list on failure
        """
        try:
            result = await self.search_agent.run(query, mode=mode)
            return result.sources
        except TimeoutError:
            # Handle timeout gracefully
            return []
        except Exception:
            # Handle other search errors
            return []

    async def store_sources_to_vector_db(
        self,
        session_id: str,
        sources: list[SearchSource],
    ) -> int:
        """Store search sources in vector database for hybrid retrieval.

        Args:
            session_id: Research session UUID
            sources: List of SearchSource objects to store

        Returns:
            Number of documents successfully stored

        Note:
            Only stores sources with content (crawled results)
            Generates embeddings using embedding service
        """
        stored_count = 0

        for source in sources:
            # Skip if no content
            if not source.content or not source.content.strip():
                continue

            try:
                # Generate embedding for content
                embedding = await self.search_agent.deps.embedding_service.embed_text(
                    source.content
                )

                # Store in vector database
                await self.vector_store.store_vector(
                    session_id=session_id,
                    content=source.content,
                    embedding=embedding,
                    metadata={
                        "title": source.title,
                        "url": source.url,
                        "source_type": source.source_type,
                        "relevance": source.relevance,
                        "semantic_score": source.semantic_score,
                    },
                )

                stored_count += 1

            except Exception as e:
                # Log error but continue with other sources
                continue

        return stored_count

    async def hybrid_retrieve(
        self,
        session_id: str,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> list[dict]:
        """Retrieve documents using hybrid search (vector + FTS).

        Args:
            session_id: Research session UUID
            query: Query text for retrieval
            top_k: Number of top results to return
            semantic_weight: Weight for semantic similarity (default: 0.6)
            keyword_weight: Weight for keyword matching (default: 0.4)

        Returns:
            List of retrieved documents with content and metadata

        Note:
            Uses VectorStoreRepository.hybrid_search() for RRF-based retrieval
            Combines vector similarity + PostgreSQL FTS
        """
        try:
            # Generate query embedding
            query_embedding = await self.search_agent.deps.embedding_service.embed_text(query)

            # Perform hybrid search
            results = await self.vector_store.hybrid_search(
                session_id=session_id,
                query_text=query,
                query_vector=query_embedding,
                top_k=top_k,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
            )

            # Convert SearchResult objects to dicts
            return [
                {
                    "id": str(result.id),
                    "content": result.content,
                    "metadata": result.metadata,
                    "similarity_score": result.similarity_score,
                }
                for result in results
            ]

        except Exception as e:
            # Return empty list on error
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
            Synthesized findings text (minimum 500 characters)

        Raises:
            ValueError: If synthesis fails
        """
        system_prompt = """You are a research synthesis expert who extracts and explains SPECIFIC information from sources.

MANDATORY Rules:
- Extract EVERY specific detail: names, numbers, dates, features, products
- EXPLAIN every item you mention - what it is, what it does, why it matters
- Never just list product names - always add descriptions
- NO generic statements without specifics
- NO hedging or meta-commentary
- Cite source numbers for every fact
- Use bullet points with explanations: "- Item Name: what it does/is [source]"
- 600+ words minimum with full explanations
- Add context: what, why, how, when for each point"""

        # Build citation context
        citation_context = "\n\n".join(
            [
                f"Source {i + 1}: {c.title}\nURL: {c.url}\nExcerpt: {c.excerpt}"
                for i, c in enumerate(citations)
            ]
        )

        user_prompt = f"""Synthesize findings for: "{query}"

Sources:
{citation_context}

EXTRACT AND EXPLAIN ALL INFORMATION:

1. For EVERY item mentioned in sources, provide:
   - Name/Title
   - What it is/does
   - Key capabilities or features
   - Why it matters or use cases
   - Source citation [number]

2. NEVER just list names:
   ✗ BAD: "Azure AI Foundry, Azure AI Search, Azure OpenAI [2]"
   ✓ GOOD:
     "- Azure AI Foundry: Unified platform for developing and deploying AI applications, providing tools for model training and management [2]
      - Azure AI Search: Vector search service with semantic ranking capabilities for retrieval-augmented generation [2]
      - Azure OpenAI: Provides access to GPT-4, GPT-3.5, and other OpenAI models through Azure infrastructure [2]"

3. Add context and details:
   - Numbers → what they represent and why significant
   - Events → dates, locations, purpose, expected outcomes
   - Products → capabilities, target users, integration points
   - Features → how they work, benefits, use cases

4. Structure with sections, bullets with descriptions

5. 600+ words with full explanations for everything

Write detailed synthesis with descriptions for every item:"""

        response = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="anthropic/claude-3.5-sonnet",
            temperature=0.3,
            max_tokens=2048,  # Allow longer, more detailed responses
        )

        # Extract synthesis - fix bug: response has "content" key, not "synthesis"
        if isinstance(response, dict) and "content" in response:
            synthesis: str = str(response["content"])
        else:
            logger.warning(f"Unexpected response format: {type(response)}")
            synthesis = ""

        # Ensure minimum length
        if len(synthesis) < 200:
            logger.warning(f"⚠️ Synthesis too short ({len(synthesis)} chars), requesting more detail")
            # Try again with more explicit instructions
            retry_prompt = f"{user_prompt}\n\nIMPORTANT: Provide a DETAILED synthesis of at least 400 words. Do not summarize briefly."
            response = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": retry_prompt},
                ],
                model="anthropic/claude-3.5-sonnet",
                temperature=0.3,
                max_tokens=2048,
            )
            if isinstance(response, dict) and "content" in response:
                synthesis = str(response["content"])

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

    async def run(
        self,
        query: str,
        mode: SearchMode | str | None = None,
    ) -> ResearchOutput:
        """Execute full research workflow with configurable mode.

        Args:
            query: Research query to process
            mode: Search mode (SPEED/BALANCED/DEEP) or mode string or None (defaults to BALANCED)

        Returns:
            ResearchOutput with plan, findings, and citations

        Workflow:
            1. Generate research plan
            2. Execute plan steps (gather evidence) with mode
            3. Extract and deduplicate citations
            4. Synthesize findings
            5. Validate output quality
        """
        # Parse mode
        if isinstance(mode, str):
            search_mode = get_mode_from_string(mode)
        elif mode is None:
            search_mode = SearchMode.BALANCED
        else:
            search_mode = mode
        
        config = search_mode.config
        
        import structlog
        logger = structlog.get_logger(__name__)
        logger.info(
            "Starting research with mode",
            query=query,
            mode=search_mode.value,
        )

        # Step 1: Generate plan
        plan = await self.generate_plan(query)

        # Step 2: Execute plan steps with mode
        all_sources: list[SearchSource] = []
        for step in plan.steps:
            # Pass mode to SearchAgent via gather_evidence
            sources = await self.gather_evidence(step.search_query, mode=search_mode)
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

        logger.info(
            "Research complete",
            mode=search_mode.value,
            num_citations=len(citations),
            num_steps=len(plan.steps),
        )

        return output

    async def run_with_rag(
        self,
        query: str,
        session_id: str,
        mode: SearchMode | str | None = None,
        use_hybrid_search: bool = True,
    ) -> ResearchOutput:
        """Execute research workflow with RAG (hybrid search enabled) and configurable mode.

        This enhanced workflow:
        1. Generates research plan
        2. Gathers evidence from web search with mode
        3. Stores sources in vector database
        4. Optionally retrieves from past research using hybrid search
        5. Synthesizes findings from both new and retrieved sources
        6. Validates output quality

        Args:
            query: Research query to process
            session_id: Session UUID for vector storage
            mode: Search mode (SPEED/BALANCED/DEEP) or mode string or None (defaults to BALANCED)
            use_hybrid_search: Whether to retrieve from past research (default: True)

        Returns:
            ResearchOutput with plan, findings, and citations

        Example:
            >>> output = await agent.run_with_rag(
            ...     query="How do transformer models work?",
            ...     session_id=str(uuid.uuid4()),
            ...     mode=SearchMode.DEEP,
            ...     use_hybrid_search=True
            ... )
        """
        import uuid
        import structlog
        
        logger = structlog.get_logger(__name__)

        # Parse mode
        if isinstance(mode, str):
            search_mode = get_mode_from_string(mode)
        elif mode is None:
            search_mode = SearchMode.BALANCED
        else:
            search_mode = mode
        
        config = search_mode.config
        
        # Override use_hybrid_search based on mode
        if not config.enable_rag:
            use_hybrid_search = False
            logger.info("RAG disabled by mode", mode=search_mode.value)
        
        logger.info(
            "Starting RAG research with mode",
            query=query,
            mode=search_mode.value,
            use_hybrid_search=use_hybrid_search,
        )

        # Step 1: Generate plan
        plan = await self.generate_plan(query)

        # Step 2: Execute plan steps (gather fresh evidence) with mode
        all_sources: list[SearchSource] = []
        for step in plan.steps:
            sources = await self.gather_evidence(step.search_query, mode=search_mode)
            all_sources.extend(sources)

        # Step 3: Store sources in vector database for future retrieval
        if all_sources:
            stored_count = await self.store_sources_to_vector_db(
                session_id=uuid.UUID(session_id),
                sources=all_sources,
            )
            logger.info("Stored sources to vector DB", count=stored_count)

        # Step 4: Retrieve from past research using hybrid search with mode weights
        retrieved_docs = []
        if use_hybrid_search:
            retrieved_docs = await self.hybrid_retrieve(
                session_id=uuid.UUID(session_id),
                query=query,
                top_k=config.max_sources,  # Use mode's max_sources
                semantic_weight=config.semantic_weight,  # Use mode's weights
                keyword_weight=config.keyword_weight,
            )
            logger.info("Retrieved from hybrid search", count=len(retrieved_docs))

        # Step 5: Convert retrieved docs to SearchSource format
        retrieved_sources = []
        for doc in retrieved_docs:
            metadata = doc.get("metadata", {})
            retrieved_sources.append(
                SearchSource(
                    title=metadata.get("title", "Retrieved Document"),
                    url=metadata.get("url", ""),
                    snippet="",  # Content is in full content field
                    content=doc["content"],
                    relevance=metadata.get("relevance", 0.5),
                    semantic_score=metadata.get("semantic_score"),
                    final_score=doc["similarity_score"],  # Hybrid RRF score
                    source_type=metadata.get("source_type", "web"),
                )
            )

        # Combine fresh and retrieved sources
        combined_sources = all_sources + retrieved_sources

        # Step 6: Extract citations (with deduplication)
        citations = await self.extract_citations(combined_sources, query)

        # Step 7: Synthesize findings from both new and retrieved sources
        findings = await self.synthesize_findings(citations, query)

        # Step 8: Build output
        output = ResearchOutput(
            plan=plan,
            findings=findings,
            citations=citations,
            confidence=min(sum(c.relevance for c in citations) / max(len(citations), 1), 1.0),
            execution_steps=len(plan.steps),
        )

        # Step 9: Validate
        await self.validate_output(output)

        return output
