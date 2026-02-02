"""
Performance Dashboard

Rich console-based dashboard for displaying performance metrics in real-time.
Provides beautiful, colorful visualization of workflow execution metrics.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from caas_framework.monitoring.metrics_collector import MetricsCollector, WorkflowMetrics


class PerformanceDashboard:
    """
    Performance Dashboard

    Displays workflow performance metrics using Rich console library.
    Provides real-time visualization, summaries, and comparisons.
    """

    def __init__(self, console: Optional[Any] = None):
        """
        Initialize dashboard

        Args:
            console: Rich Console instance (creates new if None)
        """
        if not RICH_AVAILABLE:
            raise ImportError("Rich library not available. Install: pip install rich")

        self.console = console or Console()

    def display_workflow_summary(self, metrics: WorkflowMetrics):
        """
        Display workflow execution summary

        Args:
            metrics: WorkflowMetrics to display
        """
        # Header
        self.console.print()
        self.console.print("=" * 70, style="cyan")
        self.console.print(f"  Performance Summary: {metrics.workflow_id}", style="bold cyan")
        self.console.print("=" * 70, style="cyan")
        self.console.print()

        # Main metrics panel
        summary_text = f"""
[bold]Requirement:[/bold] {metrics.requirement}

[bold cyan]⏱️  Duration:[/bold cyan]        {metrics.total_duration_seconds:.2f}s
[bold green]✅ Success Rate:[/bold green]     {metrics.success_rate * 100:.1f}%
[bold yellow]📊 Total Phases:[/bold yellow]    {metrics.total_phases} ({metrics.successful_phases} succeeded, {metrics.failed_phases} failed)
[bold red]🔥 Bottleneck:[/bold red]       {metrics.bottleneck_phase or 'None'} ({metrics.slowest_phase_duration:.2f}s)

[bold magenta]💰 LLM Usage:[/bold magenta]
   • Total Calls:      {metrics.total_llm_calls}
   • Input Tokens:     {metrics.total_tokens_input:,}
   • Output Tokens:    {metrics.total_tokens_output:,}
   • Total Tokens:     {metrics.total_tokens:,}
   • Estimated Cost:   ${metrics.total_cost_usd:.4f}

[bold blue]📈 Performance:[/bold blue]
   • Fastest Phase:    {metrics.fastest_phase_duration:.2f}s
   • Slowest Phase:    {metrics.slowest_phase_duration:.2f}s
   • Average Phase:    {metrics.avg_phase_duration:.2f}s
   • Peak Memory:      {metrics.peak_memory_mb:.1f} MB
        """

        panel = Panel(
            summary_text.strip(),
            title="[bold]Workflow Summary[/bold]",
            border_style="green",
            box=box.ROUNDED,
        )

        self.console.print(panel)
        self.console.print()

    def display_phase_breakdown(self, metrics: WorkflowMetrics):
        """
        Display phase-by-phase performance breakdown

        Args:
            metrics: WorkflowMetrics with phase details
        """
        table = Table(
            title="Phase Performance Breakdown",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Phase", style="cyan", no_wrap=True)
        table.add_column("Duration", justify="right", style="yellow")
        table.add_column("% of Total", justify="right")
        table.add_column("LLM Calls", justify="right", style="magenta")
        table.add_column("Tokens", justify="right", style="blue")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Status", justify="center")

        for phase in metrics.phases:
            # Calculate percentage of total time
            pct_of_total = (
                (phase.duration_seconds / metrics.total_duration_seconds * 100)
                if metrics.total_duration_seconds > 0
                else 0
            )

            # Status emoji
            if phase.success:
                status = "✅"
                status_style = "green"
            else:
                status = "❌"
                status_style = "red"

            # Highlight bottleneck
            phase_style = "bold red" if phase.phase == metrics.bottleneck_phase else ""

            table.add_row(
                f"[{phase_style}]{phase.phase}[/{phase_style}]",
                f"{phase.duration_seconds:.2f}s",
                f"{pct_of_total:.1f}%",
                str(phase.llm_calls),
                f"{phase.llm_tokens_total:,}",
                f"${phase.llm_cost_usd:.4f}",
                f"[{status_style}]{status}[/{status_style}]",
            )

        self.console.print(table)
        self.console.print()

    def display_comparison(
        self, current: WorkflowMetrics, baseline: WorkflowMetrics, comparison: Dict[str, Any]
    ):
        """
        Display comparison between current and baseline metrics

        Args:
            current: Current workflow metrics
            baseline: Baseline workflow metrics
            comparison: Comparison dict from MetricsCollector.compare_with_baseline
        """
        self.console.print()
        self.console.print("=" * 70, style="cyan")
        self.console.print("  Comparison with Baseline", style="bold cyan")
        self.console.print("=" * 70, style="cyan")
        self.console.print()

        # Duration comparison
        duration_imp = comparison["duration_improvement"]
        duration_color = "green" if duration_imp["improved"] else "red"
        duration_arrow = "↓" if duration_imp["improved"] else "↑"

        # Cost comparison
        cost_imp = comparison["cost_improvement"]
        cost_color = "green" if cost_imp["improved"] else "red"
        cost_arrow = "↓" if cost_imp["improved"] else "↑"

        comparison_text = f"""
