# Phase 3: Advanced Response Quality Features - Architecture & Implementation Roadmap

**Status:** ✅ **DESIGN COMPLETE** | Task 1 Initiated | Tasks 2-7 Ready for Implementation

**Scope:** Optional advanced features (5-7 hours total implementation time)

---

## Executive Summary

Phase 3 adds seven advanced capabilities to further enhance response quality, accessibility, and observability:

1. **Citation Quality Verification** (Task 1) - Grade and reorder citations
2. **Multi-Lingual Adaptation** (Task 2) - Language-specific prompt optimization
3. **Post-Generation Corrections** (Task 3) - Auto-fix low-quality answers
4. **Industry Templates** (Task 4) - Domain-specific response formats
5. **Confidence Scoring** (Task 5) - Per-type quality metrics
6. **Error Recovery** (Task 6) - Graceful degradation strategies
7. **Observability** (Task 7) - Comprehensive monitoring

---

## Complete Architecture

```
[Phase 1 + Phase 2 Foundation]
         |
         v
[Phase 3 Processing Pipeline]
         |
    +----+----+----+----+----+----+----+
    |    |    |    |    |    |    |    |
   T1   T2   T3   T4   T5   T6   T7
   |    |    |    |    |    |    |
   v    v    v    v    v    v    v
[Enhanced Response] -> [Confidence Score] -> [API Output]
```

---

## Task 1: Citation Quality Verification (✅ INITIATED)

### Status
- ✅ Citation model enhanced with `authority_level`, `freshness_score`, `is_direct_quote`
- ✅ Claim model enhanced with `citation_quality_score`, `citation_authority_level`
- ⏳ Methods to implement in ClaimGrounder

### Implementation

**File:** `src/utils/claim_grounder.py`

**Methods to Add:**

```python
def _grade_citation_authority(self, citation: Citation) -> str:
    """Grade citation authority level based on source characteristics.

    Returns: "primary" | "secondary" | "tertiary"
    """
    url_lower = citation.url.lower()

    # Primary (official documentation)
    primary_domains = [
        "docs.microsoft.com", "cloud.google.com", "aws.amazon.com",
        "github.com/official", ".org/docs", "developer.apple.com"
    ]
    if any(domain in url_lower for domain in primary_domains):
        return "primary"

    # Secondary (reputable sources)
    if citation.relevance > 0.8:
        return "secondary"

    # Tertiary (general sources)
    return "tertiary"

async def calculate_citation_quality(
    self, claim: Claim, citations: list[Citation]
) -> float:
    """Calculate overall quality of citations for a claim.

    Returns: 0.0-1.0 score
    """
    if not claim.supporting_sources:
        return 0.0

    quality_scores = []
    for source_id in claim.supporting_sources[:1]:  # Best source
        citation = next((c for c in citations if c.source_id == source_id), None)
        if not citation:
            continue

        # Score components
        relevance_score = citation.relevance  # 0-1
        freshness_score = citation.freshness_score  # 0-1
        authority_multiplier = {
            "primary": 1.2,
            "secondary": 1.0,
            "tertiary": 0.7
        }.get(citation.authority_level, 1.0)

        quality = (relevance_score + freshness_score) / 2 * authority_multiplier
        quality_scores.append(min(quality, 1.0))

    return sum(quality_scores) / len(quality_scores) if quality_scores else 0.5

def _reorder_claims_by_citation_quality(
    self, claims: list[Claim]
) -> list[Claim]:
    """Reorder claims by citation quality (best first)."""
    return sorted(
        claims,
        key=lambda c: (c.citation_quality_score, c.grounding_score),
        reverse=True
    )
```

### Integration in `generate_answer()`:

```python
# After generating answer and running hallucination detection:
# Grade and reorder citations by quality
reordered_claims = claim_grounder._reorder_claims_by_citation_quality(
    grounding_result.claims
)

# Update answer with citation reordering if needed
if reordered_claims != grounding_result.claims:
    logger.info("Reordered citations by quality")
```

---

## Task 2: Multi-Lingual Prompt Adaptation

### Implementation

**File:** `src/agents/search_agent.py`

**Methods to Add:**

