import pytest
from unittest.mock import MagicMock, patch
from models.router import ModelRouter

@pytest.fixture
def router():
    return ModelRouter()

def test_router_initialization(router):
    assert "thinking" in router.models
    assert "reasoning" in router.models
    assert router.usage_stats["total_cost"] == 0.0

@patch("models.router.Groq")
def test_route_request_success(mock_groq, router):
    # Mock successful API response
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    router.groq_client = mock_client
    router.moonshot_client = mock_client
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Mocked response"))]
    mock_client.chat.completions.create.return_value = mock_response
    
    res = router.route_request("thinking", [{"role": "user", "content": "test"}])
    assert res["success"] is True
    assert res["content"] == "Mocked response"
    assert router.usage_stats["thinking_calls"] == 1

@patch("models.router.Groq")
def test_retry_logic(mock_groq, router):
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    router.groq_client = mock_client
    router.moonshot_client = mock_client
    
    # Sequential side effects: Fail once, then succeed
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Success after retry"))]
    
    mock_client.chat.completions.create.side_effect = [
        Exception("Rate limit"),
        mock_response
    ]
    
    # We need to speed up the retry delay for testing if possible, 
    # but the decorator might use fixed values. 
    # For now, just verify it eventually returns the success
    with patch("time.sleep", return_value=None):
        res = router.route_request("thinking", [{"role": "user", "content": "test"}])
        assert res["success"] is True
        assert res["content"] == "Success after retry"
        assert mock_client.chat.completions.create.call_count == 2