[bold]Duration Comparison:[/bold]
   • Baseline:     {duration_imp['baseline_seconds']:.2f}s
   • Current:      {duration_imp['current_seconds']:.2f}s
   • Difference:   [{duration_color}]{duration_arrow} {abs(duration_imp['difference_seconds']):.2f}s ({abs(duration_imp['difference_percent']):.1f}%)[/{duration_color}]
   • Speedup:      {comparison['speedup']:.2f}x

[bold]Cost Comparison:[/bold]
   • Baseline:     ${cost_imp['baseline_usd']:.4f}
   • Current:      ${cost_imp['current_usd']:.4f}
   • Difference:   [{cost_color}]{cost_arrow} ${abs(cost_imp['difference_usd']):.4f} ({abs(cost_imp['difference_percent']):.1f}%)[/{cost_color}]

[bold]Resource Savings:[/bold]
   • Tokens Saved:     {comparison['tokens_saved']:,}
   • LLM Calls Saved:  {comparison['llm_calls_saved']}
        """

        panel = Panel(
            comparison_text.strip(),
            title="[bold]Performance Comparison[/bold]",
            border_style="blue",
            box=box.ROUNDED,
        )

        self.console.print(panel)
        self.console.print()

    def display_bottleneck_analysis(self, metrics: WorkflowMetrics):
        """
        Display bottleneck analysis

        Args:
            metrics: WorkflowMetrics
        """
        if not metrics.bottleneck_phase:
            return

        bottleneck = next((p for p in metrics.phases if p.phase == metrics.bottleneck_phase), None)
        if not bottleneck:
            return

        # Calculate impact
        pct_of_total = (
            (bottleneck.duration_seconds / metrics.total_duration_seconds * 100)
            if metrics.total_duration_seconds > 0
            else 0
        )

        analysis_text = f"""
[bold red]🔥 Bottleneck Identified:[/bold red] {bottleneck.phase}

[bold]Impact:[/bold]
   • Duration:         {bottleneck.duration_seconds:.2f}s ({pct_of_total:.1f}% of total)
   • LLM Calls:        {bottleneck.llm_calls}
   • Tokens Used:      {bottleneck.llm_tokens_total:,}
   • Validation Runs:  {bottleneck.validation_runs}
   • Retries:          {bottleneck.retry_count}

