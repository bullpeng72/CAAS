"""
Monitoring Command

Real-time monitoring, metrics, cost tracking, and alerts.
"""

import time
from datetime import datetime

import click
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
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


@click.group(name="monitor")
def monitor():
    """
    Monitoring and metrics management

    \b
    📊 MONITORING FEATURES:
    ═══════════════════════════════════════════════════════════════════════════
    • Real-time metrics monitoring
    • Cost tracking and analysis
    • Quality metrics tracking
    • Alert management
    • Metric export (Prometheus, JSON)

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    View metrics:
      $ caas monitor metrics

    \b
    Track costs:
      $ caas monitor cost
      $ caas monitor cost --breakdown

    \b
    View quality metrics:
      $ caas monitor quality

    \b
    Manage alerts:
      $ caas monitor alerts list
      $ caas monitor alerts add --metric cost --threshold 10.0

    \b
    Export metrics:
      $ caas monitor export --format prometheus
      $ caas monitor export --format json --output metrics.json
    """
    pass


@monitor.command(name="metrics")
@click.option("--watch", "-w", is_flag=True, help="Watch metrics in real-time")
@click.option(
    "--interval",
    "-i",
    type=int,
    default=5,
    help="Update interval in seconds (default: 5)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed metrics")
@handle_keyboard_interrupt
def metrics(watch, interval, verbose):
    """
    View system metrics

    \b
    METRICS SHOWN:
    ═══════════════════════════════════════════════════════════════════════════
    • Total generations
    • Success/failure rate
    • Average generation time
    • LLM API calls
    • Cache hit rate
    • Current active sessions
    """
    try:
        from caas_framework.monitoring import get_metrics_collector

        collector = get_metrics_collector()

        def display_metrics():
            metrics_data = collector.get_all_metrics()

            # Create layout
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
            )

            # Header
            header_text = f"[bold cyan]System Metrics[/bold cyan] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            layout["header"].update(Panel(header_text, border_style="cyan"))

            # Body - metrics table
            table = Table(border_style="blue", expand=True)
            table.add_column("Metric", style="cyan", width=30)
            table.add_column("Value", style="green", width=20)
            table.add_column("Change", style="yellow", width=15)

            # Add metrics
            table.add_row(
                "Total Generations",
                str(metrics_data.get("total_generations", 0)),
                f"+{metrics_data.get('generation_delta', 0)}",
            )
            table.add_row(
                "Success Rate", f"{metrics_data.get('success_rate', 0):.1f}%", ""
            )
            table.add_row(
                "Average Time", f"{metrics_data.get('avg_generation_time', 0):.2f}s", ""
            )
            table.add_row(
                "LLM API Calls",
                str(metrics_data.get("llm_api_calls", 0)),
                f"+{metrics_data.get('llm_calls_delta', 0)}",
            )
            table.add_row(
                "Cache Hit Rate", f"{metrics_data.get('cache_hit_rate', 0):.1f}%", ""
            )
            table.add_row(
                "Active Sessions", str(metrics_data.get("active_sessions", 0)), ""
            )

            if verbose:
                table.add_row("", "", "")
                table.add_row("[bold]Detailed Metrics[/bold]", "", "")
                table.add_row(
                    "Total Errors", str(metrics_data.get("total_errors", 0)), ""
                )
                table.add_row(
                    "Avg Phase Time",
                    f"{metrics_data.get('avg_phase_time', 0):.2f}s",
                    "",
                )
                table.add_row(
                    "Memory Usage", f"{metrics_data.get('memory_mb', 0):.1f} MB", ""
                )

            layout["body"].update(table)
            return layout

        if watch:
            # Watch mode with live updates
            echo_info("Monitoring metrics (press Ctrl+C to stop)...")
            console.print()

            try:
                with Live(
                    display_metrics(), refresh_per_second=1 / interval, console=console
                ):
                    while True:
                        time.sleep(interval)
            except KeyboardInterrupt:
                echo_info("\nStopped monitoring")
        else:
            # Single display
            console.print()
            console.print(display_metrics())
            console.print()

    except ImportError as e:
        echo_error(f"Failed to import monitoring modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Failed to get metrics: {e}")
        if verbose:
            import traceback

            echo_error(traceback.format_exc())
        return 1