```python
def _build_language_specific_instructions(self, language: str) -> str:
    """Build language-specific LLM instructions.

    Args:
        language: Language code (en, es, fr, de)

    Returns:
        Language-adapted instruction string
    """
    language_instructions = {
        "en": """
ENGLISH-SPECIFIC INSTRUCTIONS:
- Use active voice primarily
- Structure: Clear topic sentences, supporting details
- Citations: Author (Year) format
- Numbers: Use commas (1,000; 1.5 million)
- Dates: Month Day, Year format
""",
        "es": """
INSTRUCCIONES ESPECÍFICAS DEL ESPAÑOL:
- Usar voz activa preferentemente
- Estructura: Oraciones temáticas claras, detalles de apoyo
- Citas: Formato Autor (Año)
- Números: Usar puntos (1.000; 1,5 millones)
- Fechas: Formato Día de Mes de Año
""",
        "fr": """
INSTRUCTIONS SPÉCIFIQUES AU FRANÇAIS:
- Utiliser la voix active de préférence
- Structure: Phrases thématiques claires, détails de soutien
- Citations: Format Auteur (Année)
- Nombres: Utiliser des espaces (1 000 ; 1,5 million)
- Dates: Format Jour Mois Année
""",
        "de": """
DEUTSCHSPEZIFISCHE ANWEISUNGEN:
- Aktive Stimme bevorzugt verwenden
- Struktur: Klare Themensätze, unterstützende Details
- Zitate: Autor (Jahr) Format
- Zahlen: Punkte verwenden (1.000; 1,5 Millionen)
- Daten: Datumsformat Tag. Monat Jahr
"""
    }

    return language_instructions.get(language, language_instructions["en"])
```

### Integration in `generate_answer()`:

```python
# After getting sub_queries (which include language detection):
detected_lang = sub_queries[0].language if sub_queries else "en"
language_instructions = self._build_language_specific_instructions(detected_lang)

# Inject into prompt:
prompt = f"""...
{language_instructions}
CONTENT-TYPE ADAPTATION:...
"""
```

---

## Task 3: Post-Generation Answer Corrections

### Implementation

**File:** `src/agents/search_agent.py`

```python
async def _correct_low_quality_answer(
    self,
    answer: str,
    grounding_score: float,
    hallucination_count: int,
    total_claims: int,
) -> tuple[str, bool]:
    """Correct answer if quality metrics are below threshold.

    Returns: (corrected_answer, was_regenerated)
    """
    hallucination_rate = hallucination_count / total_claims if total_claims > 0 else 0

    # Check if regeneration is needed
    if grounding_score < 0.65 and hallucination_rate > 0.25:
        logger.info("Low quality detected, regenerating answer")
        # Regenerate with stricter prompt
        stricter_prompt = prompt + "\n\nIMPORTANT: ONLY include facts directly supported by sources [citations]. Do not speculate."
        new_answer = await self.deps.llm_client.chat(...)
        return new_answer, True

    # Filter unsupported claims if high hallucination rate
    if hallucination_rate > 0.2:
        filtered_answer = self._filter_unsupported_claims(answer, unsupported_claims)
        return filtered_answer, False

    return answer, False
```

---

## Task 4: Industry-Specific Format Templates

### Implementation

```python
def _detect_industry_type(self, query: str, sources: list[SearchSource]) -> str:
    """Detect industry type from query and sources."""

    industry_keywords = {
        "healthcare": ["medical", "health", "disease", "patient", "treatment", "drug"],
        "finance": ["investment", "stock", "fund", "revenue", "earnings", "financial"],
        "legal": ["lawsuit", "legislation", "attorney", "court", "compliance", "regulation"],
        "technology": ["software", "code", "api", "github", "deployment", "infrastructure"],
        "academic": ["research", "study", "paper", "methodology", "hypothesis"]
    }

    combined_text = f"{query} {' '.join(s.title for s in sources)}".lower()

    for industry, keywords in industry_keywords.items():
        matches = sum(1 for kw in keywords if kw in combined_text)
        if matches >= 2:
            return industry

    return "general"

def _get_industry_template(self, industry: str) -> str:
    """Get format template for specific industry."""

    templates = {
        "healthcare": """
HEALTHCARE RESPONSE TEMPLATE:
- Include medical context and patient considerations
- Note contraindications and side effects when applicable
- Distinguish between treatment types (pharmaceutical, surgical, etc.)
- Cite clinical trial data and statistics
- Include qualification: "Consult healthcare providers for medical advice"
""",
        "finance": """
FINANCE RESPONSE TEMPLATE:
- Include risk disclaimers for investment-related content
- Emphasize source authority and time sensitivity
- Compare historical vs current data
- Include performance metrics and returns
- Note: "Past performance does not guarantee future results"
""",
        # ... more templates
    }

    return templates.get(industry, "")
```

---

## Task 5: Response Confidence Scoring

### Implementation

