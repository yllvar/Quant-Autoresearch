import pytest
import os
import json
from utils.iteration_tracker import IterationTracker

@pytest.fixture
def tracker(tmp_path):
    log_file = tmp_path / "test_iterations.json"
    return IterationTracker(log_file=str(log_file))

def test_log_iteration(tracker):
    data = {"score": 1.5, "status": "KEEP", "hypothesis": "Test"}
    tracker.log_iteration(data)
    assert len(tracker.iterations) == 1
    assert tracker.iterations[0]["score"] == 1.5
    assert tracker.iterations[0]["iteration_number"] == 1

def test_get_iteration_summary(tracker):
    tracker.log_iteration({"score": 1.0, "status": "KEEP"})
    tracker.log_iteration({"score": 2.0, "status": "DISCARD"})
    
    summary = tracker.get_iteration_summary(last_n=10)
    assert summary["total_iterations"] == 2
    assert summary["average_score"] == 1.5
    assert summary["best_score"] == 2.0
    assert summary["success_rate"] == 0.5

def test_performance_trend(tracker):
    scores = [1.0, 1.1, 1.2, 1.3, 1.4]
    for s in scores:
        tracker.log_iteration({"score": s})
    
    trend = tracker.get_performance_trend(window_size=4)
    assert trend["trend"] == "improving"
    assert trend["improvement"] > 0

def test_session_stats(tracker):
    tracker.log_iteration({"score": 1.0, "status": "KEEP"})
    tracker.log_iteration({"score": 0.5, "status": "CRASH"})
    
    stats = tracker.get_session_stats()
    assert stats["keep_count"] == 1
    assert stats["crash_count"] == 1
    assert stats["total_iterations"] == 2

def test_stagnation_detection(tracker):
    # Stagnating scores
    for _ in range(10):
        tracker.log_iteration({"score": 1.0})
    
    stagnation = tracker.detect_stagnation(window_size=5, threshold=0.1)
    assert stagnation["stagnating"] is True
    
    # Non-stagnating scores
    tracker.log_iteration({"score": 2.0})
    stagnation = tracker.detect_stagnation(window_size=5, threshold=0.1)
    assert stagnation["stagnating"] is False