@monitor.command(name="cost")
@click.option(
    "--breakdown", "-b", is_flag=True, help="Show cost breakdown by phase/model"
)
@click.option(
    "--period",
    "-p",
    type=click.Choice(["hour", "day", "week", "month", "all"]),
    default="day",
    help="Time period for cost analysis",
)
@click.option("--export", "-e", type=click.Path(), help="Export cost report to file")
@handle_keyboard_interrupt
def cost(breakdown, period, export):
    """
    View cost tracking and analysis

    \b
    COST TRACKING:
    ═══════════════════════════════════════════════════════════════════════════
    • Total costs (USD)
    • Cost by phase
    • Cost by LLM model
    • Cost trends
    • Budget alerts

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    View today's costs:
      $ caas monitor cost

    Detailed breakdown:
      $ caas monitor cost --breakdown

    Weekly costs:
      $ caas monitor cost --period week

    Export report:
      $ caas monitor cost --breakdown --export cost_report.json
    """
    try:
        from caas_framework.monitoring import get_cost_tracker

        tracker = get_cost_tracker()

        # Get cost data
        cost_data = tracker.get_costs(period=period)

        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]Cost Report - {period.upper()}[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()

        # Summary table
        summary_table = Table(title="Cost Summary", border_style="blue")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Total Cost", f"${cost_data.get('total_cost', 0):.4f}")
        summary_table.add_row("Total Tokens", f"{cost_data.get('total_tokens', 0):,}")
        summary_table.add_row("API Calls", str(cost_data.get("api_calls", 0)))
        summary_table.add_row(
            "Avg Cost/Call", f"${cost_data.get('avg_cost_per_call', 0):.4f}"
        )

        console.print(summary_table)
        console.print()

        if breakdown:
            # Cost by phase
            if cost_data.get("by_phase"):
                phase_table = Table(title="Cost by Phase", border_style="green")
                phase_table.add_column("Phase", style="cyan")
                phase_table.add_column("Cost (USD)", style="green")
                phase_table.add_column("% of Total", style="yellow")

                for phase, phase_cost in cost_data["by_phase"].items():
                    percentage = (
                        (phase_cost / cost_data["total_cost"] * 100)
                        if cost_data["total_cost"] > 0
                        else 0
                    )
                    phase_table.add_row(
                        phase, f"${phase_cost:.4f}", f"{percentage:.1f}%"
                    )

                console.print(phase_table)
                console.print()

            # Cost by model
            if cost_data.get("by_model"):
                model_table = Table(title="Cost by Model", border_style="magenta")
                model_table.add_column("Model", style="cyan")
                model_table.add_column("Cost (USD)", style="green")
                model_table.add_column("Calls", style="yellow")

                for model, model_data in cost_data["by_model"].items():
                    model_table.add_row(
                        model,
                        f"${model_data.get('cost', 0):.4f}",
                        str(model_data.get("calls", 0)),
                    )

                console.print(model_table)
                console.print()

        # Budget warning
        budget_limit = cost_data.get("budget_limit")
        if budget_limit and cost_data["total_cost"] > budget_limit * 0.8:
            echo_warning(
                f"⚠️  Cost is at {cost_data['total_cost']/budget_limit*100:.1f}% of budget limit (${budget_limit})"
            )

        # Export
        if export:
            import json

            with open(export, "w") as f:
                json.dump(cost_data, f, indent=2)
            echo_success(f"Cost report exported to {export}")

    except ImportError as e:
        echo_error(f"Failed to import monitoring modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to get cost data: {e}")
        return 1


@monitor.command(name="quality")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed quality metrics")
@handle_keyboard_interrupt
def quality(detailed):
    """
    View quality metrics tracking

    \b
    QUALITY METRICS:
    ═══════════════════════════════════════════════════════════════════════════
    • Average quality score
    • Quality by phase
    • Validation pass rate
    • Auto-fix success rate
    • Quality trends
    """
    try:
        from caas_framework.monitoring import get_quality_tracker

        tracker = get_quality_tracker()
        quality_data = tracker.get_quality_metrics()

        console.print()
        console.print(
            Panel.fit("[bold cyan]Quality Metrics[/bold cyan]", border_style="cyan")
        )
        console.print()

        # Summary
        summary_table = Table(border_style="blue")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row(
            "Avg Quality Score", f"{quality_data.get('avg_score', 0):.1f}/10.0"
        )
        summary_table.add_row(
            "Validation Pass Rate",
            f"{quality_data.get('validation_pass_rate', 0):.1f}%",
        )
        summary_table.add_row(
            "Auto-fix Success Rate",
            f"{quality_data.get('autofix_success_rate', 0):.1f}%",
        )
        summary_table.add_row(
            "Total Validations", str(quality_data.get("total_validations", 0))
        )

        console.print(summary_table)
        console.print()

        if detailed:
            # Quality by phase
            if quality_data.get("by_phase"):
                phase_table = Table(title="Quality by Phase", border_style="green")
                phase_table.add_column("Phase", style="cyan")
                phase_table.add_column("Avg Score", style="green")
                phase_table.add_column("Pass Rate", style="yellow")

                for phase, phase_data in quality_data["by_phase"].items():
                    phase_table.add_row(
                        phase,
                        f"{phase_data.get('avg_score', 0):.1f}/10.0",
                        f"{phase_data.get('pass_rate', 0):.1f}%",
                    )

                console.print(phase_table)
                console.print()

    except ImportError as e:
        echo_error(f"Failed to import monitoring modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to get quality metrics: {e}")
        return 1


@monitor.command(name="alerts")
@click.argument("action", type=click.Choice(["list", "add", "remove", "test"]))
@click.option("--metric", type=str, help="Metric name for alert")
@click.option("--threshold", type=float, help="Alert threshold value")
@click.option(
    "--condition", type=click.Choice(["above", "below", "equals"]), default="above"
)
@handle_keyboard_interrupt
def alerts(action, metric, threshold, condition):
    """
    Manage monitoring alerts

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    List alerts:
      $ caas monitor alerts list

    Add alert:
      $ caas monitor alerts add --metric cost --threshold 10.0 --condition above

    Remove alert:
      $ caas monitor alerts remove --metric cost

    Test alerts:
      $ caas monitor alerts test
    """
    try:
        from caas_framework.monitoring import get_alert_system

        alert_system = get_alert_system()

        if action == "list":
            alerts = alert_system.list_alerts()

            if not alerts:
                echo_info("No alerts configured")
                return

            console.print()
            table = Table(title="Configured Alerts", border_style="blue")
            table.add_column("Metric", style="cyan")
            table.add_column("Condition", style="yellow")
            table.add_column("Threshold", style="green")
            table.add_column("Status", style="magenta")

            for alert in alerts:
                status = "🔔 Active" if alert.get("active") else "🔕 Inactive"
                table.add_row(
                    alert["metric"], alert["condition"], str(alert["threshold"]), status
                )

            console.print(table)
            console.print()

        elif action == "add":
            if not metric or threshold is None:
                echo_error("--metric and --threshold are required for adding alerts")
                return 1

            alert_system.add_alert(
                metric=metric, threshold=threshold, condition=condition
            )
            echo_success(f"✅ Added alert: {metric} {condition} {threshold}")

        elif action == "remove":
            if not metric:
                echo_error("--metric is required for removing alerts")
                return 1

            alert_system.remove_alert(metric)
            echo_success(f"✅ Removed alert for metric: {metric}")

        elif action == "test":
            triggered = alert_system.test_alerts()
            if triggered:
                echo_warning(f"⚠️  {len(triggered)} alert(s) would be triggered")
                for alert in triggered:
                    echo_warning(
                        f"  - {alert['metric']}: {alert['current_value']} {alert['condition']} {alert['threshold']}"
                    )
            else:
                echo_success("✅ No alerts would be triggered")

    except ImportError as e:
        echo_error(f"Failed to import monitoring modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to manage alerts: {e}")
        return 1


@monitor.command(name="export")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["prometheus", "json", "csv"]),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@handle_keyboard_interrupt
def export(format, output):
    """
    Export metrics to file

    \b
    SUPPORTED FORMATS:
    ═══════════════════════════════════════════════════════════════════════════
    • prometheus - Prometheus format
    • json - JSON format
    • csv - CSV format

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    Export to Prometheus:
      $ caas monitor export --format prometheus --output metrics.prom

    Export to JSON:
      $ caas monitor export --format json --output metrics.json

    Print to console:
      $ caas monitor export --format json
    """
    try:
        from caas_framework.monitoring import get_metrics_exporter

        exporter = get_metrics_exporter()

        # Export metrics
        exported_data = exporter.export(format=format)

        if output:
            # Write to file
            with open(output, "w") as f:
                f.write(exported_data)
            echo_success(f"✅ Metrics exported to {output}")
        else:
            # Print to console
            console.print()
            console.print(
                Panel(
                    exported_data,
                    title=f"Metrics Export ({format.upper()})",
                    border_style="cyan",
                )
            )
            console.print()

    except ImportError as e:
        echo_error(f"Failed to import monitoring modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to export metrics: {e}")
        return 1
