"""
TDD Code Generation CLI Command

CLI command for generating code using test-driven development approach.

Part of CAAS-E Week 4 implementation (Task 4.2).
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from caas_framework.codegen.tdd_orchestrator import TDDOrchestrator, TDDWorkflowConfig
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel,
)
from caas_framework.plugins.llm.factory import create_llm_plugin
from caas_framework.config.loader import load_config

console = Console()


@click.command("generate-tdd")
@click.option(
    "--tests",
    "-t",
    type=click.Path(exists=True),
    required=True,
    help="Directory containing test files",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./generated",
    help="Output directory for generated code (default: ./generated)",
)
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    default=None,
    help="Path to Golden Data JSON file (optional context)",
)
@click.option(
    "--agents",
    "-a",
    type=click.Path(exists=True),
    default=None,
    help="Path to agents JSON file (optional context)",
)
@click.option(
    "--tasks",
    "-k",
    type=click.Path(exists=True),
    default=None,
    help="Path to tasks JSON file (optional context)",
)
@click.option(
    "--specs",
    "-s",
    type=click.Path(exists=True),
    default=None,
    help="Directory with YAML specs (optional context)",
)
@click.option(
    "--max-iterations",
    type=int,
    default=3,
    help="Maximum refinement iterations (default: 3)",
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Timeout per test in seconds (default: 30)",
)
@click.option(
    "--require-all-pass",
    is_flag=True,
    default=True,
    help="Require all tests to pass (default: True)",
)
def generate_tdd_cmd(
    tests: str,
    output: str,
    golden_data: Optional[str],
    agents: Optional[str],
    tasks: Optional[str],
    specs: Optional[str],
    max_iterations: int,
    timeout: int,
    require_all_pass: bool,
):
    """
    Generate code using Test-Driven Development (TDD) approach.

    Workflow:
    1. Parse test files to extract requirements
    2. Generate code to pass tests
    3. Run tests iteratively
    4. Refine code until tests pass (max 3 iterations)

    Examples:

    \b
    # Generate code from tests
    caas generate-tdd -t ./tests -o ./generated

    \b
    # With context (Golden Data, agents, tasks)
    caas generate-tdd -t ./tests -o ./generated -g golden.json -a agents.json

    \b
    # With YAML specs
    caas generate-tdd -t ./tests -o ./generated -s ./specs

    \b
    # Custom iterations and timeout
    caas generate-tdd -t ./tests -o ./generated --max-iterations 5 --timeout 60
    """
    asyncio.run(
        _generate_tdd(
            tests,
            output,
            golden_data,
            agents,
            tasks,
            specs,
            max_iterations,
            timeout,
            require_all_pass,
        )
    )


async def _generate_tdd(
    tests_path: str,
    output_dir: str,
    golden_data_path: Optional[str],
    agents_path: Optional[str],
    tasks_path: Optional[str],
    specs_path: Optional[str],
    max_iterations: int,
    timeout: int,
    require_all_pass: bool,
):
    """Async implementation of generate-tdd command."""
    console.print("\n[bold cyan]🧪 TDD Code Generation Workflow[/bold cyan]\n")

    # Step 1: Load context (if provided)
    golden_data = None
    agents_list = None
    tasks_list = None

    if golden_data_path:
        console.print("📖 Loading Golden Data...", style="dim")
        golden_data = _load_golden_data(golden_data_path)
        console.print(f"  ✅ Loaded: {golden_data.project_name}", style="green")

    if agents_path:
        console.print("📖 Loading Agents...", style="dim")
        agents_list = _load_agents(agents_path)
        console.print(f"  ✅ Loaded {len(agents_list)} agents", style="green")

    if tasks_path:
        console.print("📖 Loading Tasks...", style="dim")
        tasks_list = _load_tasks(tasks_path)
        console.print(f"  ✅ Loaded {len(tasks_list)} tasks", style="green")

    # Step 2: Initialize TDD Orchestrator
    config = load_config()
    llm = create_llm_plugin(config)

    tdd_config = TDDWorkflowConfig(
        max_iterations=max_iterations,
        timeout_per_test=timeout,
        require_all_tests_pass=require_all_pass,
    )

    orchestrator = TDDOrchestrator(llm_plugin=llm, config=tdd_config)

    # Step 3: Run TDD workflow
    console.print(f"\n🚀 Starting TDD workflow...", style="bold cyan")
    console.print(f"  Tests: {tests_path}")
    console.print(f"  Output: {output_dir}")
    console.print(f"  Max iterations: {max_iterations}")
    console.print("")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating code...", total=None)

        result = await orchestrator.generate_with_tests(
            test_dir=Path(tests_path),
            output_dir=Path(output_dir),
            golden_data=golden_data,
            agents=agents_list,
            tasks=tasks_list,
            specs_dir=Path(specs_path) if specs_path else None,
        )

        progress.remove_task(task)

    # Step 4: Display results
    _display_results(result, output_dir)


def _load_golden_data(file_path: str) -> ConcretizedRequirement:
    """Load Golden Data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ConcretizedRequirement(**data)
    except Exception as e:
        console.print(f"❌ Failed to load Golden Data: {e}", style="bold red")
        raise click.Abort()


