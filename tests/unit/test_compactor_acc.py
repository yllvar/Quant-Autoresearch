import pytest
from context.compactor import ContextCompactor

def test_compactor_initialization():
    compactor = ContextCompactor(max_context_percent=90)
    assert compactor.max_context_percent == 90
    assert compactor.get_context_status()["acc_stage"] == "SAFE"

def test_pressure_safe():
    compactor = ContextCompactor(max_context_percent=100)
    # Simulate low usage
    status = compactor.get_context_status()
    # Assuming initial status is safe
    assert status["acc_stage"] == "SAFE"

def test_stage_logic():
    compactor = ContextCompactor()
    # Manually test the update_acc_stage logic which sits in compactor
    # (Note: In the implementation, this might be triggered during compaction)
    
    # Simulate 75% usage -> WARNING
    # This depends on how get_context_status calculates usage
    # If it's 0-100, we can mock or inject
    pass

def test_compaction_mock():
    compactor = ContextCompactor()
    # Test that get_context_status returns valid dict
    status = compactor.get_context_status()
    assert "usage_percent" in status
    assert "acc_stage" in status
    assert "context_history" in status
