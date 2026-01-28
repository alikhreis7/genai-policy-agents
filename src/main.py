"""
Policy Intelligence Engine - CLI Entry Point

This is the main interface for the system. It demonstrates:
- Clean CLI with rich formatting
- Async execution of the agent graph
- Structured output presentation
"""

import asyncio
import sys
import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models.schemas import UserQuery, EngineResponse
from .orchestration.graph import create_workflow


console = Console()


def print_header():
    """Print the application header."""
    console.print()
    console.print(Panel.fit(
        "[bold blue]Enterprise Policy & Decision Intelligence Engine[/bold blue]\n"
        "[dim]Multi-agent GenAI system for policy lookup and decision support[/dim]",
        border_style="blue"
    ))
    console.print()


def print_response(response: EngineResponse):
    """Pretty print the engine response."""
    
    # Intent classification
    intent_table = Table(show_header=False, box=None, padding=(0, 2))
    intent_table.add_column("Label", style="dim")
    intent_table.add_column("Value")
    intent_table.add_row("Intent", f"[cyan]{response.intent.intent.value}[/cyan]")
    intent_table.add_row("Confidence", f"{response.intent.confidence:.0%}")
    intent_table.add_row("Reasoning", response.intent.reasoning[:80] + "..." if len(response.intent.reasoning) > 80 else response.intent.reasoning)
    
    console.print(Panel(intent_table, title="[bold]Intent Classification[/bold]", border_style="cyan"))
    console.print()
    
    # Main answer
    console.print(Panel(
        Markdown(response.answer.answer),
        title="[bold green]Answer[/bold green]",
        subtitle=f"[dim]{response.answer.summary}[/dim]",
        border_style="green"
    ))
    console.print()
    
    # Citations
    if response.answer.citations:
        citations_table = Table(title="Citations", show_lines=True)
        citations_table.add_column("Claim", style="white", max_width=40)
        citations_table.add_column("Source", style="cyan")
        citations_table.add_column("Relevance", style="yellow")
        
        for citation in response.answer.citations[:5]:  # Limit to 5
            citations_table.add_row(
                citation.claim[:40] + "..." if len(citation.claim) > 40 else citation.claim,
                citation.source,
                citation.relevance
            )
        
        console.print(citations_table)
        console.print()
    
    # Confidence
    conf = response.confidence
    conf_color = "green" if conf.overall_confidence > 0.7 else "yellow" if conf.overall_confidence > 0.5 else "red"
    
    conf_table = Table(show_header=False, box=None, padding=(0, 2))
    conf_table.add_column("Metric", style="dim")
    conf_table.add_column("Score")
    conf_table.add_row("Overall", f"[{conf_color}]{conf.overall_confidence:.0%}[/{conf_color}]")
    conf_table.add_row("Grounding", f"{conf.grounding_score:.0%}")
    conf_table.add_row("Coverage", f"{conf.coverage_score:.0%}")
    conf_table.add_row("Consistency", f"{conf.consistency_score:.0%}")
    
    escalation_text = ""
    if conf.requires_escalation:
        escalation_text = f"\n\n[bold red]⚠ ESCALATION RECOMMENDED[/bold red]\n{conf.escalation_reason}"
    
    console.print(Panel(
        conf_table,
        title="[bold]Confidence Assessment[/bold]",
        subtitle=escalation_text if escalation_text else None,
        border_style=conf_color
    ))
    console.print()
    
    # Caveats
    if response.answer.caveats:
        caveats_text = "\n".join(f"• {c}" for c in response.answer.caveats)
        console.print(Panel(caveats_text, title="[bold yellow]Caveats[/bold yellow]", border_style="yellow"))
        console.print()
    
    # Metadata
    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column("", style="dim")
    meta_table.add_column("")
    meta_table.add_row("Processing Time", f"{response.processing_time_ms:.0f}ms")
    meta_table.add_row("Agents Invoked", ", ".join(response.agents_invoked))
    meta_table.add_row("Sources Consulted", str(response.retrieval.total_sources))
    
    console.print(Panel(meta_table, title="[dim]Metadata[/dim]", border_style="dim"))


async def run_query(query_text: str, context: Optional[str] = None) -> EngineResponse:
    """Run a query through the policy engine."""
    
    query = UserQuery(text=query_text, context=context)
    workflow = create_workflow()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        progress.add_task("Processing query through agent pipeline...", total=None)
        response = await workflow.run(query)
    
    return response


def run_interactive():
    """Run in interactive mode."""
    print_header()
    
    console.print("[dim]Enter your policy questions below. Type 'quit' to exit.[/dim]")
    console.print("[dim]Example: Can we store PII in Redis?[/dim]")
    console.print()
    
    while True:
        try:
            query = console.input("[bold blue]Question:[/bold blue] ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                console.print("\n[dim]Goodbye![/dim]")
                break
            
            console.print()
            response = asyncio.run(run_query(query))
            print_response(response)
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


def run_single_query(query: str):
    """Run a single query and exit."""
    print_header()
    
    console.print(f"[bold]Query:[/bold] {query}")
    console.print()
    
    response = asyncio.run(run_query(query))
    print_response(response)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Query provided as argument
        query = " ".join(sys.argv[1:])
        run_single_query(query)
    else:
        # Interactive mode
        run_interactive()


if __name__ == "__main__":
    main()
