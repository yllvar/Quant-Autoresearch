#!/usr/bin/env python3
"""
Quant Autoresearch CLI
"""
import typer
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from data.connector import DataConnector
from data.preprocessor import prepare_data as prepare_all_data

app = typer.Typer(help="Quant Autoresearch")

@app.command()
def run(
    iterations: int = typer.Option(10, "--iterations", "-i", help="Max research iterations"),
    db: str = typer.Option("experiments/database/playbook.db", "--db", help="Path to playbook database")
):
    """Run the autonomous research loop"""
    typer.echo("Run command is not yet available in V2. Use Claude Code directly.")

@app.command()
def status():
    """Show system status"""
    typer.echo("Quant Autoresearch Status")
    typer.echo("=" * 50)
    typer.echo("V2 architecture — status command coming soon.")

@app.command()
def report():
    """Generate detailed performance report"""
    typer.echo("Generating Analysis Report...")
    typer.echo("=" * 60)
    typer.echo("Report command is not yet available in V2.")

@app.command()
def fetch(symbol: str, start: str = "2020-01-01"):
    """Fetch market data for a specific symbol"""
    typer.echo(f"Fetching data for {symbol} starting from {start}...")
    connector = DataConnector()
    if connector.fetch_and_cache(symbol, start):
        typer.echo(f"Successfully cached {symbol}")
    else:
        typer.echo(f"Failed to fetch data for {symbol}")

@app.command()
def ingest(file: str, symbol: str):
    """Ingest custom CSV data into the research cache"""
    typer.echo(f"Ingesting {file} as {symbol}...")
    connector = DataConnector()
    if connector.ingest_custom_csv(file, symbol):
        typer.echo(f"Successfully ingested {symbol} from {file}")
    else:
        typer.echo(f"Failed to ingest {file}")

@app.command()
def setup_data():
    """Download default market data symbols (SPY, BTC, etc.)"""
    typer.echo("Preparing default research dataset...")
    prepare_all_data()

@app.command()
def research(
    query: str = typer.Option(..., "--query", "-q", help="Research query to investigate"),
    web: bool = typer.Option(True, "--web/--no-web", help="Include web search"),
    academic: bool = typer.Option(True, "--academic/--no-academic", help="Include academic search"),
    max_results: int = typer.Option(5, "--max", "-m", help="Max results per source")
):
    """Run research on a topic using web and/or academic sources"""
    typer.echo(f"Researching: {query}")
    typer.echo("=" * 60)

    from core.research import (
        get_research_context,
        search_web,
        get_comprehensive_research_context
    )

    if web and academic:
        typer.echo("Fetching both academic and web sources...\n")
        context = get_comprehensive_research_context(
            query,
            max_papers=max_results,
            max_web_results=max_results,
            include_web=True
        )
        typer.echo(context)
    elif web:
        typer.echo("Fetching web sources...\n")
        results = search_web(query, num_results=max_results)
        if results:
            for i, r in enumerate(results, 1):
                typer.echo(f"**Result {i}**: {r.get('title', 'N/A')}")
                typer.echo(f"   URL: {r.get('url', 'N/A')}")
                typer.echo(f"   Summary: {r.get('snippet', 'N/A')[:200]}...")
                typer.echo()
        else:
            typer.echo("No web results. Configure EXA_API_KEY or SERPAPI_KEY in .env")
    else:
        typer.echo("Fetching academic sources...\n")
        context = get_research_context(query, max_papers=max_results)
        typer.echo(context)

if __name__ == "__main__":
    app()
