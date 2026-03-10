import pytest
import time
from unittest.mock import MagicMock, patch
from utils.retries import retry_with_backoff

def test_retry_success_first_try():
    mock_func = MagicMock(return_value="success")
    decorator = retry_with_backoff(max_retries=3)
    decorated = decorator(mock_func)
    
    result = decorated()
    assert result == "success"
    assert mock_func.call_count == 1

def test_retry_success_after_failure():
    mock_func = MagicMock()
    mock_func.__name__ = "mock_func"
    mock_func.side_effect = [ValueError("fail"), "success"]
    
    # Mock time.sleep to avoid slow tests
    with patch("time.sleep") as mock_sleep:
        decorator = retry_with_backoff(max_retries=3, initial_delay=1)
        decorated = decorator(mock_func)
        
        result = decorated()
        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_with(1)

def test_retry_max_reached():
    mock_func = MagicMock()
    mock_func.__name__ = "mock_func"
    mock_func.side_effect = ValueError("permanent fail")
    
    with patch("time.sleep"):
        decorator = retry_with_backoff(max_retries=2)
        decorated = decorator(mock_func)
        
        with pytest.raises(ValueError, match="permanent fail"):
            decorated()
        
        # Initial call + 2 retries = 3 calls
        assert mock_func.call_count == 3

def test_retry_specific_exception():
    mock_func = MagicMock()
    mock_func.side_effect = [KeyError("wrong type"), "success"]
    
    decorator = retry_with_backoff(max_retries=3, exceptions=(ValueError,))
    decorated = decorator(mock_func)
    
    # Should raise KeyError immediately because it's not in the exceptions list
    with pytest.raises(KeyError):
        decorated()
    assert mock_func.call_count == 1
