import pytest
from unittest.mock import MagicMock, patch
import sys

# We need to mock research_engine because it's imported at the top level of BM25SearchTool.
# This fixture will run for all tests in this module and restore sys.modules afterward.
@pytest.fixture(scope="module", autouse=True)
def mock_research_engine():
    # Store original if it exists
    original = sys.modules.get("research_engine")
    mock = MagicMock()
    sys.modules["research_engine"] = mock
    yield mock
    # Restore original
    if original:
        sys.modules["research_engine"] = original
    else:
        del sys.modules["research_engine"]

# Now we can import BM25SearchTool
from tools.bm25_search import BM25SearchTool

@pytest.fixture
def bm25_tool():
    return BM25SearchTool()

def test_search_research_success(bm25_tool):
    with patch("tools.bm25_search.get_research_context") as mock_get_context:
        mock_get_context.return_value = "PAPER: Test Paper\nSUMMARY: Test Summary\nURL: http://test.com\n(2023)"
        
        result = bm25_tool.search_research("momentum")
        assert result["success"] is True
        assert result["papers_found"] == 1
        assert result["papers"][0]["title"] == "Test Paper"

def test_search_research_error(bm25_tool):
    with patch("tools.bm25_search.get_research_context") as mock_get_context:
        mock_get_context.side_effect = Exception("Search failed")
        
        result = bm25_tool.search_research("momentum")
        assert result["success"] is False
        assert "Search failed" in result["error"]

def test_parse_research_context(bm25_tool):
    context = """
PAPER: Alpha Generation
SUMMARY: Generating alpha is hard.
URL: http://alpha.com
(Jan 2024)

PAPER: Beta Strategies
SUMMARY: Beta is easy.
URL: http://beta.com
(Feb 2024)
"""
    papers = bm25_tool._parse_research_context(context)
    assert len(papers) == 2
    assert papers[0]["title"] == "Alpha Generation"
    assert papers[1]["published"] == "Feb 2024"

def test_search_similar_strategies(bm25_tool):
    # Mock search_research to avoid calling real research_engine
    with patch.object(bm25_tool, "search_research") as mock_search:
        mock_search.return_value = {
            "success": True,
            "papers": [
                {"title": "Paper 1", "summary": "momentum strategy", "url": "url1"}
            ]
        }
        
        result = bm25_tool.search_similar_strategies("momentum with RSI")
        assert result["success"] is True
        assert len(result["similar_strategies"]) == 1
        assert "Paper 1" in result["similar_strategies"][0]["title"]

def test_get_search_statistics(bm25_tool):
    bm25_tool.search_stats["total_searches"] = 2
    bm25_tool.search_stats["local_hits"] = 1
    
    stats = bm25_tool.get_search_statistics()
    assert stats["total_searches"] == 2
    assert stats["local_hit_rate"] == 0.5
