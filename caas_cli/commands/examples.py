"""
Examples Command - Browse and Use Requirement Examples

Provides users with a catalog of example requirements to help them get started
quickly with common project types.
"""

from typing import Optional

import click

from caas_cli.utils import echo_error, echo_info, echo_success, echo_warning
from caas_framework.examples.requirement_examples import (
    REQUIREMENT_EXAMPLES,
    Complexity,
    Domain,
    get_example_summary,
    get_examples_by_complexity,
    get_examples_by_domain,
    get_examples_by_tag,
    search_examples,
    suggest_examples,
)


@click.group(name="examples")
def examples_group():
    """
    Browse and use requirement examples

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    • caas examples list                    - List all available examples
    • caas examples show <title>            - Show a specific example
    • caas examples search <query>          - Search examples by keyword
    • caas examples by-domain <domain>      - Filter by domain
    • caas examples by-complexity <level>   - Filter by complexity
    • caas examples stats                   - Show example statistics

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    1️⃣  List all examples:
       $ caas examples list

    2️⃣  Search for specific type:
       $ caas examples search "e-commerce"

    3️⃣  Filter by domain:
       $ caas examples by-domain finance

    4️⃣  Show a specific example:
       $ caas examples show "Simple To-Do List Application"

    5️⃣  View statistics:
       $ caas examples stats
    """
    pass


@examples_group.command(name="list")
@click.option(
    "--domain",
    "-d",
    type=click.Choice([d.value for d in Domain], case_sensitive=False),
    help="Filter by domain",
)
@click.option(
    "--complexity",
    "-c",
    type=click.Choice([c.value for c in Complexity], case_sensitive=False),
    help="Filter by complexity level",
)
@click.option("--tag", "-t", help="Filter by tag")
def list_examples(domain: Optional[str], complexity: Optional[str], tag: Optional[str]):
    """
    List all available requirement examples

    \b
    EXAMPLES:
    • caas examples list
    • caas examples list --domain web_app
    • caas examples list --complexity simple
    • caas examples list --tag api
    """
    # Apply filters
    examples = REQUIREMENT_EXAMPLES

    if domain:
        examples = [ex for ex in examples if ex.domain.value == domain]
    if complexity:
        examples = [ex for ex in examples if ex.complexity.value == complexity]
    if tag:
        examples = get_examples_by_tag(tag)

    if not examples:
        echo_warning("No examples found matching the filters")
        return

    # Display header
    echo_info(f"📚 Requirement Examples ({len(examples)} found)")
    click.echo()

    # Group by complexity
    simple = [ex for ex in examples if ex.complexity == Complexity.SIMPLE]
    moderate = [ex for ex in examples if ex.complexity == Complexity.MODERATE]
    complex_ex = [ex for ex in examples if ex.complexity == Complexity.COMPLEX]

    if simple:
        click.echo(click.style("🟢 SIMPLE", fg="green", bold=True))
        for ex in simple:
            click.echo(f"  • {ex.title}")
            click.echo(f"    Domain: {ex.domain.value} | Tags: {', '.join(ex.tags[:3])}")
        click.echo()

    if moderate:
        click.echo(click.style("🟡 MODERATE", fg="yellow", bold=True))
        for ex in moderate:
            click.echo(f"  • {ex.title}")
            click.echo(f"    Domain: {ex.domain.value} | Tags: {', '.join(ex.tags[:3])}")
        click.echo()

    if complex_ex:
        click.echo(click.style("🔴 COMPLEX", fg="red", bold=True))
        for ex in complex_ex:
            click.echo(f"  • {ex.title}")
            click.echo(f"    Domain: {ex.domain.value} | Tags: {', '.join(ex.tags[:3])}")
        click.echo()

    # Show usage hint
    click.echo(click.style("💡 TIP:", fg="cyan", bold=True))
    click.echo("   Use 'caas examples show <title>' to see full details")
    click.echo("   Or use 'caas generate --example <title>' to use directly")


