import pytest
import os
import json
import sqlite3
from memory.playbook import Playbook

@pytest.fixture
def playbook(tmp_path):
    db_path = tmp_path / "test_playbook.db"
    return Playbook(db_path=str(db_path))

def test_playbook_initialization(playbook):
    assert os.path.exists(playbook.db_path)
    # Check if tables exist
    with sqlite3.connect(playbook.db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_patterns'")
        assert cursor.fetchone() is not None

def test_store_and_retrieve_pattern(playbook):
    h = "Trend following"
    code = "signals = returns > 0"
    metrics = {"sharpe_ratio": 1.2, "max_drawdown": 0.1, "total_return": 0.2}
    tags = ["trend"]
    
    p_hash = playbook.store_pattern(h, code, metrics, tags)
    assert p_hash is not None
    
    pattern = playbook.get_pattern_by_hash(p_hash)
    assert pattern["hypothesis"] == h
    assert pattern["performance_metrics"]["sharpe_ratio"] == 1.2

def test_find_similar_patterns(playbook):
    playbook.store_pattern("Momentum strategy", "code1", {"sharpe_ratio": 1.1})
    playbook.store_pattern("Mean reversion", "code2", {"sharpe_ratio": 0.9})
    
    # Query for momentum
    results = playbook.find_similar_patterns("momentum", min_similarity=0.1)
    assert len(results) >= 1
    assert "Momentum" in results[0]["hypothesis"]

def test_get_best_patterns(playbook):
    playbook.store_pattern("Good", "code1", {"sharpe_ratio": 2.0, "total_return": 0.3})
    playbook.store_pattern("Bad", "code2", {"sharpe_ratio": 0.1, "total_return": 0.01})
    
    best = playbook.get_best_patterns(metric="sharpe_ratio", min_success_rate=0.0)
    assert best[0]["hypothesis"] == "Good"
    assert best[0]["sharpe_ratio"] == 2.0

def test_update_usage(playbook):
    p_hash = playbook.store_pattern("Test", "code", {"sharpe_ratio": 1.0})
    playbook.update_pattern_usage(p_hash, success=True)
    
    pattern = playbook.get_pattern_by_hash(p_hash)
    assert pattern["usage_count"] == 1
    assert pattern["success_rate"] > 0

def test_import_export(playbook, tmp_path):
    playbook.store_pattern("Export me", "code", {"sharpe_ratio": 1.5})
    export_path = tmp_path / "export.json"
    playbook.export_patterns(str(export_path), min_success_rate=0.1)
    
    # New playbook
    new_db = tmp_path / "new_playbook.db"
    new_playbook = Playbook(db_path=str(new_db))
    new_playbook.import_patterns(str(export_path))
    
    best = new_playbook.get_best_patterns(min_success_rate=0.0)
    assert len(best) == 1
    assert best[0]["hypothesis"] == "Export me"
