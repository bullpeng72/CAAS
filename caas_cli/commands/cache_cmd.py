"""
Cache Management Command

Manage caching system - statistics, clearing, configuration.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    handle_keyboard_interrupt,
)

console = Console()


@click.group(name="cache")
def cache():
    """
    Manage caching system

    \b
    📦 CACHE MANAGEMENT:
    ═══════════════════════════════════════════════════════════════════════════
    • View cache statistics (hit rate, size, entries)
    • Clear cache by type (LLM, validation, all)
    • Configure cache settings (TTL, backend, size limits)

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    View cache statistics:
      $ caas cache stats

    \b
    Clear all cache:
      $ caas cache clear

    \b
    Clear specific cache type:
      $ caas cache clear --type llm
      $ caas cache clear --type validation

    \b
    View cache configuration:
      $ caas cache config

    \b
    Update cache settings:
      $ caas cache config --set default_ttl 7200
      $ caas cache config --set enabled true
    """
    pass


@cache.command(name="stats")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed statistics")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["llm", "validation", "golden_data", "phase_output", "all"]),
    default="all",
    help="Cache type to show statistics for",
)
@handle_keyboard_interrupt
def stats(verbose, type):
    """
    Show cache statistics

    \b
    STATISTICS SHOWN:
    ═══════════════════════════════════════════════════════════════════════════
    • Total entries
    • Cache size (MB)
    • Hit rate (%)
    • Miss rate (%)
    • Average TTL
    • Most accessed keys
    """
    try:
        from caas_framework.caching import get_cache_manager

        cache_manager = get_cache_manager()

        # Get statistics
        stats_data = cache_manager.get_statistics(cache_type=type if type != "all" else None)

        console.print()
        console.print(Panel.fit("[bold cyan]Cache Statistics[/bold cyan]", border_style="cyan"))
        console.print()

        if type == "all":
            # Show all cache types
            for cache_type, cache_stats in stats_data.items():
                _display_cache_stats(cache_type, cache_stats, verbose)
        else:
            # Show specific cache type
            _display_cache_stats(type, stats_data, verbose)

        # Overall summary
        total_entries = (
            sum(s.get("entries", 0) for s in stats_data.values())
            if isinstance(stats_data, dict)
            else stats_data.get("entries", 0)
        )
        total_size = (
            sum(s.get("size_mb", 0) for s in stats_data.values())
            if isinstance(stats_data, dict)
            else stats_data.get("size_mb", 0)
        )

        console.print()
        console.print(
            Panel(
                f"[bold]Total Entries:[/bold] {total_entries}\n"
                f"[bold]Total Size:[/bold] {total_size:.2f} MB",
                title="Overall Summary",
                border_style="green",
            )
        )
        console.print()

    except ImportError as e:
        echo_error(f"Failed to import caching modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Failed to get cache statistics: {e}")
        if verbose:
            import traceback

            echo_error(traceback.format_exc())
        return 1


def _display_cache_stats(cache_type: str, stats: dict, verbose: bool = False):
    """Display statistics for a single cache type"""
    table = Table(title=f"{cache_type.upper()} Cache", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Basic stats
    table.add_row("Entries", str(stats.get("entries", 0)))
    table.add_row("Size (MB)", f"{stats.get('size_mb', 0):.2f}")
    table.add_row("Hit Rate", f"{stats.get('hit_rate', 0):.1f}%")
    table.add_row("Miss Rate", f"{stats.get('miss_rate', 0):.1f}%")
    table.add_row("Avg TTL (s)", str(stats.get("avg_ttl", 0)))

    if verbose:
        table.add_row("Total Hits", str(stats.get("total_hits", 0)))
        table.add_row("Total Misses", str(stats.get("total_misses", 0)))
        table.add_row("Evictions", str(stats.get("evictions", 0)))

    console.print(table)
    console.print()


@cache.command(name="clear")
@click.option(
    "--type",
    "-t",
    type=click.Choice(["llm", "validation", "golden_data", "phase_output", "all"]),
    default="all",
    help="Cache type to clear",
)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@handle_keyboard_interrupt
def clear(type, force):
    """
    Clear cache

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    Clear all cache:
      $ caas cache clear

    Clear specific type:
      $ caas cache clear --type llm
      $ caas cache clear --type validation --force
    """
    try:
        from caas_framework.caching import get_cache_manager

        if not force:
            cache_type_str = type if type != "all" else "all caches"
            if not click.confirm(f"Clear {cache_type_str}?", default=False):
                echo_info("Cancelled")
                return

        cache_manager = get_cache_manager()

        # Clear cache
        if type == "all":
            cleared = cache_manager.clear_all()
        else:
            cleared = cache_manager.clear(cache_type=type)

        echo_success(f"✅ Cleared {cleared} cache entries")

    except ImportError as e:
        echo_error(f"Failed to import caching modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to clear cache: {e}")
        return 1


@cache.command(name="config")
@click.option(
    "--set", "-s", type=(str, str), multiple=True, help="Set cache configuration (key value)"
)
@click.option("--get", "-g", type=str, help="Get specific configuration value")
@handle_keyboard_interrupt
def config(set, get):
    """
    View or modify cache configuration

    \b
    CONFIGURATION OPTIONS:
    ═══════════════════════════════════════════════════════════════════════════
    • enabled          - Enable/disable caching (true/false)
    • backend          - Cache backend (in_memory/file/redis)
    • default_ttl      - Default TTL in seconds
    • max_size_mb      - Maximum cache size in MB
    • max_entries      - Maximum number of entries
    • enable_llm_cache - Enable LLM response caching

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    View current config:
      $ caas cache config

    Get specific value:
      $ caas cache config --get default_ttl

    Set values:
      $ caas cache config --set enabled true
      $ caas cache config --set default_ttl 7200
    """
    try:
        from caas_framework.config import get_settings

        settings = get_settings()
        cache_config = settings.workflow.caching

        if set:
            # Set configuration values
            for key, value in set:
                # Convert string to appropriate type
                if value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)

                if hasattr(cache_config, key):
                    setattr(cache_config, key, value)
                    echo_success(f"Set {key} = {value}")
                else:
                    echo_error(f"Unknown configuration key: {key}")

            # Save settings
            settings.save()
            return

        if get:
            # Get specific value
            if hasattr(cache_config, get):
                value = getattr(cache_config, get)
                click.echo(f"{get}: {value}")
            else:
                echo_error(f"Unknown configuration key: {get}")
            return

        # Display all configuration
        console.print()
        console.print(Panel.fit("[bold cyan]Cache Configuration[/bold cyan]", border_style="cyan"))
        console.print()

        table = Table(border_style="blue")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        config_dict = cache_config.model_dump()
        for key, value in config_dict.items():
            table.add_row(key, str(value))

        console.print(table)
        console.print()

    except ImportError as e:
        echo_error(f"Failed to import configuration modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to manage cache configuration: {e}")
        return 1
