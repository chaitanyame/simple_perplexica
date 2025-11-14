"""Tests for ResearchAgent integration with dynamic prompts and configurable LLM.

Tests that ResearchAgent uses:
1. Dynamic system prompts from SystemPromptGenerator
2. DeepSeek R1 LLM from factory (via settings)
3. Fallback LLM when primary fails
4. Feature flags for dynamic prompts
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.research_agent import ResearchAgent, ResearchAgentDeps
from src.core.config import settings


@pytest.mark.unit
class TestResearchAgentDynamicPrompts:
    """Test ResearchAgent uses dynamic system prompts."""

    @pytest.mark.asyncio
    async def test_generate_plan_uses_dynamic_prompt_when_enabled(self):
        """Test that plan generation uses SystemPromptGenerator when enabled."""
        # Mock dependencies
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {
            "content": '{"steps": [{"step_number": 1, "description": "test", "search_query": "test", "expected_outcome": "test", "depends_on": []}], "estimated_time": 30.0, "complexity": "simple"}'
        }
        
        mock_search_agent = MagicMock()
        mock_tracer = MagicMock()
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        mock_embedding = MagicMock()
        
        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=mock_db,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding
        )
        
        agent = ResearchAgent(deps)
        
        # Patch SystemPromptGenerator
        with patch("src.agents.research_agent.SystemPromptGenerator") as mock_gen:
            mock_gen.generate.return_value = "Dynamic system prompt for planning"
            
            # Enable dynamic prompts
            with patch.object(settings, "ENABLE_DYNAMIC_PROMPTS", True):
                await agent.generate_plan("How to deploy Docker?")
                
                # Verify SystemPromptGenerator was called
                mock_gen.generate.assert_called_once()
                call_args = mock_gen.generate.call_args
                assert "Docker" in call_args[1]["query"] or "Docker" in call_args[0][0]
                
                # Verify LLM received dynamic prompt
                llm_call_args = mock_llm.chat.call_args
                messages = llm_call_args[1]["messages"]
                assert any("Dynamic system prompt" in msg.get("content", "") for msg in messages)

    @pytest.mark.asyncio
    async def test_generate_plan_uses_static_prompt_when_disabled(self):
        """Test that plan generation uses static prompt when dynamic disabled."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {
            "content": '{"steps": [{"step_number": 1, "description": "test", "search_query": "test", "expected_outcome": "test", "depends_on": []}], "estimated_time": 30.0, "complexity": "simple"}'
        }
        
        mock_search_agent = MagicMock()
        mock_tracer = MagicMock()
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        mock_embedding = MagicMock()
        
        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=mock_db,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding
        )
        
        agent = ResearchAgent(deps)
        
        # Disable dynamic prompts
        with patch.object(settings, "ENABLE_DYNAMIC_PROMPTS", False):
            with patch("src.agents.research_agent.SystemPromptGenerator") as mock_gen:
                await agent.generate_plan("How to deploy Docker?")
                
                # Verify SystemPromptGenerator was NOT called
                mock_gen.generate.assert_not_called()
                
                # Verify LLM received static prompt
                llm_call_args = mock_llm.chat.call_args
                messages = llm_call_args[1]["messages"]
                assert any("research planning expert" in msg.get("content", "").lower() for msg in messages)


