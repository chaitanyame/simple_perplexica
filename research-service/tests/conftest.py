"""Pytest configuration for tests."""
# ruff: noqa: E402  # Module imports after sys.path manipulation

import asyncio
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.models import Base

# Test database URL (use same credentials as main DB for now)
# TODO: Create separate test database in future
TEST_DATABASE_URL = (
    "postgresql+asyncpg://research_user:your_secure_password_here@localhost:5432/research_db"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def mock_openrouter_client():
    """Global fixture to mock all OpenRouter API calls."""
    with patch("src.services.llm.openrouter_client.OpenRouterClient") as mock_client_class:
        # Create a mock instance
        mock_instance = MagicMock()

        # Mock async chat method
        mock_chat = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "Mocked response"}}],
                "usage": {"total_tokens": 100},
            }
        )
        mock_instance.chat = mock_chat

        # Make the class return the mock instance
        mock_client_class.return_value = mock_instance

        yield mock_client_class


@pytest.fixture(scope="function", autouse=True)
def prevent_real_api_calls(monkeypatch):
    """Prevent any real API calls during tests."""
    # Mock httpx client to prevent network calls
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Mocked response"}}],
        "usage": {"total_tokens": 100},
    }

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        yield


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_maker = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# Authority Scoring Fixtures


@pytest.fixture
def mock_settings():
    """Create mock settings for authority scoring tests."""
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.ENABLE_AUTHORITY_SCORING = True
    settings.AUTHORITY_SCORING_WEIGHT = 0.15
    settings.AUTHORITY_BOOST_MULTIPLIER = 1.5
    settings.ENABLE_PATTERN_AUTHORITY = True
    settings.ENABLE_WIKIPEDIA_AUTHORITY = True
    settings.WIKIPEDIA_CACHE_TTL = 3600
    return settings


@pytest.fixture
def authority_scorer(mock_settings):
    """Create AuthorityScorer instance with mocked settings."""
    from unittest.mock import patch
    from src.utils.authority_scorer import AuthorityScorer

    with patch("src.utils.authority_scorer.settings", mock_settings):
        scorer = AuthorityScorer()
        yield scorer


@pytest.fixture
def sample_sources():
    """Create sample search sources for testing."""
    from src.agents.search_agent import SearchSource

    return [
        SearchSource(
            url="https://docs.python.org/3/library/asyncio.html",
            title="asyncio — Python Documentation",
            snippet="Official Python asyncio documentation",
            relevance=0.85,
        ),
        SearchSource(
            url="https://stackoverflow.com/questions/12345/asyncio",
            title="How to use asyncio?",
            snippet="StackOverflow Q&A on asyncio",
            relevance=0.90,
        ),
        SearchSource(
            url="https://github.com/python/cpython/blob/main/Lib/asyncio/__init__.py",
            title="CPython asyncio source",
            snippet="Python asyncio source code",
            relevance=0.75,
        ),
        SearchSource(
            url="https://blog.example.com/asyncio-tutorial",
            title="Asyncio Tutorial",
            snippet="Personal blog on asyncio",
            relevance=0.88,
        ),
        SearchSource(
            url="https://arxiv.org/abs/2103.12345",
            title="Research on Async Patterns",
            snippet="Academic paper on async programming",
            relevance=0.80,
        ),
    ]


@pytest.fixture
def realistic_search_sources():
    """Create realistic search sources with diverse domains."""
    from src.agents.search_agent import SearchSource

    return [
        SearchSource(
            url="https://docs.python.org/3/library/asyncio.html",
            title="asyncio — Asynchronous I/O — Python 3.12 documentation",
            snippet="asyncio is used as a foundation for multiple Python asynchronous frameworks...",
            relevance=0.82,
        ),
        SearchSource(
            url="https://stackoverflow.com/questions/37278647/fire-and-forget-python-async-await",
            title="Fire and forget python async/await",
            snippet="Q&A with practical examples of async/await usage...",
            relevance=0.88,
        ),
        SearchSource(
            url="https://realpython.com/async-io-python/",
            title="Async IO in Python: A Complete Walkthrough",
            snippet="Comprehensive tutorial on Python asyncio...",
            relevance=0.90,
        ),
        SearchSource(
            url="https://arxiv.org/abs/2103.12345",
            title="Async Programming Patterns in Modern Python",
            snippet="Academic analysis of async patterns...",
            relevance=0.78,
        ),
        SearchSource(
            url="https://github.com/python/cpython/blob/main/Lib/asyncio/__init__.py",
            title="cpython/Lib/asyncio/__init__.py",
            snippet="Python asyncio implementation source code...",
            relevance=0.75,
        ),
        SearchSource(
            url="https://medium.com/@asyncio_expert/mastering-python-async-abc123",
            title="Mastering Python Async/Await in 2024",
            snippet="Practical guide to async programming...",
            relevance=0.85,
        ),
        SearchSource(
            url="https://techcrunch.com/2024/01/15/python-async-adoption-grows",
            title="Python Async Adoption Grows",
            snippet="Industry news on async adoption...",
            relevance=0.70,
        ),
        SearchSource(
            url="https://myblog.example.com/python-async-tutorial",
            title="My Python Async Tutorial",
            snippet="Personal learning experience with asyncio...",
            relevance=0.80,
        ),
    ]
