"""
Performance Profiling Command

Profile system performance, analyze bottlenecks, and generate reports.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)

console = Console()


@click.group(name="profile")
def profile():
    """
    Performance profiling and analysis

    \b
    📊 PROFILING FEATURES:
    ═══════════════════════════════════════════════════════════════════════════
    • Phase-by-phase performance profiling
    • Bottleneck detection
    • Memory usage tracking
    • Performance reports
    • Optimization suggestions

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    Profile a generation:
      $ caas profile run "Build a todo app"

    \b
    View profiling report:
      $ caas profile report --latest
      $ caas profile report --session abc123

    \b
    Show bottlenecks:
      $ caas profile bottlenecks

    \b
    Performance comparison:
      $ caas profile compare session1 session2
    """
    pass


@profile.command(name="run")
@click.argument("requirement")
@click.option("--output", "-o", type=click.Path(), help="Output directory for generated code")
@click.option("--report", "-r", type=click.Path(), help="Save profiling report to file")
@click.option("--enable-memory-profiling", is_flag=True, help="Enable memory profiling (slower)")
@handle_keyboard_interrupt
def run(requirement, output, report, enable_memory_profiling):
    """
    Run generation with profiling enabled

    \b
    PROFILING DATA:
    ═══════════════════════════════════════════════════════════════════════════
    • Phase execution times
    • LLM API call latencies
    • Cache hit/miss rates
    • Memory usage (if enabled)
    • Bottleneck identification

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    Basic profiling:
      $ caas profile run "Build a REST API"

    With memory profiling:
      $ caas profile run "Build a chatbot" --enable-memory-profiling

    Save report:
      $ caas profile run "Build a blog" --report profile.json
    """
    try:
        from caas_framework.framework import CrewAIFramework
        from caas_framework.performance import get_profiler

        echo_info("Starting generation with profiling enabled...")
        console.print()

        # Create profiler
        profiler = get_profiler()
        profiler.enable(memory_profiling=enable_memory_profiling)

        # Start profiling
        profiler.start("full_generation")

        try:
            # Run generation
            framework = CrewAIFramework()
            result = framework.generate_from_requirement(
                requirement=requirement, output_dir=output or "./output"
            )

            # Stop profiling
            profiler.stop("full_generation")

            # Get profiling report
            profile_report = profiler.get_report()

            # Display summary
            console.print()
            echo_success("✅ Generation completed with profiling")
            console.print()

            _display_profile_summary(profile_report)

            # Save report
            if report:
                import json

                with open(report, "w") as f:
                    json.dump(profile_report, f, indent=2)
                echo_success(f"Profiling report saved to {report}")

            return result

        except Exception as e:
            profiler.stop("full_generation")
            echo_error(f"Generation failed: {e}")
            raise

    except ImportError as e:
        echo_error(f"Failed to import profiling modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Failed to run profiling: {e}")
        return 1


def _display_profile_summary(report: dict):
    """Display profiling report summary"""
    console.print(Panel.fit("[bold cyan]Profiling Summary[/bold cyan]", border_style="cyan"))
    console.print()

    # Overall metrics
    summary_table = Table(border_style="blue")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Time", f"{report.get('total_time', 0):.2f}s")
    summary_table.add_row("LLM Calls", str(report.get("llm_calls", 0)))
    summary_table.add_row("Cache Hits", str(report.get("cache_hits", 0)))
    summary_table.add_row("Cache Misses", str(report.get("cache_misses", 0)))

    if report.get("memory_mb"):
        summary_table.add_row("Peak Memory", f"{report['memory_mb']:.1f} MB")

    console.print(summary_table)
    console.print()

    # Phase breakdown
    if report.get("phases"):
        phase_table = Table(title="Phase Performance", border_style="green")
        phase_table.add_column("Phase", style="cyan")
        phase_table.add_column("Time (s)", style="green")
        phase_table.add_column("% of Total", style="yellow")

        total_time = report.get("total_time", 1)
        for phase, phase_data in report["phases"].items():
            phase_time = phase_data.get("time", 0)
            percentage = (phase_time / total_time * 100) if total_time > 0 else 0

            phase_table.add_row(phase, f"{phase_time:.2f}", f"{percentage:.1f}%")

        console.print(phase_table)
        console.print()


@profile.command(name="report")
@click.option("--latest", is_flag=True, help="Show latest profiling report")
@click.option("--session", "-s", type=str, help="Show report for specific session")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed report")
@click.option("--export", "-e", type=click.Path(), help="Export report to file")
@handle_keyboard_interrupt
def report(latest, session, detailed, export):
    """
    View profiling reports

    \b
    REPORT CONTENTS:
    ═══════════════════════════════════════════════════════════════════════════
    • Phase execution times
    • Function-level profiling
    • Memory usage
    • Bottleneck analysis
    • Optimization suggestions

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    Latest report:
      $ caas profile report --latest

    Specific session:
      $ caas profile report --session abc123

    Detailed report:
      $ caas profile report --latest --detailed

    Export:
      $ caas profile report --latest --export report.html
    """
    try:
        from caas_framework.performance import get_profiler

        profiler = get_profiler()

        # Get report
        if latest:
            report_data = profiler.get_latest_report()
        elif session:
            report_data = profiler.get_report(session_id=session)
        else:
            echo_error("Please specify --latest or --session")
            return 1

        if not report_data:
            echo_info("No profiling report found")
            return

        console.print()
        console.print(Panel.fit("[bold cyan]Performance Report[/bold cyan]", border_style="cyan"))
        console.print()

        # Display report
        _display_profile_summary(report_data)

        if detailed:
            # Function-level profiling
            if report_data.get("functions"):
                console.print(
                    Panel.fit("[bold cyan]Function Profiling[/bold cyan]", border_style="blue")
                )
                console.print()

                func_table = Table(border_style="blue")
                func_table.add_column("Function", style="cyan", width=40)
                func_table.add_column("Calls", style="green", width=10)
                func_table.add_column("Total Time", style="yellow", width=12)
                func_table.add_column("Avg Time", style="magenta", width=12)

                for func_name, func_data in sorted(
                    report_data["functions"].items(),
                    key=lambda x: x[1].get("total_time", 0),
                    reverse=True,
                )[
                    :20
                ]:  # Top 20
                    calls = func_data.get("calls", 0)
                    total_time = func_data.get("total_time", 0)
                    avg_time = total_time / calls if calls > 0 else 0

                    func_table.add_row(
                        func_name, str(calls), f"{total_time:.3f}s", f"{avg_time:.3f}s"
                    )

                console.print(func_table)
                console.print()

        # Export
        if export:
            import json

            with open(export, "w") as f:
                json.dump(report_data, f, indent=2)
            echo_success(f"Report exported to {export}")

    except ImportError as e:
        echo_error(f"Failed to import profiling modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to get report: {e}")
        return 1


@profile.command(name="bottlenecks")
@click.option(
    "--threshold", "-t", type=float, default=1.0, help="Time threshold in seconds (default: 1.0)"
)
@click.option(
    "--limit", "-l", type=int, default=10, help="Number of bottlenecks to show (default: 10)"
)
@handle_keyboard_interrupt
def bottlenecks(threshold, limit):
    """
    Identify performance bottlenecks

    \b
    BOTTLENECK DETECTION:
    ═══════════════════════════════════════════════════════════════════════════
    • Slowest phases
    • Slowest functions
    • High-latency LLM calls
    • Memory-intensive operations

    \b
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════
    Show top 10 bottlenecks:
      $ caas profile bottlenecks

    Custom threshold:
      $ caas profile bottlenecks --threshold 2.0

    Show top 20:
      $ caas profile bottlenecks --limit 20
    """
    try:
        from caas_framework.performance import get_profiler

        profiler = get_profiler()
        bottlenecks_data = profiler.identify_bottlenecks(threshold=threshold, limit=limit)

        if not bottlenecks_data:
            echo_success("✅ No significant bottlenecks found")
            return

        console.print()
        console.print(
            Panel.fit(
                f"[bold yellow]Performance Bottlenecks (>{threshold}s)[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print()

        # Create tree view
        tree = Tree("🔍 Bottlenecks", guide_style="blue")

        for bottleneck in bottlenecks_data:
            severity = bottleneck.get("severity", "low")
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                severity, "⚪"
            )

            branch = tree.add(f"{severity_icon} {bottleneck['name']} - {bottleneck['time']:.2f}s")

            if bottleneck.get("suggestion"):
                branch.add(f"💡 {bottleneck['suggestion']}")

        console.print(tree)
        console.print()

        # Show recommendations
        console.print(
            Panel(
                "[bold]Optimization Recommendations:[/bold]\n\n"
                "• Enable caching to reduce LLM API calls\n"
                "• Use faster models for simple phases\n"
                "• Enable parallel processing where possible\n"
                "• Consider using multi-model routing",
                title="Recommendations",
                border_style="green",
            )
        )
        console.print()

    except ImportError as e:
        echo_error(f"Failed to import profiling modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to identify bottlenecks: {e}")
        return 1


@profile.command(name="compare")
@click.argument("session1")
@click.argument("session2")
@click.option(
    "--metric",
    "-m",
    type=click.Choice(["time", "memory", "llm_calls", "cache_hits"]),
    default="time",
    help="Metric to compare",
)
@handle_keyboard_interrupt
def compare(session1, session2, metric):
    """
    Compare performance between two sessions

    \b
    COMPARISON METRICS:
    ═══════════════════════════════════════════════════════════════════════════
    • Execution time
    • Memory usage
    • LLM API calls
    • Cache hit rates

    \b
    USAGE:
    ═══════════════════════════════════════════════════════════════════════════
    Compare two sessions:
      $ caas profile compare abc123 def456

    Compare specific metric:
      $ caas profile compare abc123 def456 --metric memory
    """
    try:
        from caas_framework.performance import get_profiler

        profiler = get_profiler()

        # Get reports
        report1 = profiler.get_report(session_id=session1)
        report2 = profiler.get_report(session_id=session2)

        if not report1 or not report2:
            echo_error("One or both session reports not found")
            return 1

        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]Performance Comparison: {metric.upper()}[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()

        # Comparison table
        table = Table(border_style="blue")
        table.add_column("Metric", style="cyan")
        table.add_column(f"Session 1\n({session1[:8]})", style="green")
        table.add_column(f"Session 2\n({session2[:8]})", style="yellow")
        table.add_column("Difference", style="magenta")

        # Add comparison rows based on metric
        if metric == "time":
            time1 = report1.get("total_time", 0)
            time2 = report2.get("total_time", 0)
            diff = time2 - time1
            diff_pct = (diff / time1 * 100) if time1 > 0 else 0

            table.add_row(
                "Total Time", f"{time1:.2f}s", f"{time2:.2f}s", f"{diff:+.2f}s ({diff_pct:+.1f}%)"
            )

        elif metric == "memory":
            mem1 = report1.get("memory_mb", 0)
            mem2 = report2.get("memory_mb", 0)
            diff = mem2 - mem1
            diff_pct = (diff / mem1 * 100) if mem1 > 0 else 0

            table.add_row(
                "Peak Memory",
                f"{mem1:.1f} MB",
                f"{mem2:.1f} MB",
                f"{diff:+.1f} MB ({diff_pct:+.1f}%)",
            )

        elif metric == "llm_calls":
            calls1 = report1.get("llm_calls", 0)
            calls2 = report2.get("llm_calls", 0)
            diff = calls2 - calls1
            diff_pct = (diff / calls1 * 100) if calls1 > 0 else 0

            table.add_row("LLM Calls", str(calls1), str(calls2), f"{diff:+d} ({diff_pct:+.1f}%)")

        elif metric == "cache_hits":
            hits1 = report1.get("cache_hits", 0)
            hits2 = report2.get("cache_hits", 0)
            total1 = hits1 + report1.get("cache_misses", 0)
            total2 = hits2 + report2.get("cache_misses", 0)
            rate1 = (hits1 / total1 * 100) if total1 > 0 else 0
            rate2 = (hits2 / total2 * 100) if total2 > 0 else 0

            table.add_row(
                "Cache Hit Rate", f"{rate1:.1f}%", f"{rate2:.1f}%", f"{rate2-rate1:+.1f}%"
            )

        console.print(table)
        console.print()

        # Verdict
        improvement = diff < 0 if metric in ["time", "memory", "llm_calls"] else diff > 0
        if improvement:
            echo_success(f"✅ Session 2 shows improvement in {metric}")
        else:
            echo_warning(f"⚠️  Session 2 shows regression in {metric}")

    except ImportError as e:
        echo_error(f"Failed to import profiling modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to compare profiles: {e}")
        return 1
