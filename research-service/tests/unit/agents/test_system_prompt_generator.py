"""Tests for system prompt generator.

This module tests the SystemPromptGenerator which creates dynamic
system prompts based on query analysis (NO LLM CALLS - pure logic).
"""
from __future__ import annotations

import pytest

from src.agents.system_prompt_generator import (
    QueryDomain,
    QueryType,
    SystemPromptGenerator,
)


@pytest.mark.unit
@pytest.mark.fast
class TestQueryTypeDetection:
    """Test query type detection from patterns."""

    def test_detect_factual_query(self):
        """Test detection of factual queries."""
        assert SystemPromptGenerator.detect_query_type("What is AI?") == QueryType.FACTUAL
        assert SystemPromptGenerator.detect_query_type("Who invented Python?") == QueryType.FACTUAL
        assert SystemPromptGenerator.detect_query_type("When was Docker created?") == QueryType.FACTUAL
        assert SystemPromptGenerator.detect_query_type("Where is headquarters located?") == QueryType.FACTUAL

    def test_detect_howto_query(self):
        """Test detection of how-to queries."""
        assert SystemPromptGenerator.detect_query_type("How do I deploy with Docker?") == QueryType.HOW_TO
        assert SystemPromptGenerator.detect_query_type("How to implement OAuth2?") == QueryType.HOW_TO
        assert SystemPromptGenerator.detect_query_type("Explain how neural networks work") == QueryType.HOW_TO
        assert SystemPromptGenerator.detect_query_type("Show me how to create API") == QueryType.HOW_TO

    def test_detect_comparison_query(self):
        """Test detection of comparison queries."""
        assert SystemPromptGenerator.detect_query_type("Rust vs Go performance") == QueryType.COMPARISON
        assert SystemPromptGenerator.detect_query_type("Compare Docker and Kubernetes") == QueryType.COMPARISON
        assert SystemPromptGenerator.detect_query_type("Difference between REST and GraphQL") == QueryType.COMPARISON
        assert SystemPromptGenerator.detect_query_type("Which is better: Python or JavaScript?") == QueryType.COMPARISON

    def test_detect_analytical_query(self):
        """Test detection of analytical queries."""
        assert SystemPromptGenerator.detect_query_type("Why is TypeScript popular?") == QueryType.ANALYTICAL
        assert SystemPromptGenerator.detect_query_type("Analyze the impact of AI") == QueryType.ANALYTICAL
        assert SystemPromptGenerator.detect_query_type("What are the implications of quantum computing?") == QueryType.ANALYTICAL
        assert SystemPromptGenerator.detect_query_type("Evaluate the pros and cons") == QueryType.ANALYTICAL

    def test_detect_temporal_query(self):
        """Test detection of temporal/recent queries."""
        assert SystemPromptGenerator.detect_query_type("Latest Python releases") == QueryType.TEMPORAL
        assert SystemPromptGenerator.detect_query_type("Recent developments in AI") == QueryType.TEMPORAL
        assert SystemPromptGenerator.detect_query_type("Current state of blockchain") == QueryType.TEMPORAL
        assert SystemPromptGenerator.detect_query_type("Updates in 2024") == QueryType.TEMPORAL

    def test_detect_exploratory_query(self):
        """Test detection of exploratory/open-ended queries."""
        assert SystemPromptGenerator.detect_query_type("Tell me about machine learning") == QueryType.EXPLORATORY
        assert SystemPromptGenerator.detect_query_type("Explore the benefits of microservices") == QueryType.EXPLORATORY
        assert SystemPromptGenerator.detect_query_type("Overview of cloud computing") == QueryType.EXPLORATORY
        assert SystemPromptGenerator.detect_query_type("Discuss the future of AI") == QueryType.EXPLORATORY

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        assert SystemPromptGenerator.detect_query_type("WHAT IS AI?") == QueryType.FACTUAL
        assert SystemPromptGenerator.detect_query_type("how to deploy docker?") == QueryType.HOW_TO
        assert SystemPromptGenerator.detect_query_type("RusT Vs Go") == QueryType.COMPARISON