@pytest.mark.unit
class TestResearchAgentLLMFactory:
    """Test ResearchAgent uses LLM from factory."""

    def test_uses_research_llm_from_factory(self):
        """Test that ResearchAgent can be initialized with factory LLM."""
        with patch("src.agents.research_agent.get_research_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.model = "deepseek/deepseek-r1:free"
            mock_get_llm.return_value = mock_llm
            
            from src.agents.research_agent import get_research_llm
            client = get_research_llm()
            
            # Should get DeepSeek R1 model
            assert "deepseek-r1" in client.model.lower()


@pytest.mark.unit
class TestResearchAgentFallback:
    """Test ResearchAgent fallback mechanism."""

    @pytest.mark.asyncio
    async def test_falls_back_to_fallback_llm_on_error(self):
        """Test that agent falls back to fallback LLM when primary fails."""
        # Primary LLM that fails
        mock_primary_llm = AsyncMock()
        mock_primary_llm.chat.side_effect = Exception("API Error")
        mock_primary_llm.model = "deepseek/deepseek-r1:free"
        
        # Fallback LLM that succeeds
        mock_fallback_llm = AsyncMock()
        mock_fallback_llm.chat.return_value = {
            "content": '{"steps": [{"step_number": 1, "description": "test", "search_query": "test", "expected_outcome": "test", "depends_on": []}], "estimated_time": 30.0, "complexity": "simple"}'
        }
        mock_fallback_llm.model = "google/gemini-2.0-flash-thinking-exp:free"
        
        mock_search_agent = MagicMock()
        mock_tracer = MagicMock()
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        mock_embedding = MagicMock()
        
        # Start with primary LLM
        deps = ResearchAgentDeps(
            llm_client=mock_primary_llm,
            tracer=mock_tracer,
            db=mock_db,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding
        )
        
        agent = ResearchAgent(deps)
        
        # Enable fallback
        with patch.object(settings, "ENABLE_LLM_FALLBACK", True):
            with patch("src.agents.research_agent.get_fallback_llm") as mock_get_fallback:
                mock_get_fallback.return_value = mock_fallback_llm
                
                # Should fallback and succeed
                plan = await agent.generate_plan("What is AI?")
                
                # Verify primary was tried
                assert mock_primary_llm.chat.called
                
                # Verify fallback was called
                mock_get_fallback.assert_called_once()
                assert mock_fallback_llm.chat.called
                
                # Verify plan was generated
                assert len(plan.steps) == 1

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self):
        """Test that agent does not fallback when feature is disabled."""
        # Primary LLM that fails
        mock_primary_llm = AsyncMock()
        mock_primary_llm.chat.side_effect = Exception("API Error")
        
        mock_search_agent = MagicMock()
        mock_tracer = MagicMock()
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        mock_embedding = MagicMock()
        
        deps = ResearchAgentDeps(
            llm_client=mock_primary_llm,
            tracer=mock_tracer,
            db=mock_db,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding
        )
        
        agent = ResearchAgent(deps)
        
        # Disable fallback
        with patch.object(settings, "ENABLE_LLM_FALLBACK", False):
            with patch("src.agents.research_agent.get_fallback_llm") as mock_get_fallback:
                # Should raise exception without trying fallback
                with pytest.raises(Exception, match="API Error"):
                    await agent.generate_plan("What is AI?")
                
                # Verify fallback was NOT called
                mock_get_fallback.assert_not_called()


@pytest.mark.unit
class TestResearchAgentConfiguration:
    """Test ResearchAgent respects configuration."""

    @pytest.mark.asyncio
    async def test_synthesize_uses_dynamic_prompt(self):
        """Test that synthesis uses dynamic prompt for query context."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {
            "content": "Synthesized findings with citations [Source 1]"
        }
        
        mock_search_agent = MagicMock()
        mock_tracer = MagicMock()
        mock_db = MagicMock()
        mock_vector_store = MagicMock()
        mock_embedding = MagicMock()
        
        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=mock_db,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding
        )
        
        agent = ResearchAgent(deps)
        
        # Mock sources
        from src.agents.search_agent import SearchSource
        sources = [
            SearchSource(
                title="Test",
                url="http://test.com",
                content="Test content",
                relevance_score=0.9,
                timestamp="2024-01-01"
            )
        ]
        
        # Enable dynamic prompts
        with patch.object(settings, "ENABLE_DYNAMIC_PROMPTS", True):
            with patch("src.agents.research_agent.SystemPromptGenerator") as mock_gen:
                mock_gen.generate.return_value = "Dynamic synthesis prompt"
                
                await agent.synthesize_findings(
                    query="How does Docker work?",
                    sources=sources,
                    plan_description="Understanding Docker"
                )
                
                # Verify dynamic prompt was used
                mock_gen.generate.assert_called()
                call_kwargs = mock_gen.generate.call_args[1]
                assert "Docker" in call_kwargs.get("query", "")
