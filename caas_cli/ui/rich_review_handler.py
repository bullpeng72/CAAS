"""
Rich-based Review Handler for CLI

Implements ReviewHandler protocol using Rich library for beautiful console output.
"""

import json
from typing import Any, Dict, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from caas_framework.modes.interfaces import ApprovalDecision


class RichReviewHandler:
    """
    Rich-based implementation of ReviewHandler protocol.

    Provides colorful, formatted console output for CLI using Rich library.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize Rich review handler.

        Args:
            console: Optional Rich Console instance
        """
        self.console = console or Console()

    def display_phase_output(
        self, phase_name: str, description: str, output: Dict[str, Any]
    ) -> None:
        """Display phase output for review."""
        self.console.print(f"\n{'='*70}")
        self.console.print(
            Panel.fit(
                f"[bold cyan]{phase_name} COMPLETE[/bold cyan]\n" f"[dim]{description}[/dim]",
                border_style="cyan",
                box=box.DOUBLE,
            )
        )
        self.console.print(f"{'='*70}\n")

        # Display output based on content
        if "system_scope" in output or "features" in output:
            self._display_requirements(output)
        elif "agents" in output and "tasks" in output:
            self._display_design(output)
        elif "files" in output:
            self._display_code(output)
        else:
            # Generic display
            self._display_generic_output(output)

    def request_decision(
        self, phase_name: str, options: Optional[Dict[str, str]] = None
    ) -> ApprovalDecision:
        """Request user decision on phase output."""
        default_options = {
            "approve": "Continue to next phase",
            "reject": "Stop execution",
            "edit": "Provide feedback for refinement",
            "skip": "Skip this phase (advanced)",
        }
        opts = options or default_options

        # Display options panel
        options_text = "\n".join(
            [
                f"  [{'green' if k == 'approve' else 'red' if k == 'reject' else 'cyan' if k == 'edit' else 'dim'}]{k}[/] - {v}"
                for k, v in opts.items()
            ]
        )

        self.console.print(
            Panel.fit(
                f"[bold yellow]Review {phase_name} output above[/bold yellow]\n\n"
                f"Options:\n{options_text}",
                border_style="yellow",
            )
        )

        # Request choice
        while True:
            choice = Prompt.ask(
                "\n[bold]Your decision[/bold]", choices=list(opts.keys()), default="approve"
            )

            if choice in ["approve", "a", "y", "yes"]:
                return ApprovalDecision.APPROVE
            elif choice in ["reject", "r", "n", "no"]:
                if Confirm.ask("[red]Are you sure you want to stop?[/red]"):
                    return ApprovalDecision.REJECT
            elif choice in ["edit", "e"]:
                return ApprovalDecision.EDIT
            elif choice in ["skip", "s"]:
                if Confirm.ask("[yellow]Skip this approval gate?[/yellow]"):
                    return ApprovalDecision.SKIP
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")

    def request_feedback(
        self, phase_name: str, current_output: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Request user feedback for refinement.

        For now, just collect textual feedback.
        In the future, could support actual JSON editing.

        Returns:
            Tuple of (edited_output, feedback_text)
        """
        self.console.print("\n[bold cyan]Provide feedback for refinement:[/bold cyan]")
        self.console.print("[dim]Enter your feedback (press Ctrl+D or Ctrl+Z when done)[/dim]\n")

        feedback_lines = []
        try:
            while True:
                line = input()
                feedback_lines.append(line)
        except EOFError:
            pass

        feedback = "\n".join(feedback_lines)

        if not feedback.strip():
            self.console.print("[yellow]No feedback provided, using original output[/yellow]")
            return current_output, ""

        self.console.print(f"\n[green]Feedback recorded ({len(feedback)} chars)[/green]")

        # TODO: In future, could use LLM to apply feedback to output
        # For now, just return original output with feedback
        return current_output, feedback

    def display_summary(self, summary_data: Dict[str, Any]) -> None:
        """Display approval gates summary."""
        table = Table(
            title="[bold cyan]Approval Gates Summary[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Phase", style="cyan")
        table.add_column("Decision", justify="center")
        table.add_column("Edited", justify="center")

        for gate_info in summary_data["gates"]:
            decision_emoji = {"approve": "✅", "reject": "❌", "edit": "✏️", "skip": "⏭️"}.get(
                gate_info["decision"], "❓"
            )

            table.add_row(
                gate_info["phase"],
                f"{decision_emoji} {gate_info['decision']}",
                "✏️" if gate_info["had_edits"] else "-",
            )

        self.console.print()
        self.console.print(table)

        stats_panel = Panel(
            f"[bold]Total Gates:[/bold] {summary_data['total_gates']}\n"
            f"[bold]Approved:[/bold] [green]{summary_data['approved']}[/green]\n"
            f"[bold]Rejected:[/bold] [red]{summary_data['rejected']}[/red]\n"
            f"[bold]Skipped:[/bold] [dim]{summary_data.get('skipped', 0)}[/dim]\n"
            f"[bold]Edited:[/bold] [cyan]{summary_data['edited']}[/cyan]\n"
            f"[bold]Approval Rate:[/bold] {summary_data['approval_rate']:.1%}",
            title="Statistics",
            border_style="blue",
        )

        self.console.print(stats_panel)
        self.console.print()

    # ===========================================
    # Private display methods
    # ===========================================

    def _display_requirements(self, output: Dict[str, Any]):
        """Display requirements specification."""
        # System scope
        if "system_scope" in output:
            scope = output["system_scope"]
            self.console.print(
                Panel(
                    f"[bold]Project:[/bold] {scope.get('project_name', 'N/A')}\n"
                    f"[bold]Purpose:[/bold] {scope.get('purpose', 'N/A')}\n"
                    f"[bold]Type:[/bold] {scope.get('system_type', 'N/A')}",
                    title="System Scope",
                    border_style="blue",
                )
            )
            self.console.print()

        # Features
        if "features" in output:
            features = output["features"]
            table = Table(
                title="Features", box=box.ROUNDED, show_header=True, header_style="bold magenta"
            )
            table.add_column("Name", style="cyan")
            table.add_column("Priority", style="yellow")
            table.add_column("Description")

            for feat in features[:10]:  # Show first 10
                if isinstance(feat, dict):
                    table.add_row(
                        feat.get("name", "N/A"),
                        feat.get("priority", "medium"),
                        (
                            feat.get("description", "")[:60] + "..."
                            if len(feat.get("description", "")) > 60
                            else feat.get("description", "")
                        ),
                    )

            self.console.print(table)
            self.console.print()

            if len(features) > 10:
                self.console.print(f"[dim]... and {len(features) - 10} more features[/dim]\n")

        # Data models
        if "data_models" in output:
            data_models = output["data_models"]
            if data_models:
                self.console.print(f"[bold]Data Models:[/bold] {len(data_models)} entities")
                for dm in data_models[:5]:
                    if isinstance(dm, dict):
                        self.console.print(f"  • {dm.get('entity_name', 'N/A')}")
                self.console.print()

    def _display_design(self, output: Dict[str, Any]):
        """Display agent/task design."""
        agents = output.get("agents", [])
        tasks = output.get("tasks", [])

        # Summary
        self.console.print(
            Panel(
                f"[bold]Agents:[/bold] {len(agents)}\n"
                f"[bold]Tasks:[/bold] {len(tasks)}\n"
                f"[bold]Workflow:[/bold] {output.get('workflow_type', 'sequential')}",
                title="Design Summary",
                border_style="blue",
            )
        )
        self.console.print()

        # Agents table
        if agents:
            agent_table = Table(
                title="Agents", box=box.ROUNDED, show_header=True, header_style="bold magenta"
            )
            agent_table.add_column("ID", style="cyan", no_wrap=True)
            agent_table.add_column("Role", style="yellow")
            agent_table.add_column("Tools", style="green")
            agent_table.add_column("Goal")

            for agent in agents[:5]:  # Show first 5
                if isinstance(agent, dict):
                    tools = agent.get("tools", [])
                    tools_str = ", ".join(tools[:3]) if tools else "none"
                    if len(tools) > 3:
                        tools_str += f" +{len(tools)-3}"

                    goal = agent.get("goal", "")
                    goal_short = goal[:40] + "..." if len(goal) > 40 else goal

                    agent_table.add_row(
                        agent.get("id", "N/A"), agent.get("role", "N/A"), tools_str, goal_short
                    )

            self.console.print(agent_table)
            self.console.print()

            if len(agents) > 5:
                self.console.print(f"[dim]... and {len(agents) - 5} more agents[/dim]\n")

        # Tasks summary
        if tasks:
            self.console.print("[bold]Tasks:[/bold]")
            for i, task in enumerate(tasks[:5], 1):
                if isinstance(task, dict):
                    desc = task.get("description", "")[:60]
                    agent_id = task.get("agent", "N/A")
                    self.console.print(f"  {i}. [{agent_id}] {desc}...")

            if len(tasks) > 5:
                self.console.print(f"[dim]... and {len(tasks) - 5} more tasks[/dim]")

            self.console.print()

    def _display_code(self, output: Dict[str, Any]):
        """Display generated code."""
        files = output.get("files", {})

        # Summary
        self.console.print(
            Panel(
                f"[bold]Generated Files:[/bold] {len(files)}\n"
                + "\n".join(f"  • {filename}" for filename in list(files.keys())[:10]),
                title="Code Generation Summary",
                border_style="blue",
            )
        )
        self.console.print()

        # Preview main.py
        if "main.py" in files:
            main_content = files["main.py"]
            preview_lines = main_content.split("\n")[:30]
            preview = "\n".join(preview_lines)

            syntax = Syntax(preview, "python", theme="monokai", line_numbers=True)

            self.console.print(
                Panel(syntax, title="main.py Preview (first 30 lines)", border_style="green")
            )
            self.console.print()

        # File sizes
        if len(files) > 1:
            size_table = Table(title="File Sizes", box=box.SIMPLE)
            size_table.add_column("File", style="cyan")
            size_table.add_column("Lines", justify="right", style="yellow")
            size_table.add_column("Size", justify="right", style="green")

            for filename, content in list(files.items())[:10]:
                lines = len(content.split("\n"))
                size = len(content)
                size_table.add_row(filename, str(lines), f"{size:,} bytes")

            self.console.print(size_table)
            self.console.print()

    def _display_generic_output(self, output: Dict[str, Any]):
        """Generic output display."""
        # Pretty print JSON
        json_str = json.dumps(output, indent=2, ensure_ascii=False)
        preview = "\n".join(json_str.split("\n")[:50])

        syntax = Syntax(preview, "json", theme="monokai", line_numbers=True)

        self.console.print(Panel(syntax, title="Phase Output (JSON)", border_style="blue"))
        self.console.print()


def create_rich_review_handler(console: Optional[Console] = None) -> RichReviewHandler:
    """
    Factory function to create Rich review handler.

    Args:
        console: Optional Console instance

    Returns:
        RichReviewHandler instance
    """
    return RichReviewHandler(console=console)
