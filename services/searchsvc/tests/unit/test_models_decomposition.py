"""
Unit tests for DecisionOutput model enhancements - TDD approach (RED phase)
Tests multi-query support and SearchStrategy enum
"""
import pytest
from enum import Enum


def test_search_strategy_enum_exists():
    """Test that SearchStrategy enum is defined"""
    from app.models import SearchStrategy

    # Should have single and multi options
    assert hasattr(SearchStrategy, 'single')
    assert hasattr(SearchStrategy, 'multi')

    assert SearchStrategy.single.value == "single"
    assert SearchStrategy.multi.value == "multi"


def test_decision_output_with_single_query():
    """Test DecisionOutput with single query (backward compatibility)"""
    from app.models import DecisionOutput

    # Should accept single query in list
    decision = DecisionOutput(
        need_search=True,
        optimized_queries=["what is python"],
        search_strategy="single",
        links=[]
    )

    assert decision.need_search is True
    assert isinstance(decision.optimized_queries, list)
    assert len(decision.optimized_queries) == 1
    assert decision.optimized_queries[0] == "what is python"
    assert decision.search_strategy == "single"


def test_decision_output_with_multi_queries():
    """Test DecisionOutput with multiple queries (new feature)"""
    from app.models import DecisionOutput

    queries = [
        "AWS cloud latest news",
        "Azure cloud latest news",
        "Google Cloud Platform latest news"
    ]

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=queries,
        search_strategy="multi",
        links=[]
    )

    assert decision.need_search is True
    assert decision.optimized_queries == queries
    assert len(decision.optimized_queries) == 3
    assert decision.search_strategy == "multi"


def test_decision_output_strategy_enum_validation():
    """Test that search_strategy validates against SearchStrategy enum"""
    from app.models import DecisionOutput

    # Valid strategies should work
    for strategy in ["single", "multi"]:
        decision = DecisionOutput(
            need_search=True,
            optimized_queries=["test"],
            search_strategy=strategy,
            links=[]
        )
        assert decision.search_strategy == strategy


def test_decision_output_default_strategy():
    """Test that search_strategy has default value"""
    from app.models import DecisionOutput

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=["test"],
        links=[]
    )

    # Should default to single
    assert decision.search_strategy == "single"


def test_decision_output_empty_queries_list():
    """Test handling of empty queries list"""
    from app.models import DecisionOutput

    # Empty list should be allowed (for edge cases)
    decision = DecisionOutput(
        need_search=False,
        optimized_queries=[],
        search_strategy="single",
        links=[]
    )

    assert decision.optimized_queries == []


def test_decision_output_preserves_links():
    """Test that links array is preserved"""
    from app.models import DecisionOutput

    links = ["https://example.com", "https://example.org"]

    decision = DecisionOutput(
        need_search=False,
        optimized_queries=["summarize"],
        links=links
    )

    assert decision.links == links


def test_decision_output_max_queries():
    """Test DecisionOutput with maximum reasonable number of queries"""
    from app.models import DecisionOutput

    # Should support up to 10+ queries if needed
    queries = [f"query {i}" for i in range(10)]

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=queries,
        search_strategy="multi",
        links=[]
    )

    assert len(decision.optimized_queries) == 10


def test_decision_output_pydantic_validation():
    """Test Pydantic validation of DecisionOutput"""
    from app.models import DecisionOutput
    from pydantic import ValidationError

    # Should require need_search
    with pytest.raises(ValidationError):
        DecisionOutput(
            optimized_queries=["test"],
            links=[]
        )

    # Should require optimized_queries
    with pytest.raises(ValidationError):
        DecisionOutput(
            need_search=True,
            links=[]
        )


def test_decision_output_json_serialization():
    """Test JSON serialization of DecisionOutput"""
    from app.models import DecisionOutput

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=["aws", "azure", "gcp"],
        search_strategy="multi",
        links=[]
    )

    # Should serialize to JSON
    json_data = decision.model_dump()

    assert json_data['need_search'] is True
    assert json_data['optimized_queries'] == ["aws", "azure", "gcp"]
    assert json_data['search_strategy'] == "multi"
    assert json_data['links'] == []


def test_decision_output_from_dict():
    """Test creating DecisionOutput from dictionary"""
    from app.models import DecisionOutput

    data = {
        "need_search": True,
        "optimized_queries": ["aws", "azure"],
        "search_strategy": "multi",
        "links": []
    }

    decision = DecisionOutput(**data)

    assert decision.need_search is True
    assert decision.optimized_queries == ["aws", "azure"]
    assert decision.search_strategy == "multi"


def test_decision_output_with_special_characters():
    """Test DecisionOutput with special characters in queries"""
    from app.models import DecisionOutput

    queries = [
        "What's new in AWS?",
        "Azure & cloud infrastructure",
        "Google Cloud (GCP) news"
    ]

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=queries,
        search_strategy="multi",
        links=[]
    )

    assert decision.optimized_queries == queries


def test_decision_output_with_unicode():
    """Test DecisionOutput with Unicode characters"""
    from app.models import DecisionOutput

    queries = [
        "最新的 AWS 新闻",  # Chinese
        "новости облака",  # Russian
        "Últimas noticias de Azure"  # Spanish
    ]

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=queries,
        search_strategy="multi",
        links=[]
    )

    assert decision.optimized_queries == queries


def test_decision_output_long_queries():
    """Test DecisionOutput with very long query strings"""
    from app.models import DecisionOutput

    long_query = "A" * 1000

    decision = DecisionOutput(
        need_search=True,
        optimized_queries=[long_query],
        search_strategy="single",
        links=[]
    )

    assert decision.optimized_queries[0] == long_query
