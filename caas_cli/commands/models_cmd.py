"""
Multi-Model Management Command

Manage multi-model router, model selection, and performance tracking.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)

console = Console()


@click.group(name="models")
def models():
    """
    Manage multi-model router

    \b
    🤖 MULTI-MODEL FEATURES:
    ═══════════════════════════════════════════════════════════════════════════
    • List available models
    • View model performance metrics
    • Switch active model
    • Configure routing strategy
    • Model fallback management

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    List available models:
      $ caas models list

    \b
    View model metrics:
      $ caas models metrics
      $ caas models metrics --model gpt-4

    \b
    Switch model:
      $ caas models switch gpt-4
      $ caas models switch claude-3-opus

    \b
    Set routing strategy:
      $ caas models strategy phase_based
      $ caas models strategy cost_optimized
    """
    pass


@models.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed model information")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Filter by provider",
)
@handle_keyboard_interrupt
def list_models(verbose, provider):
    """
    List available LLM models

    \b
    MODEL INFORMATION:
    ═══════════════════════════════════════════════════════════════════════════
    • Model name and provider
    • Cost per 1K tokens
    • Max tokens
    • Suitable phases
    • Current status
    """
    try:
        from caas_framework.config import get_settings
        from caas_framework.plugins.llm import get_multi_model_router

        settings = get_settings()
        router = get_multi_model_router()

        # Get available models
        available_models = router.list_available_models()

        # Filter by provider
        if provider != "all":
            available_models = [m for m in available_models if m["provider"] == provider]

        if not available_models:
            echo_info(f"No models found for provider: {provider}")
            return

        console.print()
        console.print(Panel.fit("[bold cyan]Available LLM Models[/bold cyan]", border_style="cyan"))
        console.print()

        # Create table
        table = Table(border_style="blue")
        table.add_column("Model", style="cyan", width=25)
        table.add_column("Provider", style="green", width=12)
        table.add_column("Cost/1K", style="yellow", width=10)
        table.add_column("Max Tokens", style="magenta", width=12)

        if verbose:
            table.add_column("Suitable Phases", style="blue", width=30)
            table.add_column("Status", style="white", width=10)

        # Add model rows
        current_model = settings.llm.model
        for model in available_models:
            status_mark = "✅" if model["name"] == current_model else ""

            row_data = [
                f"{status_mark} {model['name']}" if status_mark else model["name"],
                model["provider"],
                f"${model.get('cost_per_1k_tokens', 0):.4f}",
                f"{model.get('max_tokens', 0):,}",
            ]

            if verbose:
                phases = ", ".join(model.get("suitable_phases", []))
                row_data.extend([phases if phases else "All", model.get("status", "available")])

            table.add_row(*row_data)

        console.print(table)
        console.print()

        # Show current configuration
        if settings.llm.enable_multi_model:
            echo_info(
                f"Multi-model routing: ✅ Enabled (Strategy: {settings.llm.model_selection_strategy})"
            )
        else:
            echo_info(f"Multi-model routing: ⏸️  Disabled (Current: {current_model})")

        console.print()

    except ImportError as e:
        echo_error(f"Failed to import multi-model modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Failed to list models: {e}")
        if verbose:
            import traceback

            echo_error(traceback.format_exc())
        return 1


@models.command(name="metrics")
@click.option("--model", "-m", type=str, help="Show metrics for specific model")
@click.option(
    "--sort-by",
    "-s",
    type=click.Choice(["cost", "latency", "success_rate", "requests"]),
    default="requests",
    help="Sort models by metric",
)
@handle_keyboard_interrupt
def metrics(model, sort_by):
    """
    View model performance metrics

    \b
    METRICS SHOWN:
    ═══════════════════════════════════════════════════════════════════════════
    • Total requests
    • Success rate
    • Average latency
    • Total cost
    • Consecutive failures
    • Last failure time

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    All models:
      $ caas models metrics

    Specific model:
      $ caas models metrics --model gpt-4

    Sort by cost:
      $ caas models metrics --sort-by cost
    """
    try:
        from caas_framework.plugins.llm import get_multi_model_router

        router = get_multi_model_router()

        # Get metrics
        if model:
            metrics_data = {model: router.get_model_metrics(model)}
        else:
            metrics_data = router.get_all_model_metrics()

        if not metrics_data:
            echo_info("No metrics available")
            return

        console.print()
        console.print(
            Panel.fit("[bold cyan]Model Performance Metrics[/bold cyan]", border_style="cyan")
        )
        console.print()

        # Create table
        table = Table(border_style="blue")
        table.add_column("Model", style="cyan", width=25)
        table.add_column("Requests", style="green", width=12)
        table.add_column("Success Rate", style="yellow", width=14)
        table.add_column("Avg Latency", style="magenta", width=14)
        table.add_column("Total Cost", style="blue", width=12)
        table.add_column("Failures", style="red", width=10)

        # Sort metrics
        sorted_metrics = sorted(
            metrics_data.items(),
            key=lambda x: (
                x[1].get(sort_by, 0)
                if sort_by != "success_rate"
                else x[1].get("successful_requests", 0) / max(x[1].get("total_requests", 1), 1)
            ),
            reverse=True,
        )

        # Add rows
        for model_name, model_metrics in sorted_metrics:
            success_rate = (
                model_metrics.get("successful_requests", 0)
                / max(model_metrics.get("total_requests", 1), 1)
                * 100
            )
            avg_latency = model_metrics.get("total_latency_ms", 0) / max(
                model_metrics.get("total_requests", 1), 1
            )

            table.add_row(
                model_name,
                str(model_metrics.get("total_requests", 0)),
                f"{success_rate:.1f}%",
                f"{avg_latency:.0f}ms",
                f"${model_metrics.get('total_cost_usd', 0):.4f}",
                str(model_metrics.get("consecutive_failures", 0)),
            )

        console.print(table)
        console.print()

        # Show summary
        total_requests = sum(m.get("total_requests", 0) for m in metrics_data.values())
        total_cost = sum(m.get("total_cost_usd", 0) for m in metrics_data.values())

        console.print(
            Panel(
                f"[bold]Total Requests:[/bold] {total_requests}\n"
                f"[bold]Total Cost:[/bold] ${total_cost:.4f}",
                title="Overall Summary",
                border_style="green",
            )
        )
        console.print()

    except ImportError as e:
        echo_error(f"Failed to import multi-model modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to get model metrics: {e}")
        return 1


@models.command(name="switch")
@click.argument("model_name")
@click.option("--provider", "-p", type=str, help="Model provider (optional, auto-detected)")
@handle_keyboard_interrupt
def switch(model_name, provider):
    """
    Switch active LLM model

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    Switch to GPT-4:
      $ caas models switch gpt-4

    Switch to Claude:
      $ caas models switch claude-3-opus --provider anthropic

    Switch to GPT-3.5:
      $ caas models switch gpt-3.5-turbo
    """
    try:
        from caas_framework.config import get_settings

        settings = get_settings()

        # Update model
        old_model = settings.llm.model
        settings.llm.model = model_name

        if provider:
            settings.llm.provider = provider

        # Save settings
        settings.save()

        echo_success(f"✅ Switched model: {old_model} → {model_name}")

        if provider:
            echo_info(f"Provider: {provider}")

    except ImportError as e:
        echo_error(f"Failed to import configuration modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to switch model: {e}")
        return 1


@models.command(name="strategy")
@click.argument(
    "strategy_name",
    type=click.Choice(["phase_based", "cost_optimized", "performance_first", "adaptive"]),
)
@click.option("--enable-multi-model", is_flag=True, help="Enable multi-model routing")
@click.option("--disable-multi-model", is_flag=True, help="Disable multi-model routing")
@handle_keyboard_interrupt
def strategy(strategy_name, enable_multi_model, disable_multi_model):
    """
    Set model selection strategy

    \b
    STRATEGIES:
    ═══════════════════════════════════════════════════════════════════════════
    • phase_based       - Select model based on phase complexity
    • cost_optimized    - Always use cheapest model
    • performance_first - Use fastest/best model
    • adaptive          - Learn from performance history

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    Set strategy:
      $ caas models strategy phase_based

    Enable multi-model:
      $ caas models strategy phase_based --enable-multi-model

    Disable multi-model:
      $ caas models strategy phase_based --disable-multi-model
    """
    try:
        from caas_framework.config import get_settings

        settings = get_settings()

        # Update strategy
        old_strategy = settings.llm.model_selection_strategy
        settings.llm.model_selection_strategy = strategy_name

        # Update multi-model flag
        if enable_multi_model:
            settings.llm.enable_multi_model = True
        elif disable_multi_model:
            settings.llm.enable_multi_model = False

        # Save settings
        settings.save()

        echo_success(f"✅ Model selection strategy updated: {old_strategy} → {strategy_name}")

        if settings.llm.enable_multi_model:
            echo_info("Multi-model routing: ✅ Enabled")
        else:
            echo_warning("Multi-model routing: ⏸️  Disabled")

        # Show strategy description
        console.print()
        strategy_desc = {
            "phase_based": "Models are selected based on phase complexity and requirements",
            "cost_optimized": "Always selects the cheapest available model",
            "performance_first": "Always selects the fastest/best performing model",
            "adaptive": "Learns from performance history and adapts selection",
        }

        console.print(
            Panel(
                f"[bold]{strategy_name.upper()}[/bold]\n\n{strategy_desc.get(strategy_name, '')}",
                title="Strategy Description",
                border_style="blue",
            )
        )
        console.print()

    except ImportError as e:
        echo_error(f"Failed to import configuration modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to set strategy: {e}")
        return 1


@models.command(name="fallback")
@click.option("--enable", is_flag=True, help="Enable fallback")
@click.option("--disable", is_flag=True, help="Disable fallback")
@click.option("--list", "list_chain", is_flag=True, help="List fallback chain")
@handle_keyboard_interrupt
def fallback(enable, disable, list_chain):
    """
    Manage model fallback configuration

    \b
    FALLBACK FEATURES:
    ═══════════════════════════════════════════════════════════════════════════
    • Automatic failover to backup models
    • Configurable fallback chain
    • Failure-based switching

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    Enable fallback:
      $ caas models fallback --enable

    Disable fallback:
      $ caas models fallback --disable

    View fallback chain:
      $ caas models fallback --list
    """
    try:
        from caas_framework.config import get_settings
        from caas_framework.plugins.llm import get_multi_model_router

        settings = get_settings()

        if enable:
            settings.llm.enable_model_fallback = True
            settings.save()
            echo_success("✅ Model fallback enabled")

        elif disable:
            settings.llm.enable_model_fallback = False
            settings.save()
            echo_success("✅ Model fallback disabled")

        elif list_chain:
            router = get_multi_model_router()
            fallback_chain = router.get_fallback_chain()

            console.print()
            console.print(Panel.fit("[bold cyan]Fallback Chain[/bold cyan]", border_style="cyan"))
            console.print()

            table = Table(border_style="blue")
            table.add_column("Priority", style="cyan", width=10)
            table.add_column("Model", style="green", width=25)
            table.add_column("Provider", style="yellow", width=15)
            table.add_column("Status", style="magenta", width=15)

            for i, model in enumerate(fallback_chain, 1):
                table.add_row(
                    str(i),
                    model["name"],
                    model["provider"],
                    "✅ Active" if model.get("active") else "⏸️  Inactive",
                )

            console.print(table)
            console.print()

        else:
            # Show current status
            status = "✅ Enabled" if settings.llm.enable_model_fallback else "❌ Disabled"
            echo_info(f"Model fallback: {status}")

    except ImportError as e:
        echo_error(f"Failed to import multi-model modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to manage fallback: {e}")
        return 1
