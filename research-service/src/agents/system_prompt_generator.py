"""System prompt generator using pattern matching (NO LLM).

This module generates dynamic system prompts based on query analysis.
Uses pure logic - no LLM calls, optimized for speed (<10ms).
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Literal


class QueryType(str, Enum):
    """Types of queries based on pattern matching."""
    
    FACTUAL = "factual"          # What, who, when, where questions
    HOW_TO = "how_to"            # How-to, explain, show me
    COMPARISON = "comparison"    # Compare, vs, difference, which is better
    ANALYTICAL = "analytical"    # Why, analyze, evaluate, implications
    TEMPORAL = "temporal"        # Latest, recent, current, updates
    EXPLORATORY = "exploratory"  # Tell me about, overview, discuss


class QueryDomain(str, Enum):
    """Knowledge domains based on keyword matching."""
    
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    BUSINESS = "business"
    MEDICAL = "medical"
    ACADEMIC = "academic"
    GENERAL = "general"


class SystemPromptGenerator:
    """Generate dynamic system prompts using pattern matching.
    
    Features:
    - Pattern-based query type detection (factual, how-to, etc.)
    - Keyword-based domain detection (tech, science, business, etc.)
    - Template-based prompt generation
    - Fast (<10ms) with no LLM calls
    - Mode-aware (search vs research depth)
    
    Example:
        >>> prompt = SystemPromptGenerator.generate(
        ...     query="How do Docker containers work?",
        ...     mode="research"
        ... )
        >>> # Returns detailed prompt for how-to technology query
    """

    # Query type patterns (order matters - more specific first)
    _TYPE_PATTERNS = {
        QueryType.COMPARISON: [
            r'\bvs\.?\b', r'\bversus\b',
            r'\bcompare\b', r'\bcomparison\b',
            r'\bdifference between\b', r'\bdifferent from\b',
            r'\bwhich is better\b', r'\bbetter than\b'
        ],
        QueryType.HOW_TO: [
            r'\bhow (do|to|can)\b', r'\bhow\s+\w+\s+(work|deploy|implement|create|build|setup|install)\b',
            r'\bexplain how\b', r'\bshow me how\b',
            r'\bsteps to\b', r'\bguide to\b'
        ],
        QueryType.ANALYTICAL: [
            r'\bwhy\b', r'\banalyze\b', r'\banalysis\b',
            r'\bevaluate\b', r'\bevaluation\b',
            r'\bimplications?\b', r'\bimpact\b',
            r'\badvantages?\b', r'\bdisadvantages?\b',
            r'\bpros and cons\b'
        ],
        QueryType.TEMPORAL: [
            r'\blatest\b', r'\brecent\b', r'\bcurrent\b',
            r'\bupdates?\b', r'\bnew\b', r'\b20\d{2}\b',  # Years like 2024
            r'\btrends?\b', r'\btoday\b', r'\bnow\b'
        ],
        QueryType.FACTUAL: [
            r'^\s*what (is|are|was|were)\b',
            r'^\s*who (is|are|was|were|invented|created|made|founded)\b',
            r'^\s*when (is|are|was|were|did)\b',
            r'^\s*where (is|are|was|were)\b',
            r'\bdefinition\b', r'\bdefine\b'
        ],
        QueryType.EXPLORATORY: [
            r'\btell me about\b', r'\bexplore\b',
            r'\boverview\b', r'\bintroduction\b',
            r'\bdiscuss\b', r'\bexplain\b'
        ]
    }

    # Domain keywords (lowercase for matching)
    _DOMAIN_KEYWORDS = {
        QueryDomain.TECHNOLOGY: [
            'programming', 'software', 'code', 'api', 'docker', 'kubernetes',
            'python', 'javascript', 'typescript', 'rust', 'go', 'java',
            'framework', 'library', 'database', 'cloud', 'aws', 'azure',
            'deployment', 'ci/cd', 'devops', 'container', 'microservice',
            'frontend', 'backend', 'algorithm', 'data structure'
        ],
        QueryDomain.SCIENCE: [
            'quantum', 'physics', 'chemistry', 'chemical', 'biology', 'neural',
            'research', 'experiment', 'hypothesis', 'theory', 'scientific',
            'molecule', 'atom', 'cell', 'dna', 'evolution', 'astronomy',
            'geology', 'ecology', 'genetics', 'reaction', 'compound'
        ],
        QueryDomain.BUSINESS: [
            'market', 'startup', 'entrepreneur', 'funding', 'investment',
            'revenue', 'profit', 'strategy', 'marketing', 'sales',
            'customer', 'product', 'service', 'business', 'company',
            'finance', 'economics', 'trade', 'industry'
        ],
        QueryDomain.MEDICAL: [
            'health', 'medical', 'healthcare', 'disease', 'treatment',
            'diagnosis', 'symptom', 'patient', 'doctor', 'hospital',
            'medicine', 'clinical', 'therapy', 'surgery', 'pharmaceutical',
            'drug', 'vaccine', 'infection'
        ],
        QueryDomain.ACADEMIC: [
            'research', 'thesis', 'dissertation', 'academic', 'scholar',
            'university', 'study', 'paper', 'journal', 'publication',
            'peer review', 'citation', 'methodology', 'literature review',
            'curriculum', 'education'
        ]
    }

    @classmethod
    def detect_query_type(cls, query: str) -> QueryType:
        """Detect query type using pattern matching.
        
        Args:
            query: User query string
            
        Returns:
            QueryType enum value
            
        Example:
            >>> SystemPromptGenerator.detect_query_type("How to deploy Docker?")
            QueryType.HOW_TO
        """
        query_lower = query.lower()
        
        # Check patterns in priority order
        for query_type, patterns in cls._TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return query_type
        
        # Default to exploratory
        return QueryType.EXPLORATORY

    @classmethod
    def detect_domain(cls, query: str) -> QueryDomain:
        """Detect query domain using keyword matching.
        
        Args:
            query: User query string
            
        Returns:
            QueryDomain enum value
            
        Example:
            >>> SystemPromptGenerator.detect_domain("Python programming")
            QueryDomain.TECHNOLOGY
        """
        query_lower = query.lower()
        
        # Count keyword matches for each domain
        domain_scores = {}
        for domain, keywords in cls._DOMAIN_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            domain_scores[domain] = score
        
        # Return domain with highest score
        max_domain = max(domain_scores, key=domain_scores.get)
        if domain_scores[max_domain] > 0:
            return max_domain
        
        # Default to general
        return QueryDomain.GENERAL

    @classmethod
    def generate(
        cls,
        query: str,
        mode: Literal["search", "research", "balanced"] = "search"
    ) -> str:
        """Generate system prompt based on query analysis.
        
        Args:
            query: User query string
            mode: Search mode (affects response depth)
            
        Returns:
            System prompt string optimized for the query
            
        Example:
            >>> prompt = SystemPromptGenerator.generate(
            ...     query="How to implement OAuth2?",
            ...     mode="research"
            ... )
        """
        query_type = cls.detect_query_type(query)
        domain = cls.detect_domain(query)
        
        # Build prompt from components
        base_role = cls._get_base_role(domain)
        type_instructions = cls._get_type_instructions(query_type)
        mode_instructions = cls._get_mode_instructions(mode)
        citation_instructions = cls._get_citation_instructions()
        
        # Combine into final prompt
        prompt = f"""{base_role}

