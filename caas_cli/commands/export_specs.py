"""
Export Specifications CLI Command

CLI command for exporting Golden Data and specifications to YAML files.

Part of CAAS-E Week 4 implementation (Task 4.1).
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from caas_framework.sdd.yaml_exporter import export_specifications
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    AgentSpecModel,
    TaskSpecModel,
)

console = Console()


@click.command("export-specs")
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    required=True,
    help="Path to Golden Data JSON file",
)
@click.option(
    "--agents",
    "-a",
    type=click.Path(exists=True),
    default=None,
    help="Path to agents JSON file (optional)",
)
@click.option(
    "--tasks",
    "-t",
    type=click.Path(exists=True),
    default=None,
    help="Path to tasks JSON file (optional)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./specs",
    help="Output directory for YAML files (default: ./specs)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "yml"]),
    default="yaml",
    help="Output format (default: yaml)",
)
@click.option(
    "--include-api-contracts",
    is_flag=True,
    default=False,
    help="Include api_contracts.yaml (bonus file)",
)
def export_specs_cmd(
    golden_data: str,
    agents: Optional[str],
    tasks: Optional[str],
    output: str,
    output_format: str,
    include_api_contracts: bool,
):
    """
    Export specifications to YAML files for SDD (Spec-Driven Development).

    Generates 5 YAML files:
    - agent_specs.yaml
    - task_specs.yaml
    - tool_specs.yaml
    - data_models.yaml
    - business_rules.yaml

    Examples:

    \b
    # Export from Golden Data only
    caas export-specs -g golden_data.json -o ./specs

    \b
    # Export with agents and tasks
    caas export-specs -g golden_data.json -a agents.json -t tasks.json -o ./specs

    \b
    # Include API contracts
    caas export-specs -g golden_data.json -o ./specs --include-api-contracts
    """
    asyncio.run(
        _export_specs(
            golden_data,
            agents,
            tasks,
            output,
            output_format,
            include_api_contracts,
        )
    )


async def _export_specs(
    golden_data_path: str,
    agents_path: Optional[str],
    tasks_path: Optional[str],
    output_dir: str,
    output_format: str,
    include_api_contracts: bool,
):
    """Async implementation of export-specs command."""
    console.print("\n[bold cyan]📤 Exporting Specifications to YAML[/bold cyan]\n")

    # Step 1: Load Golden Data
    console.print("📖 Loading Golden Data...", style="dim")
    golden_data = _load_golden_data(golden_data_path)
    console.print(f"  ✅ Loaded: {golden_data.project_name}", style="green")

    # Step 2: Load Agents (if provided)
    agents_list = None
    if agents_path:
        console.print("📖 Loading Agents...", style="dim")
        agents_list = _load_agents(agents_path)
        console.print(f"  ✅ Loaded {len(agents_list)} agents", style="green")

    # Step 3: Load Tasks (if provided)
    tasks_list = None
    if tasks_path:
        console.print("📖 Loading Tasks...", style="dim")
        tasks_list = _load_tasks(tasks_path)
        console.print(f"  ✅ Loaded {len(tasks_list)} tasks", style="green")

    # Step 4: Export specifications
    console.print(f"\n📝 Exporting to {output_dir}...", style="dim")

    exported_files = export_specifications(
        output_dir=Path(output_dir),
        golden_data=golden_data,
        agents=agents_list,
        tasks=tasks_list,
        include_api_contracts=include_api_contracts,
    )

    # Step 5: Display results
    _display_export_results(exported_files, output_dir)


def _load_golden_data(file_path: str) -> ConcretizedRequirement:
    """Load Golden Data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert to ConcretizedRequirement
        return ConcretizedRequirement(**data)

    except Exception as e:
        console.print(f"❌ Failed to load Golden Data: {e}", style="bold red")
        raise click.Abort()


def _load_agents(file_path: str) -> list[AgentSpecModel]:
    """Load agents from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different formats
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

        # Handle different formats
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


def _display_export_results(exported_files: dict, output_dir: str):
    """Display export results in a table."""
    console.print("\n✅ [bold green]Export Complete![/bold green]\n")

    # Create table
    table = Table(title="Exported Specification Files")
    table.add_column("Spec Type", style="cyan", no_wrap=True)
    table.add_column("File Name", style="green")
    table.add_column("Path", style="dim")

    for spec_type, file_path in exported_files.items():
        table.add_row(
            spec_type.replace("_", " ").title(),
            file_path.name,
            str(file_path),
        )

    console.print(table)

    # Summary panel
    summary_text = f"""
[bold]Total Files:[/bold] {len(exported_files)}
[bold]Output Directory:[/bold] {output_dir}

[dim]Use these YAML files for:[/dim]
  • Documentation and review
  • Test generation (TDD RED phase)
  • Code generation (Phase 5)
  • Validation and compliance
    """

    console.print(
        Panel(
            summary_text.strip(),
            title="[bold cyan]Export Summary[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print(
        f"\n💡 [bold yellow]Next Steps:[/bold yellow]"
        f"\n  1. Review YAML files in {output_dir}/"
        f"\n  2. Use for test generation: caas tdd generate-tests --specs {output_dir}"
        f"\n  3. Use for code generation: caas generate --specs {output_dir}\n"
    )