def _load_agents(file_path: str) -> list[AgentSpecModel]:
    """Load agents from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            agents_data = data
        elif isinstance(data, dict) and "agents" in data:
            agents_data = data["agents"]
        else:
            raise ValueError("Invalid agents file format")

        return [AgentSpecModel(**agent) for agent in agents_data]
    except Exception as e:
        console.print(f"❌ Failed to load agents: {e}", style="bold red")
        raise click.Abort()


def _load_tasks(file_path: str) -> list[TaskSpecModel]:
    """Load tasks from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            tasks_data = data
        elif isinstance(data, dict) and "tasks" in data:
            tasks_data = data["tasks"]
        else:
            raise ValueError("Invalid tasks file format")

        return [TaskSpecModel(**task) for task in tasks_data]
    except Exception as e:
        console.print(f"❌ Failed to load tasks: {e}", style="bold red")
        raise click.Abort()


def _display_results(result, output_dir: str):
    """Display TDD generation results."""
    if result.success:
        console.print("\n✅ [bold green]TDD Generation Successful![/bold green]\n")
    else:
        console.print("\n⚠️ [bold yellow]TDD Generation Incomplete[/bold yellow]\n")

    # Iterations table
    table = Table(title="Generation Iterations")
    table.add_column("Iteration", style="cyan", no_wrap=True)
    table.add_column("Tests Passed", style="green", justify="center")
    table.add_column("Tests Failed", style="red", justify="center")
    table.add_column("Status", justify="center")

    for iteration in result.iterations:
        status = "✅ Pass" if iteration.failed_count == 0 else "🔄 Refine"
        table.add_row(
            str(iteration.iteration),
            str(iteration.passed_count),
            str(iteration.failed_count),
            status,
        )

    console.print(table)

    # Summary panel
    summary_text = f"""
[bold]Total Tests:[/bold] {result.total_tests}
[bold]Passed:[/bold] [green]{result.passed_tests}[/green]
[bold]Failed:[/bold] [red]{result.failed_tests}[/red]
[bold]Iterations:[/bold] {len(result.iterations)}/{result.iterations[0].iteration if result.iterations else 0}
[bold]Generation Time:[/bold] {result.generation_time:.2f}s

[dim]Generated code:[/dim] {output_dir}/generated_code.py
    """

    console.print(
        Panel(
            summary_text.strip(),
            title="[bold cyan]TDD Results[/bold cyan]",
            border_style="green" if result.success else "yellow",
        )
    )

    # Next steps
    if result.success:
        console.print(
            f"\n💡 [bold yellow]Next Steps:[/bold yellow]"
            f"\n  1. Review generated code in {output_dir}/"
            f"\n  2. Run tests: pytest {output_dir}/"
            f"\n  3. Integrate into your project\n"
        )
    else:
        console.print(
            f"\n💡 [bold yellow]Troubleshooting:[/bold yellow]"
            f"\n  1. Review failing tests"
            f"\n  2. Increase max iterations: --max-iterations 5"
            f"\n  3. Check test expectations vs generated code"
            f"\n  4. Manually fix and rerun: pytest {output_dir}/\n"
        )
