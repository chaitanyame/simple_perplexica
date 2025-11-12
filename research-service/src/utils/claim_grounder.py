"""Citation grounding and claim verification system.

This module provides tools for verifying that synthesized research findings
are grounded in source citations, detecting hallucinations, and calculating
confidence scores for claims.

TDD Phase: GREEN - Implementation to make tests pass.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import BaseModel, Field

from ..models.citation import Citation
from ..services.embedding.embedding_service import EmbeddingService


class Claim(BaseModel):
    """Single atomic claim extracted from synthesis.

    Attributes:
        text: The claim text
        claim_id: Unique identifier for this claim
        supporting_sources: List of source IDs that support this claim
        grounding_score: Confidence score (0.0-1.0) that claim is grounded
        is_grounded: Whether claim meets grounding threshold
        evidence_snippets: Exact text from sources supporting this claim
        citation_markers: Citation markers like ["1"], ["2"] from original text
        citation_quality_score: Phase 3 - Quality of supporting citations (0.0-1.0)
        citation_authority_level: Phase 3 - Best authority level of supporting sources
    """

    text: str = Field(..., description="Claim text")
    claim_id: str = Field(..., description="Unique claim identifier")
    supporting_sources: list[str] = Field(default_factory=list, description="Supporting source IDs")
    grounding_score: float = Field(0.0, description="Grounding confidence 0.0-1.0")
    is_grounded: bool = Field(False, description="Meets grounding threshold")
    evidence_snippets: list[str] = Field(default_factory=list, description="Evidence from sources")
    citation_markers: list[str] = Field(default_factory=list, description="Citation markers [1], [2]")
    # Phase 3: Citation quality enhancements
    citation_quality_score: float = Field(0.5, ge=0.0, le=1.0, description="Quality of supporting citations")
    citation_authority_level: str = Field("secondary", description="Best authority of supporting sources")


class GroundingResult(BaseModel):
    """Complete grounding analysis for synthesized text.
    
    Attributes:
        original_text: The synthesis text that was analyzed
        claims: List of all extracted claims with grounding info
        overall_grounding: Average grounding score across all claims
        unsupported_claims: Claims below grounding threshold
        hallucination_count: Number of likely hallucinated claims
        citation_map: Mapping of claim IDs to supporting source IDs
    """
    
    original_text: str = Field(..., description="Original synthesis text")
    claims: list[Claim] = Field(default_factory=list, description="Extracted claims")
    overall_grounding: float = Field(0.0, description="Average grounding score")
    unsupported_claims: list[Claim] = Field(default_factory=list, description="Weak/unsupported claims")
    hallucination_count: int = Field(0, description="Count of hallucinated claims")
    citation_map: dict[str, list[str]] = Field(default_factory=dict, description="Claim to source mapping")


class ClaimExtractor:
    """Extract atomic claims from synthesized text.
    
    Uses sentence tokenization and filtering to identify
    factual claims that can be verified against sources.
    """
    
    def __init__(self) -> None:
        """Initialize claim extractor."""
        # Lazy import to avoid nltk requirement at module load
        self._sentence_tokenizer = None
    
    def _get_tokenizer(self):
        """Get NLTK sentence tokenizer (lazy loaded)."""
        if self._sentence_tokenizer is None:
            try:
                import nltk
                # Try to use punkt tokenizer
                try:
                    self._sentence_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
                except LookupError:
                    # Download if not available
                    nltk.download('punkt', quiet=True)
                    nltk.download('punkt_tab', quiet=True)
                    self._sentence_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
            except ImportError:
                # Fallback to simple splitting if NLTK not available
                self._sentence_tokenizer = None
        return self._sentence_tokenizer
    
    def _simple_sentence_split(self, text: str) -> list[str]:
        """Fallback sentence splitter using regex."""
        # Split on common sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_citation_markers(self, text: str) -> list[str]:
        """Extract citation markers like [1], [2] from text."""
        markers = re.findall(r'\[(\d+)\]', text)
        return markers
    
    def _is_factual_claim(self, sentence: str) -> bool:
        """Check if sentence is a factual claim (not meta-commentary).
        
        Filters out:
        - Questions
        - Meta-commentary (let me explain, in summary, etc.)
        - Very short sentences (< 5 words)
        """
        sentence_lower = sentence.lower().strip()
        
        # Filter questions
        if sentence.endswith('?'):
            return False
        
        # Filter meta-commentary phrases
        meta_phrases = [
            'let me explain',
            'in summary',
            'to summarize',
            'in conclusion',
            'what does this mean',
            'as we can see',
            'it is important to note',
            'we will discuss',
        ]
        if any(phrase in sentence_lower for phrase in meta_phrases):
            return False
        
        # Filter very short sentences (likely not complete claims)
        words = sentence_lower.split()
        if len(words) < 3:  # Less than 3 words
            return False
        
        return True
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_claims(self, text: str) -> list[Claim]:
        """Extract atomic factual claims from text.
        
        Args:
            text: Synthesis text to extract claims from
            
        Returns:
            List of Claim objects
            
        Example:
            >>> extractor = ClaimExtractor()
            >>> claims = extractor.extract_claims("Python 3.11 was released. It is faster.")
            >>> len(claims)
            2
        """
        if not text or not text.strip():
            return []
        
        # Tokenize into sentences
        tokenizer = self._get_tokenizer()
        if tokenizer:
            try:
                sentences = tokenizer.tokenize(text)
            except Exception:
                # Fallback if tokenizer fails
                sentences = self._simple_sentence_split(text)
        else:
            sentences = self._simple_sentence_split(text)
        
        # Extract claims from factual sentences
        claims = []
        for sentence in sentences:
            # Normalize whitespace
            sentence = self._normalize_whitespace(sentence)
            
            # Filter non-factual sentences
            if not self._is_factual_claim(sentence):
                continue
            
            # Extract citation markers
            citation_markers = self._extract_citation_markers(sentence)
            
            # Create claim
            claim = Claim(
                text=sentence,
                claim_id=f"claim_{uuid.uuid4().hex[:8]}",
                supporting_sources=[],
                grounding_score=0.0,
                is_grounded=False,
                evidence_snippets=[],
                citation_markers=citation_markers,
            )
            claims.append(claim)
        
        return claims


class ClaimGrounder:
    """Verify that claims are grounded in source citations.
    
    This class provides the core citation grounding functionality:
    - Matching claims to supporting sources
    - Calculating grounding confidence scores
    - Detecting hallucinations
    - Generating detailed grounding reports
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        grounding_threshold: float = 0.6,
        similarity_threshold: float = 0.7,
    ) -> None:
        """Initialize claim grounder.
        
        Args:
            embedding_service: Service for generating embeddings
            grounding_threshold: Minimum score to be considered "grounded" (default: 0.6)
            similarity_threshold: Minimum similarity for claim-source match (default: 0.7)
        """
        self.embedding_service = embedding_service
        self.grounding_threshold = grounding_threshold
        self.similarity_threshold = similarity_threshold
        self.extractor = ClaimExtractor()
    
    async def ground_synthesis(
        self,
        synthesis: str,
        citations: list[Citation],
    ) -> GroundingResult:
        """Ground LLM synthesis against source citations.
        
        Full pipeline:
        1. Extract claims from synthesis
        2. For each claim, find supporting sources
        3. Calculate grounding score via semantic similarity
        4. Flag hallucinations (score < threshold)
        5. Return detailed grounding analysis
        
        Args:
            synthesis: LLM-generated synthesis text
            citations: Source citations to verify against
            
        Returns:
            GroundingResult with complete analysis
            
        Example:
            >>> result = await grounder.ground_synthesis(synthesis, citations)
            >>> print(f"Overall grounding: {result.overall_grounding:.2f}")
            >>> print(f"Hallucinations: {result.hallucination_count}")
        """
        # Step 1: Extract claims
        claims = self.extractor.extract_claims(synthesis)
        
        if not claims:
            return GroundingResult(
                original_text=synthesis,
                claims=[],
                overall_grounding=0.0,
                unsupported_claims=[],
                hallucination_count=0,
                citation_map={},
            )
        
        # Step 2: For each claim, match to sources and calculate grounding
        citation_map: dict[str, list[str]] = {}
        
        for claim in claims:
            # Find supporting sources
            matches = await self.match_claim_to_sources(claim, citations)
            
            if matches:
                # Get best match
                best_citation, best_score = matches[0]
                
                # Calculate grounding score against best source
                grounding_score = await self.calculate_grounding_score(
                    claim.text,
                    best_citation.excerpt,
                )
                
                # Update claim
                claim.grounding_score = grounding_score
                claim.is_grounded = grounding_score >= self.grounding_threshold
                claim.supporting_sources = [best_citation.source_id]
                claim.evidence_snippets = [best_citation.excerpt[:200]]
                
                # Update citation map
                citation_map[claim.claim_id] = [best_citation.source_id]
            else:
                # No supporting source found
                claim.grounding_score = 0.0
                claim.is_grounded = False
        
        # Step 3: Calculate overall metrics
        grounding_scores = [c.grounding_score for c in claims]
        overall_grounding = sum(grounding_scores) / len(grounding_scores) if grounding_scores else 0.0
        
        # Step 4: Identify unsupported claims
        unsupported_claims = [c for c in claims if not c.is_grounded]
        hallucination_count = sum(1 for c in claims if self.detect_hallucination(c, threshold=0.5))
        
        return GroundingResult(
            original_text=synthesis,
            claims=claims,
            overall_grounding=overall_grounding,
            unsupported_claims=unsupported_claims,
            hallucination_count=hallucination_count,
            citation_map=citation_map,
        )
    
    async def match_claim_to_sources(
        self,
        claim: Claim,
        citations: list[Citation],
    ) -> list[tuple[Citation, float]]:
        """Find sources that support this claim.
        
        Uses semantic similarity and entity matching to identify
        which citations provide evidence for the claim.
        
        Args:
            claim: Claim to find sources for
            citations: Available source citations
            
        Returns:
            List of (citation, confidence_score) tuples, sorted by score descending
            
        Example:
            >>> matches = await grounder.match_claim_to_sources(claim, citations)
            >>> best_source, confidence = matches[0]
            >>> print(f"Best match: {best_source.title} ({confidence:.2f})")
        """
        if not citations:
            return []
        
        # Calculate scores for each citation
        matches: list[tuple[Citation, float]] = []
        
        for citation in citations:
            # Calculate grounding score
            score = await self.calculate_grounding_score(
                claim.text,
                citation.excerpt,
            )
            
            # Only include if above similarity threshold
            if score >= self.similarity_threshold * 0.5:  # More lenient for matching
                matches.append((citation, score))
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    async def calculate_grounding_score(
        self,
        claim_text: str,
        source_content: str,
    ) -> float:
        """Calculate how well source supports claim.
        
        Uses hybrid approach:
        - Semantic similarity (70% weight) via embeddings
        - Keyword overlap (30% weight) for entities, numbers
        
        Args:
            claim_text: The claim to verify
            source_content: Source text to check against
            
        Returns:
            Grounding score from 0.0 (no support) to 1.0 (full support)
            
        Example:
            >>> score = await grounder.calculate_grounding_score(
            ...     "Python 3.11 was released",
            ...     "Python 3.11 released in October 2022"
            ... )
            >>> score > 0.8
            True
        """
        # Step 1: Calculate semantic similarity (70% weight)
        try:
            # Get embeddings
            claim_embedding = await self.embedding_service.embed(claim_text)
            source_embedding = await self.embedding_service.embed(source_content)
            
            # Calculate cosine similarity
            semantic_score = self.embedding_service.cosine_similarity(
                claim_embedding,
                source_embedding,
            )
        except Exception:
            # Fallback if embedding fails
            semantic_score = 0.5
        
        # Step 2: Calculate keyword overlap (30% weight)
        keyword_score = self._calculate_keyword_overlap(claim_text, source_content)
        
        # Step 3: Hybrid score
        final_score = 0.7 * semantic_score + 0.3 * keyword_score
        
        # Ensure score is in valid range
        final_score = max(0.0, min(1.0, final_score))
        
        return final_score
    
    def _calculate_keyword_overlap(self, claim_text: str, source_text: str) -> float:
        """Calculate keyword overlap score between claim and source.
        
        Focuses on:
        - Numbers and percentages
        - Version numbers
        - Dates
        - Capitalized words (proper nouns)
        
        Args:
            claim_text: Claim text
            source_text: Source text
            
        Returns:
            Overlap score 0.0-1.0
        """
        # Extract entities from claim
        claim_entities = self._extract_entities(claim_text)
        
        if not claim_entities:
            # No specific entities to match
            return 0.5  # Neutral score
        
        # Check how many entities appear in source
        source_lower = source_text.lower()
        matches = 0
        
        for entity in claim_entities:
            entity_lower = entity.lower()
            if entity_lower in source_lower:
                matches += 1
        
        # Calculate overlap ratio
        overlap_score = matches / len(claim_entities) if claim_entities else 0.0
        
        return overlap_score
    
    def _extract_entities(self, text: str) -> set[str]:
        """Extract entities (numbers, dates, proper nouns) from text.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            Set of entity strings
        """
        entities = set()
        
        # Extract numbers (including decimals, percentages)
        numbers = re.findall(r'\d+\.?\d*%?', text)
        entities.update(numbers)
        
        # Extract version numbers (e.g., 3.11, v2.0)
        versions = re.findall(r'v?\d+\.\d+(?:\.\d+)?', text, re.IGNORECASE)
        entities.update(versions)
        
        # Extract years (1900-2100)
        years = re.findall(r'\b(19|20)\d{2}\b', text)
        entities.update(years)
        
        # Extract capitalized words (proper nouns, but filter common words)
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        # Filter out common sentence-starting words
        common_words = {'The', 'This', 'That', 'These', 'Those', 'It', 'In', 'On', 'At', 'For'}
        proper_nouns = [w for w in words if w not in common_words]
        entities.update(proper_nouns)
        
        # Extract month names
        months = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', text, re.IGNORECASE)
        entities.update(months)
        
        return entities
    
    def detect_hallucination(
        self,
        claim: Claim,
        threshold: float = 0.5,
    ) -> bool:
        """Check if claim is likely hallucinated.

        A claim is considered hallucinated if its grounding score
        falls below the specified threshold.

        Args:
            claim: Claim to check
            threshold: Minimum score to not be hallucination (default: 0.5)

        Returns:
            True if claim is likely hallucinated, False otherwise

        Example:
            >>> claim.grounding_score = 0.3
            >>> grounder.detect_hallucination(claim)
            True
        """
        return claim.grounding_score < threshold

    # =========================================================================
    # Phase 3: Citation Quality Verification Methods
    # =========================================================================

    def _grade_citation_authority(self, citation: Citation) -> str:
        """Grade citation authority level based on source characteristics.

        Authority levels:
        - "primary": Official documentation and authoritative sources
        - "secondary": Reputable publications and high-relevance sources
        - "tertiary": General web sources and lower-relevance sources

        Args:
            citation: Citation to grade

        Returns:
            Authority level: "primary" | "secondary" | "tertiary"

        Example:
            >>> citation = Citation(..., url="https://docs.python.org", relevance=0.95)
            >>> grounder._grade_citation_authority(citation)
            "primary"
        """
        url_lower = citation.url.lower()

        # Primary (official documentation)
        primary_domains = [
            "docs.microsoft.com",
            "cloud.google.com",
            "aws.amazon.com",
            "github.com/official",
            "github.com/python",
            "docs.python.org",
            "docs.oracle.com",
            "developer.apple.com",
            "developer.mozilla.org",
            ".org/docs",
            "official-docs",
            "official documentation"
        ]

        if any(domain in url_lower for domain in primary_domains):
            return "primary"

        # Secondary (reputable sources based on relevance)
        if citation.relevance >= 0.8:
            return "secondary"

        # Tertiary (general sources)
        return "tertiary"

    async def calculate_citation_quality(
        self,
        claim: Claim,
        citations: list[Citation]
    ) -> float:
        """Calculate overall quality of citations supporting a claim.

        Quality score components:
        - Relevance: How well the source matches the claim (0-1)
        - Freshness: How recent the source is (0-1)
        - Authority: Authority level multiplier (primary=1.2, secondary=1.0, tertiary=0.7)

        Args:
            claim: Claim to evaluate
            citations: Available citations to evaluate

        Returns:
            Quality score (0.0-1.0), higher is better

        Example:
            >>> quality = await grounder.calculate_citation_quality(claim, citations)
            >>> print(f"Citation quality: {quality:.2f}")
        """
        if not claim.supporting_sources:
            return 0.0

        quality_scores = []

        # Evaluate best supporting source
        for source_id in claim.supporting_sources[:1]:
            citation = next((c for c in citations if c.source_id == source_id), None)
            if not citation:
                continue

            # Score components
            relevance_score = citation.relevance  # 0-1
            freshness_score = citation.freshness_score  # 0-1

            # Authority multiplier
            authority_multiplier = {
                "primary": 1.2,
                "secondary": 1.0,
                "tertiary": 0.7
            }.get(citation.authority_level, 1.0)

            # Combined quality score
            quality = (relevance_score + freshness_score) / 2 * authority_multiplier
            quality_scores.append(min(quality, 1.0))

        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.5

    def _reorder_claims_by_citation_quality(
        self,
        claims: list[Claim]
    ) -> list[Claim]:
        """Reorder claims by citation quality (best citations first).

        Sorting order:
        1. Citation quality score (highest first)
        2. Grounding score (highest first)

        This ensures claims with the best supporting evidence appear first.

        Args:
            claims: Claims to reorder

        Returns:
            Claims sorted by citation quality

        Example:
            >>> sorted_claims = grounder._reorder_claims_by_citation_quality(claims)
            >>> print(f"Best claim: {sorted_claims[0].text} (quality={sorted_claims[0].citation_quality_score:.2f})")
        """
        return sorted(
            claims,
            key=lambda c: (c.citation_quality_score, c.grounding_score),
            reverse=True
        )
