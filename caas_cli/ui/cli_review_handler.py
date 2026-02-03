"""
CLI Review Handler

Implements ReviewHandler protocol for CLI-based user interaction.
Provides beautiful, interactive review UI using Rich library.
"""

from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from caas_framework.api import ReviewRequest, ReviewType


class CLIReviewHandler:
    """
    CLI-based review handler implementation.

    Displays review data in beautiful CLI format and gets user decisions.
    Uses Rich library for formatting, colors, and interactivity.
    """

    def __init__(self, console: Console = None):
        """
        Initialize CLI review handler.

        Args:
            console: Optional Rich Console instance (creates new if not provided)
        """
        self.console = console or Console()

    def handle_review(self, request: ReviewRequest) -> str:
        """
        Handle a review request and return user decision.

        Args:
            request: Review request with UI-independent data

        Returns:
            User decision: one of request.options (e.g., "approve", "edit", "reject")
        """
        # Display appropriate review based on type
        if request.review_type == ReviewType.REQUIREMENTS:
            self._display_requirements_review(request.data)
        elif request.review_type == ReviewType.DESIGN:
            self._display_design_review(request.data)
        elif request.review_type == ReviewType.CODE:
            self._display_code_review(request.data)

        # Get user decision
        return self._get_user_decision(request.options)

    def _display_requirements_review(self, data: Dict[str, Any]) -> None:
        """
        Display requirements review in CLI.

        Shows:
        - Project name and description
        - Features table
        - Data models
        - Security boundaries
        """
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold yellow]📋 Requirements Review[/bold yellow]")
        self.console.print("=" * 70 + "\n")

        # Project info
        project_name = data.get("project_name", "N/A")
        description = data.get("description", "N/A")

        self.console.print(f"[bold]Project:[/bold] [cyan]{project_name}[/cyan]")
        if description and description != "N/A":
            self.console.print(f"[bold]Description:[/bold] {description}")
        self.console.print()

        # Features table
        features = data.get("features", [])
        if features:
            self.console.print("[bold green]✨ Features[/bold green]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan", width=20)
            table.add_column("Description", width=40)
            table.add_column("Priority", justify="center", width=10)

            for feature in features:
                name = feature.get("name", "N/A")
                desc = feature.get("description", "N/A")
                priority = feature.get("priority", "medium")

                # Color priority
                if priority == "high":
                    priority_str = f"[red]{priority}[/red]"
                elif priority == "medium":
                    priority_str = f"[yellow]{priority}[/yellow]"
                else:
                    priority_str = f"[green]{priority}[/green]"

                table.add_row(name, desc, priority_str)

            self.console.print(table)
            self.console.print()

        # Data models
        data_models = data.get("data_models", [])
        if data_models:
            self.console.print("[bold blue]📊 Data Models[/bold blue]\n")

            for model in data_models:
                name = model.get("name", "Unknown")
                attr_count = model.get("attributes_count", 0)
                self.console.print(f"  • {name} ({attr_count} attributes)")

            self.console.print()

        # Security boundaries
        boundaries = data.get("boundaries")
        if boundaries:
            self._display_boundaries(boundaries)

    def _display_design_review(self, data: Dict[str, Any]) -> None:
        """
        Display design review in CLI.

        Shows:
        - Agents table
        - Tasks table
        - Agent-Task relationships
        """
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold yellow]🎨 Design Review[/bold yellow]")
        self.console.print("=" * 70 + "\n")

        # Agents table
        agents = data.get("agents", [])
        if agents:
            self.console.print("[bold green]🤖 Agents[/bold green]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", width=15)
            table.add_column("Role", style="yellow", width=20)
            table.add_column("Goal", width=30)
            table.add_column("Tools", width=15)

            for agent in agents:
                agent_id = agent.get("id", "N/A")
                role = agent.get("role", "N/A")
                goal = agent.get("goal", "N/A")
                tools = agent.get("tools", [])

                # Truncate long goal
                if len(goal) > 30:
                    goal = goal[:27] + "..."

                tools_str = f"{len(tools)} tools" if tools else "No tools"

                table.add_row(agent_id, role, goal, tools_str)

            self.console.print(table)
            self.console.print()

        # Tasks table
        tasks = data.get("tasks", [])
        if tasks:
            self.console.print("[bold blue]📋 Tasks[/bold blue]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", width=15)
            table.add_column("Description", width=40)
            table.add_column("Agent", style="yellow", width=15)

            for task in tasks:
                task_id = task.get("id", "N/A")
                description = task.get("description", "N/A")
                agent = task.get("agent", "N/A")

                # Truncate long description
                if len(description) > 40:
                    description = description[:37] + "..."

                table.add_row(task_id, description, agent)

            self.console.print(table)
            self.console.print()

    def _display_code_review(self, data: Dict[str, Any]) -> None:
        """
        Display code review in CLI.

        Shows:
        - File list with sizes
        - Total statistics
        - Preview of main.py (if available)
        """
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold yellow]💻 Code Review[/bold yellow]")
        self.console.print("=" * 70 + "\n")

        # Statistics
        total_files = data.get("total_files", 0)
        total_lines = data.get("total_lines", 0)

        stats_panel = f"""[bold]Statistics:[/bold]
• Total Files: [cyan]{total_files}[/cyan]
• Total Lines: [cyan]{total_lines}[/cyan]
"""
        self.console.print(Panel(stats_panel, title="📊 Code Statistics", border_style="green"))
        self.console.print()

        # Files table
        files = data.get("files", {})
        if files:
            self.console.print("[bold green]📁 Generated Files[/bold green]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Filename", style="cyan", width=25)
            table.add_column("Lines", justify="right", width=10)
            table.add_column("Size (KB)", justify="right", width=12)

            for filename, file_info in files.items():
                lines = file_info.get("lines", 0)
                size_kb = file_info.get("size_kb", 0)

                table.add_row(filename, str(lines), f"{size_kb:.2f}")

            self.console.print(table)
            self.console.print()

        # Preview of main.py
        if "main.py" in files and files["main.py"].get("preview"):
            preview = files["main.py"]["preview"]
            self.console.print("[bold blue]👀 Preview: main.py[/bold blue]\n")

            syntax = Syntax(preview, "python", theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, border_style="blue"))
            self.console.print()

    def _display_boundaries(self, boundaries: Dict[str, List[str]]) -> None:
        """
        Display security boundaries in colored format.

        Args:
            boundaries: Dict with always_allowed, ask_first, never_allowed lists
        """
        panel_content = []

        always_allowed = boundaries.get("always_allowed", [])
        if always_allowed:
            panel_content.append("[bold green]✅ Always Allowed:[/bold green]")
            for item in always_allowed:
                panel_content.append(f"  • {item}")
            panel_content.append("")

        ask_first = boundaries.get("ask_first", [])
        if ask_first:
            panel_content.append("[bold yellow]⚠️  Ask First:[/bold yellow]")
            for item in ask_first:
                panel_content.append(f"  • {item}")
            panel_content.append("")

        never_allowed = boundaries.get("never_allowed", [])
        if never_allowed:
            panel_content.append("[bold red]❌ Never Allowed:[/bold red]")
            for item in never_allowed:
                panel_content.append(f"  • {item}")

        if panel_content:
            self.console.print(
                Panel("\n".join(panel_content), title="🔒 Security Boundaries", border_style="cyan")
            )
            self.console.print()

    def _get_user_decision(self, options: List[str]) -> str:
        """
        Get user decision via CLI input.

        Args:
            options: List of valid options (e.g., ["approve", "edit", "reject"])

        Returns:
            User's chosen option
        """
        self.console.print("=" * 70)

        # Display options with colors
        options_str = " / ".join([f"[cyan]{opt}[/cyan]" for opt in options])

        while True:
            self.console.print(f"\n[bold]Your Decision ({options_str}):[/bold] ", end="")

            # Get input (Rich doesn't have input method, use built-in)
            try:
                choice = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[red]Aborted by user[/red]")
                return "reject"

            if choice in options:
                self.console.print(f"[green]✓ Selected: {choice}[/green]\n")
                return choice

            self.console.print(
                f"[red]Invalid choice. Please choose one of: {', '.join(options)}[/red]"
            )


class AutoApproveHandler:
    """
    Auto-approve handler for testing/automation.

    Always returns "approve" without user interaction.
    Useful for CI/CD, testing, or headless mode.
    """

    def __init__(self):
        self.console = Console()

    def handle_review(self, request: ReviewRequest) -> str:
        """Always approve without user interaction."""
        self.console.print(f"[dim]Auto-approving {request.review_type.value} review...[/dim]")
        return "approve"
