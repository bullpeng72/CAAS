"""
CLI command for requirement analysis and story decomposition

Implements CAAS-E Phase 0 story decomposition workflow.
"""

import click
import json
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from caas_framework.methodology.story_decomposer import StoryDecomposer, topological_sort
from caas_framework.config.loader import load_config
from caas_framework.plugins.llm.openai import OpenAIPlugin
from dotenv import load_dotenv
from pathlib import Path as PathLib

# Load .env file
env_paths = [PathLib.cwd() / ".env", PathLib(__file__).parent.parent.parent / ".env"]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

console = Console()


@click.command("analyze-requirement")
@click.argument("requirement", type=str)
@click.option(
    "--output-format",
    type=click.Choice(["story-breakdown", "json", "summary"]),
    default="summary",
    help="Output format (story-breakdown for CAAS-E workflow)"
)
@click.option(
    "--domain",
    type=str,
    default=None,
    help="Domain hint (e.g., e_commerce, healthcare, finance)"
)
@click.option(
    "--max-features-per-story",
    type=int,
    default=5,
    help="Maximum features per story (default: 5, CAAS-E recommended: 3-7)"
)
@click.option(
    "--max-stories",
    type=int,
    default=10,
    help="Maximum stories per epic (default: 10)"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (JSON format)"
)
def analyze_requirement_cmd(
    requirement: str,
    output_format: str,
    domain: str,
    max_features_per_story: int,
    max_stories: int,
    output: str
):
    """
    Analyze requirement and decompose into stories (CAAS-E Phase 0).

    This command implements BMAD-style story decomposition:
    - 1 Epic = 5-10 Stories
    - 1 Story = 3-7 Features
    - Dependency detection
    - Complexity estimation

    Examples:

    \b
    # Story breakdown for epic
    caas analyze-requirement "Build e-commerce platform with product catalog, cart, checkout, and AI recommendations" --output-format story-breakdown

    \b
    # Summary only (quick check)
    caas analyze-requirement "User login system" --output-format summary

    \b
    # Save to file for Phase 0 input
    caas analyze-requirement "Complex system" --output-format json -o epic_breakdown.json

    \b
    # With domain hint
    caas analyze-requirement "Patient management system" --domain healthcare --output-format story-breakdown
    """
    asyncio.run(_analyze_requirement(
        requirement, output_format, domain, max_features_per_story, max_stories, output
    ))


async def _analyze_requirement(
    requirement: str,
    output_format: str,
    domain: str,
    max_features_per_story: int,
    max_stories: int,
    output: str
):
    """Async implementation"""
    # Initialize
    try:
        config = load_config()
        llm = OpenAIPlugin(config=config)
        await llm.initialize()
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize LLM: {e}[/red]")
        console.print("[yellow]💡 Tip: Run 'caas init' and 'caas env --create' first[/yellow]")
        console.print(f"[dim]Error details: {e}[/dim]")
        return

    decomposer = StoryDecomposer(
        llm_plugin=llm,
        max_features_per_story=max_features_per_story,
        max_stories_per_epic=max_stories
    )

    console.print("\n[bold cyan]🔍 Analyzing Requirement...[/bold cyan]")

    # Show requirement preview
    preview = requirement[:200] + ("..." if len(requirement) > 200 else "")
    console.print(f"[dim]Requirement: {preview}[/dim]\n")

    try:
        # Decompose epic
        with console.status("[bold green]Decomposing epic into stories..."):
            epic = await decomposer.decompose_epic(requirement, domain)

        # Output based on format
        if output_format == "story-breakdown":
            _display_story_breakdown(epic)
        elif output_format == "json":
            _display_json(epic)
        elif output_format == "summary":
            _display_summary(epic)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(epic.to_dict(), f, indent=2)

            console.print(f"\n✅ Saved to: [bold]{output_path}[/bold]")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        raise


