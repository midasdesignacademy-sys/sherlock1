"""
SHERLOCK Intelligence System - CLI entry point.
"""

import sys
from pathlib import Path
import typer
from rich.console import Console
from loguru import logger

from core.config import settings
from core.graph import run_investigation

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level=settings.LOG_LEVEL,
)
logger.add(settings.LOG_FILE, rotation="10 MB", retention="7 days", level="DEBUG")

app = typer.Typer(help="SHERLOCK Intelligence System")
console = Console()


@app.command()
def investigate(
    docs: str = typer.Option(
        str(settings.UPLOADS_DIR),
        "--docs",
        "-d",
        help="Directory containing documents to analyze",
    ),
    resume: str = typer.Option(None, "--resume", "-r", help="Resume from checkpoint (thread_id)"),
):
    """Run investigation on documents in the given directory. Use --resume <thread_id> to resume."""
    console.print("[bold cyan]SHERLOCK Intelligence System[/bold cyan]")
    if resume:
        console.print(f"Resuming thread: {resume}\n")
        try:
            run_investigation(documents_path=None, thread_id=resume)
            console.print("\n[bold green]Investigation completed.[/bold green]")
        except Exception as e:
            console.print(f"\n[bold red]Failed:[/bold red] {e}")
            raise typer.Exit(1)
        return
    console.print(f"Documents: {docs}\n")
    path = Path(docs)
    if not path.exists():
        console.print(f"[red]Error:[/red] Directory not found: {docs}")
        raise typer.Exit(1)
    if not list(path.glob("*")) or not any(path.iterdir()):
        console.print(f"[yellow]No files in[/yellow] {docs}. Add documents to data/uploads/ and run again.")
        raise typer.Exit(0)
    try:
        run_investigation(documents_path=docs)
        console.print("\n[bold green]Investigation completed.[/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]Failed:[/bold red] {e}")
        logger.exception("Investigation failed")
        raise typer.Exit(1)


@app.command()
def health():
    """Check system health (packages, spaCy, Neo4j, dirs)."""
    console.print("[bold cyan]SHERLOCK Health Check[/bold cyan]\n")
    ok = True
    try:
        import langgraph
        import spacy
        import neo4j
        console.print("  [green]Core packages[/green] OK")
    except ImportError as e:
        console.print(f"  [red]Missing[/red] {e}")
        ok = False
    try:
        import spacy
        spacy.load(settings.SPACY_MODEL_PT)
        console.print(f"  [green]spaCy[/green] {settings.SPACY_MODEL_PT} OK")
    except Exception as e:
        console.print(f"  [red]spaCy[/red] {e}")
        ok = False
    try:
        from knowledge_graph.neo4j_client import Neo4jClient
        c = Neo4jClient()
        c.connect()
        c.close()
        console.print("  [green]Neo4j[/green] OK")
    except Exception as e:
        console.print(f"  [red]Neo4j[/red] {e}. Run: docker-compose up -d")
        ok = False
    for d in [settings.UPLOADS_DIR, settings.REPORTS_DIR]:
        console.print(f"  [green]{d}[/green]" if d.exists() else f"  [red]{d}[/red] missing")
        if not d.exists():
            ok = False
    console.print("\n" + "=" * 50)
    if ok:
        console.print("[bold green]All systems operational.[/bold green]")
    else:
        console.print("[bold red]Some checks failed.[/bold red]")
        raise typer.Exit(1)


@app.command()
def clear():
    """Clear Neo4j graph (use with caution)."""
    if typer.confirm("Clear all graph data?"):
        try:
            from knowledge_graph.neo4j_client import Neo4jClient
            c = Neo4jClient()
            c.connect()
            c.clear_database()
            c.close()
            console.print("[green]Graph cleared.[/green]")
        except Exception as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)


if __name__ == "__main__":
    app()