@pytest.mark.unit
@pytest.mark.fast
class TestQueryDomainDetection:
    """Test domain detection from keywords."""

    def test_detect_technology_domain(self):
        """Test detection of technology domain."""
        assert SystemPromptGenerator.detect_domain("Python programming language") == QueryDomain.TECHNOLOGY
        assert SystemPromptGenerator.detect_domain("Docker container deployment") == QueryDomain.TECHNOLOGY
        assert SystemPromptGenerator.detect_domain("API design patterns") == QueryDomain.TECHNOLOGY
        assert SystemPromptGenerator.detect_domain("Software engineering best practices") == QueryDomain.TECHNOLOGY

    def test_detect_science_domain(self):
        """Test detection of science domain."""
        assert SystemPromptGenerator.detect_domain("Quantum physics principles") == QueryDomain.SCIENCE
        assert SystemPromptGenerator.detect_domain("Neural networks research") == QueryDomain.SCIENCE
        assert SystemPromptGenerator.detect_domain("Biology experiments") == QueryDomain.SCIENCE
        assert SystemPromptGenerator.detect_domain("Chemical reactions") == QueryDomain.SCIENCE

    def test_detect_business_domain(self):
        """Test detection of business domain."""
        assert SystemPromptGenerator.detect_domain("Market trends analysis") == QueryDomain.BUSINESS
        assert SystemPromptGenerator.detect_domain("Startup funding strategies") == QueryDomain.BUSINESS
        assert SystemPromptGenerator.detect_domain("Marketing campaigns") == QueryDomain.BUSINESS
        assert SystemPromptGenerator.detect_domain("Investment portfolio") == QueryDomain.BUSINESS

    def test_detect_medical_domain(self):
        """Test detection of medical domain."""
        assert SystemPromptGenerator.detect_domain("Healthcare treatments") == QueryDomain.MEDICAL
        assert SystemPromptGenerator.detect_domain("Medical diagnosis procedures") == QueryDomain.MEDICAL
        assert SystemPromptGenerator.detect_domain("Patient care guidelines") == QueryDomain.MEDICAL
        assert SystemPromptGenerator.detect_domain("Clinical trials") == QueryDomain.MEDICAL

    def test_detect_academic_domain(self):
        """Test detection of academic domain."""
        assert SystemPromptGenerator.detect_domain("Research methodology") == QueryDomain.ACADEMIC
        assert SystemPromptGenerator.detect_domain("Thesis writing guidelines") == QueryDomain.ACADEMIC
        assert SystemPromptGenerator.detect_domain("Academic publishing") == QueryDomain.ACADEMIC
        assert SystemPromptGenerator.detect_domain("University curriculum") == QueryDomain.ACADEMIC

    def test_detect_general_domain_fallback(self):
        """Test that general domain is used when no specific match."""
        assert SystemPromptGenerator.detect_domain("Tell me about cats") == QueryDomain.GENERAL
        assert SystemPromptGenerator.detect_domain("Random question") == QueryDomain.GENERAL
        assert SystemPromptGenerator.detect_domain("xyz abc def") == QueryDomain.GENERAL

    def test_case_insensitive_domain_detection(self):
        """Test that domain detection is case-insensitive."""
        assert SystemPromptGenerator.detect_domain("PYTHON PROGRAMMING") == QueryDomain.TECHNOLOGY
        assert SystemPromptGenerator.detect_domain("quantum physics") == QueryDomain.SCIENCE