def _display_story_breakdown(epic):
    """Display story breakdown table (CAAS-E format)"""
    # Epic header
    console.print(Panel(
        f"[bold green]{epic.name}[/bold green]\n\n"
        f"[dim]{epic.description}[/dim]\n\n"
        f"📊 Features: [bold]{epic.estimated_features}[/bold] | "
        f"Stories: [bold]{epic.recommended_stories}[/bold] | "
        f"Value: [bold]{epic.business_value.upper()}[/bold]",
        title="Epic Overview",
        border_style="green"
    ))

    console.print()

    # Stories table
    table = Table(title="Story Breakdown", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Name", style="green", width=30)
    table.add_column("Features", justify="center", width=10)
    table.add_column("Complexity", justify="center", width=12)
    table.add_column("Dependencies", width=20)
    table.add_column("Value", justify="center", width=10)

    for story in epic.stories:
        # Color-code complexity
        complexity_colors = {
            "low": "[green]",
            "medium": "[yellow]",
            "high": "[red]"
        }
        complexity_color = complexity_colors.get(story.estimated_complexity, "")

        # Color-code business value
        value_colors = {
            "low": "[dim]",
            "medium": "[yellow]",
            "high": "[green]"
        }
        value_color = value_colors.get(story.business_value, "")

        table.add_row(
            story.id,
            story.name[:30],
            str(len(story.features)) if story.features else "TBD",
            f"{complexity_color}{story.estimated_complexity}[/]",
            ", ".join(story.dependencies) if story.dependencies else "[dim]-[/dim]",
            f"{value_color}{story.business_value}[/]"
        )

    console.print(table)
    console.print()

    # Recommendation panel
    _display_recommendations(epic)


def _display_recommendations(epic):
    """Display implementation recommendations"""
    recommendation_text = []

    if epic.recommended_stories == 1:
        recommendation_text.append(
            "✅ This requirement is [green]small enough for a single story[/green]."
        )
        recommendation_text.append(
            "   You can proceed directly to Phase 0 (Golden Data generation):\n"
        )
        recommendation_text.append(
            "   [bold]caas generate-phase --phase 0 \"your requirement\"[/bold]"
        )
    else:
        recommendation_text.append(
            f"📦 Implement stories [yellow]iteratively[/yellow] (1 story per sprint)."
        )
        recommendation_text.append(
            "   Start with stories that have [bold]no dependencies[/bold].\n"
        )

        # Show suggested order
        recommendation_text.append("[bold]Suggested Implementation Order:[/bold]")
        ordered_stories = topological_sort(epic.stories)

        for i, story in enumerate(ordered_stories, 1):
            deps_info = ""
            if story.dependencies:
                deps_info = f" [dim](depends on: {', '.join(story.dependencies)})[/dim]"

            recommendation_text.append(f"  {i}. [cyan]{story.id}[/cyan]: {story.name}{deps_info}")

        recommendation_text.append("\n[bold]Next Steps:[/bold]")
        recommendation_text.append(
            f"  1. Start with [cyan]{ordered_stories[0].id}[/cyan] (no dependencies)"
        )
        recommendation_text.append(
            "  2. Run: [bold]caas generate-phase --phase 0 \"story_1 requirement\"[/bold]"
        )
        recommendation_text.append(
            "  3. Complete Phase 0-6 for story_1 before starting story_2"
        )

    console.print(Panel(
        "\n".join(recommendation_text),
        title="💡 CAAS-E Recommendations",
        border_style="yellow"
    ))


def _display_json(epic):
    """Display JSON output"""
    console.print_json(data=epic.to_dict())


def _display_summary(epic):
    """Display summary statistics"""
    summary_lines = [
        f"[bold]Epic:[/bold] {epic.name}",
        f"[bold]Estimated Features:[/bold] {epic.estimated_features}",
        f"[bold]Recommended Stories:[/bold] {epic.recommended_stories}",
        f"[bold]Business Value:[/bold] {epic.business_value.upper()}",
    ]

    if epic.recommended_stories > 1:
        summary_lines.append("")
        summary_lines.append(
            "💡 Use [bold]--output-format story-breakdown[/bold] for detailed story plan."
        )

    console.print(Panel(
        "\n".join(summary_lines),
        title="Epic Summary",
        border_style="cyan"
    ))

    # Quick stats
    if epic.stories:
        console.print("\n[bold]Story Overview:[/bold]")
        for story in epic.stories[:3]:  # Show first 3
            console.print(f"  • {story.id}: {story.name}")

        if len(epic.stories) > 3:
            console.print(f"  [dim]... and {len(epic.stories) - 3} more[/dim]")