@examples_group.command(name="show")
@click.argument("title")
def show_example(title: str):
    """
    Show details of a specific example

    \b
    USAGE:
    • caas examples show "Simple To-Do List Application"
    • caas examples show "E-Commerce Product Catalog"
    """
    # Find example by title (case-insensitive partial match)
    title_lower = title.lower()
    matches = [ex for ex in REQUIREMENT_EXAMPLES if title_lower in ex.title.lower()]

    if not matches:
        echo_error(f"No example found matching: {title}")
        echo_info("Use 'caas examples list' to see all available examples")
        return

    if len(matches) > 1:
        echo_warning(f"Multiple matches found for '{title}':")
        for ex in matches:
            click.echo(f"  • {ex.title}")
        echo_info("Please be more specific")
        return

    # Show the example
    example = matches[0]

    click.echo()
    click.echo("=" * 70)
    click.echo(click.style(f"  {example.title}", fg="cyan", bold=True))
    click.echo("=" * 70)
    click.echo()

    # Metadata
    click.echo(click.style("📋 METADATA", bold=True))
    click.echo(f"   Domain: {click.style(example.domain.value, fg='blue')}")
    complexity_color = {
        Complexity.SIMPLE: "green",
        Complexity.MODERATE: "yellow",
        Complexity.COMPLEX: "red",
    }
    click.echo(
        f"   Complexity: {click.style(example.complexity.value, fg=complexity_color[example.complexity])}"
    )
    click.echo(f"   Tags: {', '.join(example.tags)}")
    click.echo()

    # Description
    click.echo(click.style("📝 DESCRIPTION", bold=True))
    click.echo(f"   {example.description}")
    click.echo()

    # Requirement text
    click.echo(click.style("🎯 EXAMPLE REQUIREMENT", bold=True))
    click.echo()
    for line in example.requirement_text.split("\n"):
        click.echo(f"   {line}")
    click.echo()

    # Key features
    click.echo(click.style("✨ KEY FEATURES", bold=True))
    for feature in example.key_features:
        click.echo(f"   • {feature}")
    click.echo()

    # Usage instructions
    click.echo("=" * 70)
    click.echo(click.style("🚀 HOW TO USE THIS EXAMPLE", fg="green", bold=True))
    click.echo("=" * 70)
    click.echo()
    click.echo("Option 1: Copy and customize the requirement")
    click.echo(f'   $ caas generate "{example.requirement_text[:60]}..."')
    click.echo()
    click.echo("Option 2: Use as a template (coming soon)")
    click.echo(f'   $ caas generate --example "{example.title}"')
    click.echo()


@examples_group.command(name="search")
@click.argument("query")
@click.option("--limit", "-n", type=int, default=10, help="Maximum number of results (default: 10)")
def search_examples_cmd(query: str, limit: int):
    """
    Search examples by keyword

    \b
    USAGE:
    • caas examples search api
    • caas examples search "e-commerce"
    • caas examples search chatbot --limit 5
    """
    results = search_examples(query)

    if not results:
        echo_warning(f"No examples found for: {query}")
        echo_info("Try different keywords or use 'caas examples list' to browse all")
        return

    # Limit results
    results = results[:limit]

    echo_success(f"Found {len(results)} example(s) matching '{query}'")
    click.echo()

    for i, ex in enumerate(results, 1):
        complexity_emoji = {
            Complexity.SIMPLE: "🟢",
            Complexity.MODERATE: "🟡",
            Complexity.COMPLEX: "🔴",
        }

        click.echo(f"{i}. {complexity_emoji[ex.complexity]} {click.style(ex.title, bold=True)}")
        click.echo(f"   {ex.description}")
        click.echo(f"   Domain: {ex.domain.value} | Tags: {', '.join(ex.tags[:3])}")
        click.echo()

    echo_info("Use 'caas examples show <title>' to see full details")


@examples_group.command(name="by-domain")
@click.argument("domain", type=click.Choice([d.value for d in Domain], case_sensitive=False))
def filter_by_domain(domain: str):
    """
    Filter examples by domain

    \b
    AVAILABLE DOMAINS:
    • web_app              - Web applications
    • api                  - REST APIs and services
    • data_analysis        - Data processing and analytics
    • automation           - Automation scripts and workflows
    • chatbot              - Conversational interfaces
    • content_management   - CMS and content platforms
    • e_commerce           - Shopping and payments
    • finance              - Financial and trading systems
    • healthcare           - Medical and health records
    • education            - Learning management systems

    \b
    USAGE:
    • caas examples by-domain web_app
    • caas examples by-domain finance
    """
    domain_enum = Domain(domain)
    examples = get_examples_by_domain(domain_enum)

    if not examples:
        echo_warning(f"No examples found for domain: {domain}")
        return

    echo_info(f"📁 {domain.upper()} Examples ({len(examples)} found)")
    click.echo()

    for ex in examples:
        complexity_emoji = {
            Complexity.SIMPLE: "🟢",
            Complexity.MODERATE: "🟡",
            Complexity.COMPLEX: "🔴",
        }

        click.echo(f"  {complexity_emoji[ex.complexity]} {ex.title}")
        click.echo(f"     {ex.description}")
        click.echo()

    echo_info("Use 'caas examples show <title>' to see full details")


