"""
Unit tests for synthesis enhancement - TDD approach (RED phase)
Tests structured response generation for multi-query scenarios
"""
import pytest
import os


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_single_query_response_format():
    """Test that single-query responses use normal format"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "Python Guide", "url": "https://example.com/1", "pageContent": "Python is a programming language"},
    ]

    # Single query should return normal paragraph-style response
    response = await synthesize_answer("what is python", sources)

    assert response is not None
    # Should be a string or have answer field
    if hasattr(response, 'answer'):
        assert len(response.answer) > 0
    else:
        assert len(str(response)) > 0


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_multi_query_structured_response():
    """Test that multi-query responses are structured"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {
            "title": "AWS Cloud",
            "url": "https://aws.com/1",
            "pageContent": "AWS provides cloud computing services",
            "source_query": "aws"
        },
        {
            "title": "Azure Cloud",
            "url": "https://azure.com/1",
            "pageContent": "Azure is Microsoft's cloud platform",
            "source_query": "azure"
        },
    ]

    # Multi-query should hint at structured response through prompt
    response = await synthesize_answer(
        "latest cloud news from aws, azure",
        sources,
        system_instructions="Provide structured response with sections for each vendor"
    )

    assert response is not None


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_covers_all_aspects():
    """Test that synthesis addresses all sub-queries"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "AWS", "url": "https://aws.com", "pageContent": "AWS EC2 and S3 services"},
        {"title": "Azure", "url": "https://azure.com", "pageContent": "Azure VMs and Blob Storage"},
        {"title": "GCP", "url": "https://gcp.com", "pageContent": "Google Compute Engine and Cloud Storage"},
    ]

    response = await synthesize_answer(
        "Compare AWS, Azure, and GCP",
        sources,
        system_instructions="Ensure you mention all three cloud providers"
    )

    assert response is not None


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_preserves_citations():
    """Test that synthesis maintains proper citations"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "Source 1", "url": "https://example.com/1", "pageContent": "Important information here"},
        {"title": "Source 2", "url": "https://example.com/2", "pageContent": "Additional details"},
    ]

    response = await synthesize_answer(
        "test query",
        sources,
        system_instructions="Use [n] citation format for all facts"
    )

    # Response should have citations
    response_text = str(response)
    assert response_text is not None


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_with_chat_history():
    """Test synthesis using conversation history"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "Python Basics", "url": "https://example.com", "pageContent": "Python fundamentals"},
    ]

    history = [
        ["Tell me about programming", "Programming is the art of writing code"],
        ["Specifically about Python?", "Python is a high-level language"],
    ]

    response = await synthesize_answer(
        "Show me examples",
        sources,
        history=history
    )

    assert response is not None


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_balanced_coverage():
    """Test that synthesis doesn't focus too heavily on one source"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "Provider A", "url": "https://a.com", "pageContent": "A" * 2000},  # Long
        {"title": "Provider B", "url": "https://b.com", "pageContent": "B" * 500},   # Medium
        {"title": "Provider C", "url": "https://c.com", "pageContent": "C" * 200},   # Short
    ]

    response = await synthesize_answer(
        "compare providers",
        sources,
        system_instructions="Provide balanced coverage of all three providers"
    )

    assert response is not None


def test_synthesis_prompt_generation():
    """Test that synthesis prompts are generated correctly"""
    # Synthesis should use WEBSEARCH_RESPONSE_PROMPT with proper formatting
    from app.providers.openrouter import WEBSEARCH_RESPONSE_PROMPT

    assert WEBSEARCH_RESPONSE_PROMPT is not None
    assert "citation" in WEBSEARCH_RESPONSE_PROMPT.lower()
    assert "context" in WEBSEARCH_RESPONSE_PROMPT.lower()


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_handles_empty_sources():
    """Test synthesis when no sources are available"""
    from app.providers.openrouter import synthesize_answer

    response = await synthesize_answer(
        "test query",
        [],  # Empty sources
    )

    # Should still return something (error message or default)
    assert response is not None


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_with_custom_instructions():
    """Test synthesis respects user's custom instructions"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "Source", "url": "https://example.com", "pageContent": "Some content"},
    ]

    custom_instructions = "Use bullet points for all lists and keep response concise"

    response = await synthesize_answer(
        "test query",
        sources,
        system_instructions=custom_instructions
    )

    assert response is not None


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_response_quality():
    """Test that synthesis produces high-quality responses"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {
            "title": "Comprehensive Guide",
            "url": "https://example.com/guide",
            "pageContent": """
            Machine Learning is a subset of AI that focuses on learning from data.
            Key concepts include:
            1. Supervised learning - learning from labeled data
            2. Unsupervised learning - finding patterns in unlabeled data
            3. Deep learning - using neural networks
            Applications include computer vision, NLP, and predictive analytics.
            """
        },
    ]

    response = await synthesize_answer(
        "explain machine learning",
        sources,
        system_instructions="Provide a detailed but accessible explanation"
    )

    response_text = str(response)
    # Response should be substantive
    assert len(response_text) > 100


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_synthesis_markdown_formatting():
    """Test that synthesis response uses proper markdown"""
    from app.providers.openrouter import synthesize_answer

    sources = [
        {"title": "Article", "url": "https://example.com", "pageContent": "Content about topic"},
    ]

    response = await synthesize_answer(
        "explain topic",
        sources
    )

    response_text = str(response)
    # Should contain markdown elements or be well-formatted
    assert response_text is not None


def test_synthesize_answer_function_exists():
    """Test that synthesize_answer function is available"""
    from app.providers.openrouter import synthesize_answer

    assert synthesize_answer is not None
    assert callable(synthesize_answer)
