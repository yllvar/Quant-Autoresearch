import pytest
from unittest.mock import MagicMock, patch
from context.compactor import ContextCompactor

@pytest.fixture
def compactor():
    with patch("context.compactor.tiktoken") as mock_tik, \
         patch("context.compactor.model_router") as mock_router:
        # Mock encoding to avoid downloading
        mock_enc = MagicMock()
        mock_enc.encode.side_effect = lambda x: [0] * (len(x) // 4)
        mock_tik.get_encoding.return_value = mock_enc
        
        # Mock summarization
        mock_router.summarize_context.return_value = {
            "success": True,
            "content": "Short summary",
            "model_used": "mock-model"
        }
        
        return ContextCompactor(max_context_percent=95)

def test_token_counting(compactor):
    assert compactor.count_tokens("hello world") == 2
    assert compactor.count_tokens("") == 0

def test_acc_stages_logic(compactor):
    # Mock max_tokens to a small value to trigger stages easily
    compactor.max_tokens = 1000
    
    # SAFE Stage
    status = compactor.get_context_status()
    assert status["acc_stage"] == "SAFE"
    
    # Trigger WARNING (>70% and <80%)
    # Use 2900 chars -> 725 tokens -> 72.5%
    compactor.adaptive_context_compaction("op1", {"data": "x" * 2900}) 
    status = compactor.get_context_status()
    assert 70 <= status["usage_percent"] < 80
    assert status["acc_stage"] == "WARNING"
    
    # Trigger MASKING (>80%)
    # Use 3500 chars total -> ~875 tokens + overhead
    compactor.adaptive_context_compaction("op2", {"data": "x" * 600}) 
    status = compactor.get_context_status()
    # It might hit MASKING or PRUNING depending on overhead, just check it progressed
    assert status["acc_stage"] in ["WARNING_MASKING", "CRITICAL_PRUNING"]

def test_mask_old_outputs(compactor):
    compactor.max_tokens = 10000
    # Fill history with 20 items to trigger masking (it expects >15 history items)
    for i in range(20):
        compactor.context_history.append({
            "operation": f"op{i}", 
            "timestamp": "2023-01-01", 
            "tokens": 2000, 
            "data": "x" * 8000
        })
        
    res = compactor._mask_old_outputs()
    assert "Masked" in res
    assert len(compactor.masked_outputs) > 0

def test_aggressive_pruning(compactor):
    compactor.max_tokens = 1000
    for i in range(10):
        compactor.context_history.append({"operation": f"op{i}", "tokens": 200, "data": {}})
    
    res = compactor._aggressive_pruning()
    assert "pruned" in res.lower()
    assert len(compactor.context_history) == 5

def test_llm_summarization(compactor):
    compactor.context_history = [{"operation": "test", "tokens": 100, "data": {}}]
    res = compactor._llm_summarization()
    
    assert "summarized" in res.lower()
    assert len(compactor.summarized_contexts) == 1
    assert compactor.context_history[0]["operation"] == "SUMMARIZED_CONTEXT"

def test_optimize_tool_result(compactor):
    large_result = {"stdout": "a" * 10000, "other": "b" * 10000}
    optimized = compactor.optimize_tool_result(large_result, "test_tool")
    
    assert optimized["_optimized"] is True
    assert len(optimized["stdout"]) < 10000
    assert "[... " in optimized["stdout"]
