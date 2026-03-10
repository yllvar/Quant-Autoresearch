#!/usr/bin/env python3
"""
OPENDEV Enhanced CLI for Quant Autoresearch
"""
import typer
import sys
import os
import asyncio
from typing import Optional
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from core.engine import QuantAutoresearchEngine
from safety.guard import SafetyGuard, SafetyLevel, ApprovalMode
from context.compactor import ContextCompactor
from models.router import model_router
from utils.iteration_tracker import iteration_tracker
from memory.playbook import Playbook
from tools.registry import LazyToolRegistry, SubagentType
from data.connector import DataConnector
from data.preprocessor import prepare_data as prepare_all_data

app = typer.Typer(help="Quant Autoresearch - OPENDEV Autonomous Engine")

@app.command()
def run(
    iterations: int = typer.Option(10, "--iterations", "-i", help="Max research iterations"),
    safety: str = typer.Option("high", "--safety", "-s", help="Safety level: low, medium, high, critical"),
    max_context: int = typer.Option(95, "--max-context", "-c", help="Max context percentage usage"),
    thinking_model: str = typer.Option("llama-3.1-8b-instant", "--think", help="Model for thinking phase"),
    reasoning_model: str = typer.Option("llama-3.3-70b-versatile", "--reason", help="Model for reasoning phase"),
    lazy_tools: bool = typer.Option(True, "--lazy/--no-lazy", help="Enable lazy tool discovery"),
    approval_mode: str = typer.Option("semi", "--approval", help="Approval mode: auto, semi, manual"),
    db: str = typer.Option("experiments/database/playbook.db", "--db", help="Path to playbook database")
):
    """Run the autonomous research loop"""
    typer.echo(f"🚀 Initializing OPENDEV Session...")
    
    engine = QuantAutoresearchEngine(
        safety_level=SafetyLevel(safety.lower()),
        max_context_percent=max_context,
        thinking_model=thinking_model,
        reasoning_model=reasoning_model,
        lazy_tools=lazy_tools,
        approval_mode=ApprovalMode(approval_mode.lower()),
        db_path=db
    )
    
    asyncio.run(engine.run(max_iterations=iterations))

@app.command()
def status():
    """Show OPENDEV system status and metrics"""
    typer.echo("📊 Quant Autoresearch Status")
    typer.echo("=" * 50)
    
    # Context status
    compactor = ContextCompactor()
    context_status = compactor.get_context_status()
    typer.echo(f"🧠 Context Usage: {context_status['usage_percent']:.1f}%")
    typer.echo(f"📝 Context History: {len(context_status['context_history'])} operations")
    
    # Safety status
    guard = SafetyGuard()
    safety_summary = guard.get_safety_summary()
    typer.echo(f"🛡️  Safety Level: {safety_summary['safety_level']}")
    typer.echo(f"🚫 Operations Blocked: {safety_summary['blocked_operations']}")
    
    # Model router status
    model_stats = model_router.get_usage_stats()
    typer.echo(f"🤖 Model Router:")
    typer.echo(f"   - Total calls: {model_stats['calls']['thinking_calls'] + model_stats['calls']['reasoning_calls']}")
    typer.echo(f"   - Total cost: ${model_stats['total_cost']:.4f}")
    
    # Playbook status
    playbook = Playbook()
    playbook_stats = playbook.get_playbook_statistics()
    typer.echo(f"📚 Playbook Patterns: {playbook_stats['total_patterns']}")
    typer.echo("System is ready.")

@app.command()
def report():
    """Generate detailed performance and safety report"""
    typer.echo("📄 Generating OPENDEV Analysis Report...")
    typer.echo("=" * 60)
    
    # Session statistics
    session_stats = iteration_tracker.get_session_stats()
    if "total_iterations" in session_stats and session_stats["total_iterations"] > 0:
        typer.echo(f"📊 SESSION OVERVIEW")
        typer.echo(f"Total Iterations: {session_stats['total_iterations']}")
        typer.echo(f"Success Rate: {session_stats['success_rate']:.1%}")
        typer.echo(f"Best Score: {session_stats['best_score']:.3f}")
        
        # ACC Metrics
        compactor = ContextCompactor()
        acc_stats = compactor.get_acc_statistics()
        typer.echo(f"\n🧠 ACC Metrics:")
        typer.echo(f"   - Stage: {acc_stats['current_status']['acc_stage']}")
        typer.echo(f"   - Compression: {acc_stats['compression_ratio']:.2f}")
        
        # Model stats
        model_stats = model_router.get_usage_stats()
        typer.echo(f"\n🤖 Model Usage:")
        typer.echo(f"   - Thinking: {model_stats['calls']['thinking_calls']}")
        typer.echo(f"   - Reasoning: {model_stats['calls']['reasoning_calls']}")
        typer.echo(f"   - Total Cost: ${model_stats['total_cost']:.4f}")
    else:
        typer.echo("No data available. Run the engine first!")

@app.command()
def fetch(symbol: str, start: str = "2020-01-01"):
    """Fetch market data for a specific symbol"""
    typer.echo(f"📥 Fetching data for {symbol} starting from {start}...")
    connector = DataConnector()
    if connector.fetch_and_cache(symbol, start):
        typer.echo(f"✅ Successfully cached {symbol}")
    else:
        typer.echo(f"❌ Failed to fetch data for {symbol}")

@app.command()
def ingest(file: str, symbol: str):
    """Ingest custom CSV data into the research cache"""
    typer.echo(f"📁 Ingesting {file} as {symbol}...")
    connector = DataConnector()
    if connector.ingest_custom_csv(file, symbol):
        typer.echo(f"✅ Successfully ingested {symbol} from {file}")
    else:
        typer.echo(f"❌ Failed to ingest {file}")

@app.command()
def setup_data():
    """Download default market data symbols (SPY, BTC, etc.)"""
    typer.echo("📊 Preparing default research dataset...")
    prepare_all_data()

@app.command()
def test():
    """Test OPENDEV components"""
    typer.echo("🧪 Testing OPENDEV Components")
    typer.echo("=" * 40)
    
    # 1. Router
    typer.echo("1. Testing Model Router...")
    try:
        res = model_router.thinking_phase({"current_goal": "Test"})
        typer.echo(f"   ✅ Thinking: {res['success']}")
    except Exception as e:
        typer.echo(f"   ❌ Error: {e}")
        
    # 2. Safety
    typer.echo("\n2. Testing Safety Guard...")
    try:
        guard = SafetyGuard()
        res = guard.defense_in_depth_check({"tool_name": "test"}, SubagentType.PLANNER)
        typer.echo(f"   ✅ Safety: {res['safe']}")
    except Exception as e:
        typer.echo(f"   ❌ Error: {e}")

    # 3. Search
    typer.echo("\n3. Testing Search Index...")
    try:
        from core.research import local_bm25_search
        res = local_bm25_search("momentum")
        typer.echo(f"   ✅ BM25: Found {len(res)} papers")
    except Exception as e:
        typer.echo(f"   ❌ Error: {e}")

if __name__ == "__main__":
    app()