@examples_group.command(name="by-complexity")
@click.argument(
    "complexity", type=click.Choice([c.value for c in Complexity], case_sensitive=False)
)
def filter_by_complexity(complexity: str):
    """
    Filter examples by complexity level

    \b
    COMPLEXITY LEVELS:
    • simple    - Quick projects, 2-3 agents, basic features
    • moderate  - Medium projects, 4-6 agents, multiple features
    • complex   - Large projects, 7+ agents, advanced features

    \b
    USAGE:
    • caas examples by-complexity simple
    • caas examples by-complexity complex
    """
    complexity_enum = Complexity(complexity)
    examples = get_examples_by_complexity(complexity_enum)

    if not examples:
        echo_warning(f"No examples found for complexity: {complexity}")
        return

    complexity_emoji = {
        Complexity.SIMPLE: "🟢",
        Complexity.MODERATE: "🟡",
        Complexity.COMPLEX: "🔴",
    }

    echo_info(
        f"{complexity_emoji[complexity_enum]} {complexity.upper()} Examples ({len(examples)} found)"
    )
    click.echo()

    for ex in examples:
        click.echo(f"  • {ex.title}")
        click.echo(f"    Domain: {ex.domain.value} | {ex.description}")
        click.echo()

    echo_info("Use 'caas examples show <title>' to see full details")


@examples_group.command(name="stats")
def show_stats():
    """
    Show example statistics

    \b
    USAGE:
    • caas examples stats
    """
    summary = get_example_summary()

    click.echo()
    click.echo("=" * 70)
    click.echo(click.style("  📊 Example Statistics", fg="cyan", bold=True))
    click.echo("=" * 70)
    click.echo()

    click.echo(click.style(f"Total Examples: {summary['total']}", bold=True))
    click.echo()

    # By domain
    click.echo(click.style("📁 BY DOMAIN", bold=True))
    for domain, count in summary["by_domain"].items():
        if count > 0:
            bar = "█" * count
            click.echo(f"   {domain:20} {bar} {count}")
    click.echo()

    # By complexity
    click.echo(click.style("📈 BY COMPLEXITY", bold=True))
    complexity_emojis = {"simple": "🟢", "moderate": "🟡", "complex": "🔴"}
    for complexity, count in summary["by_complexity"].items():
        if count > 0:
            emoji = complexity_emojis.get(complexity, "⚪")
            bar = "█" * count
            click.echo(f"   {emoji} {complexity:15} {bar} {count}")
    click.echo()

    click.echo("=" * 70)
    echo_info("Use 'caas examples list' to browse all examples")


@examples_group.command(name="suggest")
@click.argument("keywords", nargs=-1, required=True)
@click.option(
    "--limit", "-n", type=int, default=3, help="Maximum number of suggestions (default: 3)"
)
def suggest_examples_cmd(keywords: tuple, limit: int):
    """
    Get suggestions based on keywords

    \b
    USAGE:
    • caas examples suggest todo task management
    • caas examples suggest api rest backend
    • caas examples suggest learning education --limit 5
    """
    query = " ".join(keywords)
    suggestions = suggest_examples(query, limit=limit)

    if not suggestions:
        echo_warning(f"No suggestions found for: {query}")
        echo_info("Try different keywords or use 'caas examples search'")
        return

    echo_success(f"💡 Suggested examples for '{query}'")
    click.echo()

    for i, ex in enumerate(suggestions, 1):
        complexity_color = {
            Complexity.SIMPLE: "green",
            Complexity.MODERATE: "yellow",
            Complexity.COMPLEX: "red",
        }

        click.echo(f"{i}. {click.style(ex.title, bold=True, fg='cyan')}")
        click.echo(f"   {ex.description}")
        click.echo(
            f"   {click.style(ex.complexity.value.upper(), fg=complexity_color[ex.complexity])} | {ex.domain.value}"
        )
        click.echo()

    echo_info("Use 'caas examples show <title>' to see full details")