```python
def calculate_response_confidence(
    self,
    grounding_score: float,
    authority_score: float,
    content_type: str,
    hallucination_rate: float,
) -> dict[str, float]:
    """Calculate confidence scores per content type.

    Returns: {
        "overall_confidence": 0.85,
        "academic_confidence": 0.92,  # if academic
        "news_freshness_confidence": 0.78,  # if news
        "technical_accuracy_confidence": 0.88  # if technical
    }
    """

    overall = (grounding_score * 0.5 + authority_score * 0.3 + (1 - hallucination_rate) * 0.2)

    confidence = {"overall_confidence": overall}

    # Type-specific confidence
    if content_type == "academic":
        confidence["academic_confidence"] = min(
            grounding_score * 1.1,  # Academic sources more trustworthy
            1.0
        )
    elif content_type == "news":
        confidence["news_freshness_confidence"] = overall * 0.9  # Freshness matters for news
    elif content_type == "technical":
        confidence["technical_accuracy_confidence"] = overall

    return confidence
```

---

## Task 6: Enhanced Error Recovery

### Implementation

```python
async def _attempt_answer_recovery(
    self,
    answer: str,
    quality_issues: list[str],
    retry_count: int = 1,
) -> tuple[str, bool]:
    """Attempt to recover from quality issues.

    Strategies (in order):
    1. Regenerate with stricter prompt (if grounding low)
    2. Filter out unsupported claims (if hallucination high)
    3. Return partial answer with quality warning (if max retries)
    """

    if "low_grounding" in quality_issues and retry_count < 2:
        return await self._regenerate_with_strict_prompt(answer)

    if "high_hallucination" in quality_issues:
        return self._filter_unsupported_claims(answer), False

    # Max retries reached - return with warning
    logger.warning("Could not improve answer quality after retries")
    return self._append_quality_warning(answer), False
```

---

## Task 7: Observability & Monitoring

### Metrics to Track

```python
# Add to generate_answer() logging:

logger.info(
    "response_metrics",
    grounding_score=grounding_score,
    hallucination_rate=hallucination_count / total_claims,
    citation_quality=average_citation_quality,
    content_type=composition["primary_type"],
    language=detected_language,
    industry_type=detected_industry,
    confidence_score=overall_confidence,
    regeneration_count=regeneration_count,
    execution_time=execution_time
)

# Langfuse integration:
langfuse_trace.update(
    metadata={
        "grounding_score": grounding_score,
        "content_type": composition["primary_type"],
        "language": detected_language,
        "industry": detected_industry,
        "confidence": overall_confidence,
    }
)
```

---

## Implementation Timeline

### Quick Path (2-3 hours)
- ✅ Task 1: Citation Quality Verification
- ✅ Task 2: Multi-Lingual Adaptation
- Task 5: Confidence Scoring (simple)
- Task 7: Basic Observability

### Comprehensive Path (5-7 hours)
- All 7 tasks with full implementations
- Enhanced error recovery strategies
- Complete industry template library
- Comprehensive monitoring dashboards

---

## API Response Example (Phase 3 Complete)

```json
{
  "query": "Compare ML frameworks for production",
  "answer": "TensorFlow provides enterprise-grade ML infrastructure...",
  "confidence": {
    "overall_confidence": 0.89,
    "technical_accuracy_confidence": 0.92,
    "citation_quality_confidence": 0.87
  },
  "metadata": {
    "content_type": "technical",
    "detected_industry": "technology",
    "language": "en",
    "grounding_score": 0.87,
    "hallucination_count": 1,
    "citation_quality_score": 0.91,
    "best_citation_authority": "primary",
    "regeneration_attempts": 0
  },
  "sources": [...]
}
```

---

## Backward Compatibility

✅ **All Phase 3 features are optional**
- New fields have defaults
- Graceful degradation if features unavailable
- No breaking changes to existing API
- Existing Phase 1 & 2 features unaffected

---

## Next Steps

### For Immediate Implementation
1. Use Task 1 template code (Citation Quality)
2. Add Task 2 methods (Multi-Lingual Adaptation)
3. Implement Task 5 (Confidence Scoring)
4. Add Task 7 monitoring

### For Future Enhancement
- Expand industry templates (Task 4)
- Add advanced error recovery (Task 6)
- Integrate post-generation corrections (Task 3)
- Build monitoring dashboards

---

## Testing Strategy

```python
# test_phase3_citation_quality.py
def test_citation_grading():
    """Test citation quality grading"""

def test_language_adaptation():
    """Test language-specific instructions"""

def test_confidence_calculation():
    """Test confidence score calculation"""

def test_error_recovery():
    """Test answer recovery strategies"""
```

---

## Conclusion

Phase 3 adds sophisticated quality assurance, accessibility, and observability features on top of the solid Phase 1 & 2 foundation. Implementation can be done incrementally based on priority:

1. **High Priority:** Tasks 1, 2, 5, 7 (core quality improvements)
2. **Medium Priority:** Task 4 (industry support)
3. **Optional:** Tasks 3, 6 (advanced recovery)

All templates and architecture are provided for straightforward implementation.

---

Generated: November 12, 2025
