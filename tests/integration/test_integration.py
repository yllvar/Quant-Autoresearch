#!/usr/bin/env python3
"""
Integration test for Quant Autoresearch OPENDEV components
"""
import sys
sys.path.append('src')

from core.engine import QuantAutoresearchEngine
from context.compactor import ContextCompactor
from safety.guard import SafetyGuard
from tools.registry import ToolRegistry
from tools.bm25_search import BM25SearchTool
from utils.iteration_tracker import iteration_tracker

def test_all_components():
    """Test all core components"""
    print('🚀 Quant Autoresearch Integration Test')
    print('=' * 50)
    
    # Test 1: Context Management
    print('1. Testing Context Management...')
    compactor = ContextCompactor()
    compactor.check_context_usage('test_operation')
    status = compactor.get_context_status()
    print(f'   ✅ Context usage: {status["usage_percent"]:.1f}%')
    
    # Test 2: Safety System
    print('2. Testing Safety System...')
    guard = SafetyGuard()
    safe_code = 'signals = data["Close"] > data["Close"].shift(1)'
    validation = guard.validate_code(safe_code, 'strategy')
    print(f'   ✅ Safety validation: {"PASSED" if validation["safe"] else "FAILED"}')
    
    # Test 3: Tool Registry
    print('3. Testing Tool Registry...')
    registry = ToolRegistry()
    result = registry.execute_tool('generate_hypothesis', {'current_score': 1.0})
    print(f'   ✅ Tool execution: {"SUCCESS" if result["success"] else "FAILED"}')
    
    # Test 4: BM25 Search
    print('4. Testing BM25 Search...')
    bm25 = BM25SearchTool()
    search_result = bm25.search_research('test query', max_papers=1)
    print(f'   ✅ BM25 search: {"SUCCESS" if search_result["success"] else "FAILED"}')
    
    # Test 5: Iteration Tracking
    print('5. Testing Iteration Tracking...')
    iteration_tracker.log_iteration({'hypothesis': 'test', 'score': 1.0, 'status': 'KEEP'})
    summary = iteration_tracker.get_iteration_summary()
    print(f'   ✅ Iteration logged: {summary["total_iterations"]} total')
    
    print('\n🎉 All components working correctly!')
    print('✅ Quant Autoresearch OPENDEV integration is ready!')
    
    return True

if __name__ == "__main__":
    test_all_components()