[bold yellow]💡 Optimization Suggestions:[/bold yellow]
   • Consider caching results for this phase
   • Review prompt engineering to reduce token usage
   • Check if parallel execution is possible
   • Optimize validation logic to reduce iterations
        """

        panel = Panel(
            analysis_text.strip(),
            title="[bold red]Bottleneck Analysis[/bold red]",
            border_style="red",
            box=box.ROUNDED,
        )

        self.console.print(panel)
        self.console.print()

    def display_full_report(
        self, metrics: WorkflowMetrics, baseline: Optional[WorkflowMetrics] = None
    ):
        """
        Display complete performance report

        Args:
            metrics: Current workflow metrics
            baseline: Optional baseline metrics for comparison
        """
        # Workflow summary
        self.display_workflow_summary(metrics)

        # Phase breakdown
        self.display_phase_breakdown(metrics)

        # Bottleneck analysis
        self.display_bottleneck_analysis(metrics)

        # Comparison with baseline
        if baseline:
            collector = MetricsCollector()
            comparison = collector.compare_with_baseline(metrics, baseline)
            self.display_comparison(metrics, baseline, comparison)

    def generate_markdown_report(
        self,
        metrics: WorkflowMetrics,
        output_path: Path,
        baseline: Optional[WorkflowMetrics] = None,
    ):
        """
        Generate Markdown performance report

        Args:
            metrics: Workflow metrics
            output_path: Output file path
            baseline: Optional baseline for comparison
        """
        md_lines = []

        # Header
        md_lines.append(f"# Performance Report: {metrics.workflow_id}")
        md_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"\n**Requirement:** {metrics.requirement}")
        md_lines.append("\n---\n")

        # Summary
        md_lines.append("## Summary\n")
        md_lines.append(f"- **Duration:** {metrics.total_duration_seconds:.2f}s")
        md_lines.append(f"- **Success Rate:** {metrics.success_rate * 100:.1f}%")
        md_lines.append(f"- **Total Phases:** {metrics.total_phases}")
        md_lines.append(f"- **Bottleneck:** {metrics.bottleneck_phase or 'None'}")
        md_lines.append(f"- **Total Cost:** ${metrics.total_cost_usd:.4f}")
        md_lines.append(f"- **Total Tokens:** {metrics.total_tokens:,}")
        md_lines.append("\n")

        # Phase breakdown table
        md_lines.append("## Phase Breakdown\n")
        md_lines.append("| Phase | Duration | % of Total | LLM Calls | Tokens | Cost | Status |")
        md_lines.append("|-------|----------|------------|-----------|--------|------|--------|")

        for phase in metrics.phases:
            pct = (
                (phase.duration_seconds / metrics.total_duration_seconds * 100)
                if metrics.total_duration_seconds > 0
                else 0
            )
            status = "✅" if phase.success else "❌"

            md_lines.append(
                f"| {phase.phase} | {phase.duration_seconds:.2f}s | {pct:.1f}% | "
                f"{phase.llm_calls} | {phase.llm_tokens_total:,} | ${phase.llm_cost_usd:.4f} | {status} |"
            )

        md_lines.append("\n")

        # Bottleneck analysis
        if metrics.bottleneck_phase:
            bottleneck = next(
                (p for p in metrics.phases if p.phase == metrics.bottleneck_phase), None
            )
            if bottleneck:
                md_lines.append("## Bottleneck Analysis\n")
                md_lines.append(f"**🔥 Bottleneck Phase:** {bottleneck.phase}\n")
                md_lines.append(f"- Duration: {bottleneck.duration_seconds:.2f}s")
                md_lines.append(f"- LLM Calls: {bottleneck.llm_calls}")
                md_lines.append(f"- Tokens: {bottleneck.llm_tokens_total:,}")
                md_lines.append(f"- Retries: {bottleneck.retry_count}")
                md_lines.append("\n**Optimization Suggestions:**")
                md_lines.append("- Consider caching results for this phase")
                md_lines.append("- Review prompt engineering to reduce token usage")
                md_lines.append("- Check if parallel execution is possible")
                md_lines.append("\n")

        # Comparison with baseline
        if baseline:
            collector = MetricsCollector()
            comparison = collector.compare_with_baseline(metrics, baseline)

            md_lines.append("## Comparison with Baseline\n")

            duration_imp = comparison["duration_improvement"]
            duration_arrow = "↓" if duration_imp["improved"] else "↑"

            cost_imp = comparison["cost_improvement"]
            cost_arrow = "↓" if cost_imp["improved"] else "↑"

            md_lines.append("### Duration")
            md_lines.append(f"- Baseline: {duration_imp['baseline_seconds']:.2f}s")
            md_lines.append(f"- Current: {duration_imp['current_seconds']:.2f}s")
            md_lines.append(
                f"- Difference: {duration_arrow} {abs(duration_imp['difference_seconds']):.2f}s ({abs(duration_imp['difference_percent']):.1f}%)"
            )
            md_lines.append(f"- Speedup: {comparison['speedup']:.2f}x")
            md_lines.append("\n### Cost")
            md_lines.append(f"- Baseline: ${cost_imp['baseline_usd']:.4f}")
            md_lines.append(f"- Current: ${cost_imp['current_usd']:.4f}")
            md_lines.append(
                f"- Difference: {cost_arrow} ${abs(cost_imp['difference_usd']):.4f} ({abs(cost_imp['difference_percent']):.1f}%)"
            )
            md_lines.append("\n")

        # Write to file
        with open(output_path, "w") as f:
            f.write("\n".join(md_lines))

    def generate_html_report(
        self,
        metrics: WorkflowMetrics,
        output_path: Path,
        baseline: Optional[WorkflowMetrics] = None,
    ):
        """
        Generate HTML performance report

        Args:
            metrics: Workflow metrics
            output_path: Output file path
            baseline: Optional baseline for comparison
        """
        html_lines = []

        # HTML header
        html_lines.append("<!DOCTYPE html>")
        html_lines.append("<html>")
        html_lines.append("<head>")
        html_lines.append(f"<title>Performance Report: {metrics.workflow_id}</title>")
        html_lines.append("<style>")
        html_lines.append(
            """
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; }
            .summary { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .metric { display: inline-block; margin: 10px 20px 10px 0; }
            .metric-label { font-weight: bold; color: #7f8c8d; }
            .metric-value { font-size: 1.2em; color: #2c3e50; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th { background: #3498db; color: white; padding: 12px; text-align: left; }
            td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
            tr:hover { background: #f8f9fa; }
            .success { color: #27ae60; }
            .failed { color: #e74c3c; }
            .bottleneck { background: #ffe5e5; font-weight: bold; }
            .improvement { color: #27ae60; }
            .regression { color: #e74c3c; }
        """
        )
        html_lines.append("</style>")
        html_lines.append("</head>")
        html_lines.append("<body>")
        html_lines.append("<div class='container'>")

        # Title
        html_lines.append(f"<h1>Performance Report: {metrics.workflow_id}</h1>")
        html_lines.append(
            f"<p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        )
        html_lines.append(f"<p><strong>Requirement:</strong> {metrics.requirement}</p>")

        # Summary
        html_lines.append("<div class='summary'>")
        html_lines.append("<h2>Summary</h2>")
        html_lines.append(
            "<div class='metric'><span class='metric-label'>Duration:</span> <span class='metric-value'>{:.2f}s</span></div>".format(
                metrics.total_duration_seconds
            )
        )
        html_lines.append(
            "<div class='metric'><span class='metric-label'>Success Rate:</span> <span class='metric-value'>{:.1f}%</span></div>".format(
                metrics.success_rate * 100
            )
        )
        html_lines.append(
            "<div class='metric'><span class='metric-label'>Total Cost:</span> <span class='metric-value'>${:.4f}</span></div>".format(
                metrics.total_cost_usd
            )
        )
        html_lines.append(
            "<div class='metric'><span class='metric-label'>Tokens:</span> <span class='metric-value'>{:,}</span></div>".format(
                metrics.total_tokens
            )
        )
        html_lines.append(
            "<div class='metric'><span class='metric-label'>Bottleneck:</span> <span class='metric-value'>{}</span></div>".format(
                metrics.bottleneck_phase or "None"
            )
        )
        html_lines.append("</div>")

        # Phase breakdown table
        html_lines.append("<h2>Phase Breakdown</h2>")
        html_lines.append("<table>")
        html_lines.append(
            "<tr><th>Phase</th><th>Duration</th><th>% of Total</th><th>LLM Calls</th><th>Tokens</th><th>Cost</th><th>Status</th></tr>"
        )

        for phase in metrics.phases:
            pct = (
                (phase.duration_seconds / metrics.total_duration_seconds * 100)
                if metrics.total_duration_seconds > 0
                else 0
            )
            status_class = "success" if phase.success else "failed"
            status_icon = "✅" if phase.success else "❌"
            row_class = "bottleneck" if phase.phase == metrics.bottleneck_phase else ""

            html_lines.append(
                f"<tr class='{row_class}'>"
                f"<td>{phase.phase}</td>"
                f"<td>{phase.duration_seconds:.2f}s</td>"
                f"<td>{pct:.1f}%</td>"
                f"<td>{phase.llm_calls}</td>"
                f"<td>{phase.llm_tokens_total:,}</td>"
                f"<td>${phase.llm_cost_usd:.4f}</td>"
                f"<td class='{status_class}'>{status_icon}</td>"
                f"</tr>"
            )

        html_lines.append("</table>")

        # Comparison
        if baseline:
            collector = MetricsCollector()
            comparison = collector.compare_with_baseline(metrics, baseline)

            html_lines.append("<h2>Comparison with Baseline</h2>")
            html_lines.append("<div class='summary'>")

            duration_imp = comparison["duration_improvement"]
            duration_class = "improvement" if duration_imp["improved"] else "regression"

            cost_imp = comparison["cost_improvement"]
            cost_class = "improvement" if cost_imp["improved"] else "regression"

            html_lines.append(f"<h3>Duration</h3>")
            html_lines.append(
                f"<p>Baseline: {duration_imp['baseline_seconds']:.2f}s → Current: {duration_imp['current_seconds']:.2f}s</p>"
            )
            html_lines.append(
                f"<p class='{duration_class}'>Difference: {abs(duration_imp['difference_seconds']):.2f}s ({abs(duration_imp['difference_percent']):.1f}%)</p>"
            )
            html_lines.append(f"<p>Speedup: {comparison['speedup']:.2f}x</p>")

            html_lines.append(f"<h3>Cost</h3>")
            html_lines.append(
                f"<p>Baseline: ${cost_imp['baseline_usd']:.4f} → Current: ${cost_imp['current_usd']:.4f}</p>"
            )
            html_lines.append(
                f"<p class='{cost_class}'>Difference: ${abs(cost_imp['difference_usd']):.4f} ({abs(cost_imp['difference_percent']):.1f}%)</p>"
            )

            html_lines.append("</div>")

        # Close HTML
        html_lines.append("</div>")
        html_lines.append("</body>")
        html_lines.append("</html>")

        # Write to file
        with open(output_path, "w") as f:
            f.write("\n".join(html_lines))