@pytest.mark.unit
@pytest.mark.fast
class TestSystemPromptGeneration:
    """Test system prompt generation."""

    def test_generate_prompt_for_factual_tech_query(self):
        """Test prompt generation for factual technology query."""
        prompt = SystemPromptGenerator.generate(
            query="What is Docker?",
            mode="search"
        )
        
        # Should contain query type instructions
        assert "factual" in prompt.lower() or "accurate" in prompt.lower()
        # Should contain domain context
        assert "technology" in prompt.lower() or "technical" in prompt.lower()
        # Should contain mode-specific instructions
        assert "search" in prompt.lower() or "concise" in prompt.lower()

    def test_generate_prompt_for_howto_query(self):
        """Test prompt generation for how-to query."""
        prompt = SystemPromptGenerator.generate(
            query="How to implement OAuth2?",
            mode="research"
        )
        
        # Should contain how-to instructions
        assert "step" in prompt.lower() or "guide" in prompt.lower() or "how" in prompt.lower()
        # Should contain research mode depth
        assert "detailed" in prompt.lower() or "comprehensive" in prompt.lower()

    def test_generate_prompt_for_comparison_query(self):
        """Test prompt generation for comparison query."""
        prompt = SystemPromptGenerator.generate(
            query="Python vs JavaScript",
            mode="balanced"
        )
        
        # Should contain comparison instructions (compare, comparison, or difference)
        prompt_lower = prompt.lower()
        assert ("compar" in prompt_lower or "difference" in prompt_lower or 
                "versus" in prompt_lower or "pros and cons" in prompt_lower)
        # Should mention both sides
        assert "balanced" in prompt.lower() or "objective" in prompt.lower()

    def test_generate_prompt_includes_citations_instruction(self):
        """Test that all prompts include citation instructions."""
        prompt = SystemPromptGenerator.generate(
            query="What is AI?",
            mode="search"
        )
        
        # Should mention citations or sources
        assert "citation" in prompt.lower() or "source" in prompt.lower() or "reference" in prompt.lower()

    def test_generate_prompt_includes_mode_specific_depth(self):
        """Test that prompts adapt to search mode."""
        search_prompt = SystemPromptGenerator.generate(
            query="What is Docker?",
            mode="search"
        )
        research_prompt = SystemPromptGenerator.generate(
            query="What is Docker?",
            mode="research"
        )
        
        # Research should be longer and more detailed
        assert len(research_prompt) > len(search_prompt)
        assert "detailed" in research_prompt.lower() or "comprehensive" in research_prompt.lower()

    def test_generate_prompt_is_fast(self):
        """Test that prompt generation is fast (<10ms)."""
        import time
        
        start = time.perf_counter()
        for _ in range(100):
            SystemPromptGenerator.generate(
                query="What is the latest in AI research?",
                mode="research"
            )
        elapsed = time.perf_counter() - start
        
        # 100 generations should take less than 1 second (10ms per generation)
        assert elapsed < 1.0, f"Generation too slow: {elapsed*10:.2f}ms per prompt"

    def test_generate_prompt_handles_empty_query(self):
        """Test that generator handles edge cases gracefully."""
        prompt = SystemPromptGenerator.generate(
            query="",
            mode="search"
        )
        
        # Should still return a valid prompt
        assert len(prompt) > 50
        assert "search" in prompt.lower()

    def test_generate_prompt_handles_complex_query(self):
        """Test generator with complex multi-sentence query."""
        prompt = SystemPromptGenerator.generate(
            query="I need to understand how Docker containers work. What are the differences between Docker and VMs? How do I deploy a Python application using Docker?",
            mode="research"
        )
        
        # Should detect multiple aspects
        assert len(prompt) > 100
        # Should handle mixed query types
        assert "detailed" in prompt.lower() or "comprehensive" in prompt.lower()

    def test_different_queries_produce_different_prompts(self):
        """Test that different queries produce contextually different prompts."""
        prompt1 = SystemPromptGenerator.generate(
            query="What is Python?",
            mode="search"
        )
        prompt2 = SystemPromptGenerator.generate(
            query="How to deploy with Docker?",
            mode="search"
        )
        
        # Prompts should be different (not just same template)
        assert prompt1 != prompt2

    def test_same_query_produces_consistent_prompt(self):
        """Test that same query produces consistent prompt."""
        prompt1 = SystemPromptGenerator.generate(
            query="What is Docker?",
            mode="search"
        )
        prompt2 = SystemPromptGenerator.generate(
            query="What is Docker?",
            mode="search"
        )
        
        # Should be identical (deterministic)
        assert prompt1 == prompt2

    def test_generate_prompt_for_temporal_query(self):
        """Test prompt generation for temporal queries."""
        prompt = SystemPromptGenerator.generate(
            query="Latest developments in AI 2024",
            mode="search"
        )
        
        # Should emphasize recency
        assert "recent" in prompt.lower() or "latest" in prompt.lower() or "current" in prompt.lower()

    def test_generate_prompt_for_medical_domain(self):
        """Test prompt generation respects medical domain."""
        prompt = SystemPromptGenerator.generate(
            query="What are symptoms of diabetes?",
            mode="search"
        )
        
        # Should include medical accuracy emphasis
        assert "accurate" in prompt.lower() or "medical" in prompt.lower() or "health" in prompt.lower()
