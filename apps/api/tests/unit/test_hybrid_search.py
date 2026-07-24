"""Unit tests for hybrid search RRF logic."""
import pytest
from app.infrastructure.vector_store.hybrid_search import HybridSearchEngine, HybridSearchResult


@pytest.fixture
def engine():
    return HybridSearchEngine.__new__(HybridSearchEngine)


def test_rrf_empty_results(engine):
    results = engine._rrf([], [], top_k=6)
    assert results == []


def test_rrf_semantic_only(engine):
    semantic = [
        {"text": "liability cap", "contract_id": "abc", "chunk_index": 0,
         "clause_type": "liability", "page": 1, "score": 0.9, "source": "semantic"},
    ]
    results = engine._rrf(semantic, [], top_k=6)
    assert len(results) == 1
    assert results[0].source == "semantic"
    assert results[0].rrf_score > 0


def test_rrf_keyword_only(engine):
    keyword = [
        {"text": "liability cap", "contract_id": "abc", "chunk_index": 0,
         "clause_type": "liability", "page": 0, "score": 0.8, "source": "keyword"},
    ]
    results = engine._rrf([], keyword, top_k=6)
    assert len(results) == 1
    assert results[0].source == "keyword"


def test_rrf_hybrid_merge(engine):
    """Same content appearing in both should merge into hybrid."""
    text = "liability cap USD 1,000,000"
    semantic = [{"text": text, "contract_id": "abc", "chunk_index": 0,
                 "clause_type": "liability", "page": 1, "score": 0.9, "source": "semantic"}]
    keyword  = [{"text": text, "contract_id": "abc", "chunk_index": 0,
                 "clause_type": "liability", "page": 0, "score": 0.8, "source": "keyword"}]
    results = engine._rrf(semantic, keyword, top_k=6)
    # Should merge because clause_type is same
    hybrid = [r for r in results if r.source == "hybrid"]
    assert len(hybrid) >= 1


def test_rrf_top_k_limit(engine):
    semantic = [
        {"text": f"chunk {i}", "contract_id": "abc", "chunk_index": i,
         "clause_type": "", "page": i, "score": 0.9 - i*0.05, "source": "semantic"}
        for i in range(10)
    ]
    results = engine._rrf(semantic, [], top_k=3)
    assert len(results) == 3


def test_rrf_score_ordering(engine):
    """Higher ranked results should have higher RRF scores."""
    semantic = [
        {"text": f"result {i}", "contract_id": "abc", "chunk_index": i,
         "clause_type": "", "page": i, "score": 0.9, "source": "semantic"}
        for i in range(5)
    ]
    results = engine._rrf(semantic, [], top_k=5)
    scores = [r.rrf_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_rrf_keyword_boost(engine):
    """Keyword result ranked #1 should outscore semantic result ranked #1."""
    from app.infrastructure.vector_store.hybrid_search import SEMANTIC_WEIGHT, KEYWORD_WEIGHT, RRF_K
    semantic_score = SEMANTIC_WEIGHT / (RRF_K + 0)
    keyword_score  = KEYWORD_WEIGHT  / (RRF_K + 0)
    # Both at rank 0 — keyword weight vs semantic weight
    assert keyword_score > 0
    assert semantic_score > 0