{type_instructions}

{mode_instructions}

{citation_instructions}"""
        
        return prompt.strip()

    @classmethod
    def _get_base_role(cls, domain: QueryDomain) -> str:
        """Get base role description based on domain."""
        roles = {
            QueryDomain.TECHNOLOGY: "You are a technical expert specializing in software engineering, programming, and technology systems.",
            QueryDomain.SCIENCE: "You are a scientific researcher with deep knowledge across multiple scientific disciplines.",
            QueryDomain.BUSINESS: "You are a business analyst with expertise in market analysis, strategy, and entrepreneurship.",
            QueryDomain.MEDICAL: "You are a medical information specialist providing accurate, evidence-based health information. Always emphasize consulting healthcare professionals for medical decisions.",
            QueryDomain.ACADEMIC: "You are an academic research specialist skilled in scholarly analysis and peer-reviewed sources.",
            QueryDomain.GENERAL: "You are a knowledgeable research assistant providing accurate, well-sourced information."
        }
        return roles.get(domain, roles[QueryDomain.GENERAL])

    @classmethod
    def _get_type_instructions(cls, query_type: QueryType) -> str:
        """Get query-type-specific instructions."""
        instructions = {
            QueryType.FACTUAL: "Provide accurate, factual answers with precise definitions. Focus on verified facts and clear explanations. Cite authoritative sources for all factual claims.",
            
            QueryType.HOW_TO: "Provide clear, step-by-step guidance with practical examples. Break down complex processes into manageable steps. Include code examples, commands, or procedures where relevant. Highlight common pitfalls and best practices.",
            
            QueryType.COMPARISON: "Provide balanced, objective comparisons. Present pros and cons for each option. Use clear criteria for comparison. Avoid bias and acknowledge trade-offs. Include use-case recommendations.",
            
            QueryType.ANALYTICAL: "Provide deep analysis exploring causes, effects, and implications. Consider multiple perspectives and viewpoints. Examine underlying assumptions and reasoning. Support claims with evidence and logical arguments.",
            
            QueryType.TEMPORAL: "Focus on the most recent and current information. Emphasize dates, versions, and timeline context. Highlight recent developments, changes, or updates. Note when information might become outdated.",
            
            QueryType.EXPLORATORY: "Provide comprehensive overview covering key concepts, context, and background. Organize information logically with clear structure. Include relevant examples and real-world applications. Highlight important subtopics for further exploration."
        }
        return instructions.get(query_type, instructions[QueryType.EXPLORATORY])

    @classmethod
    def _get_mode_instructions(cls, mode: str) -> str:
        """Get mode-specific depth instructions."""
        instructions = {
            "search": "Provide concise, focused answers. Prioritize clarity and brevity. Include only the most relevant information. Aim for responses that can be quickly scanned and understood.",
            
            "research": "Provide detailed, comprehensive responses with in-depth analysis. Include background context, related concepts, and nuanced details. Explore multiple angles and perspectives. Provide thorough explanations suitable for deep learning.",
            
            "balanced": "Balance depth with accessibility. Provide sufficient detail for understanding while maintaining readability. Include key details and important context without overwhelming. Structure information for progressive disclosure."
        }
        return instructions.get(mode, instructions["search"])

    @classmethod
    def _get_citation_instructions(cls) -> str:
        """Get citation and sourcing instructions."""
        return """CRITICAL: Support all claims with inline citations using [Source N] format. Every factual statement must reference its source. Provide source URLs and titles in a Sources section at the end. Ensure citations are accurate and verifiable."""
