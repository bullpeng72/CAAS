"""
Generate Code Command

Generate production-ready code from spec (agents.json + tasks.json)
"""


import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    handle_keyboard_interrupt,
    initialize_framework,
    load_json,
)


@click.command(name="generate-code")
@click.option(
    "--agents", type=click.Path(exists=True), required=True, help="Path to agents.json file"
)
@click.option(
    "--tasks", type=click.Path(exists=True), required=True, help="Path to tasks.json file"
)
@click.option(
    "--golden-data",
    type=click.Path(exists=True),
    help="Path to golden_data.json (optional, recommended for better code)",
)
@click.option(
    "--deployment-target",
    type=click.Choice(["docker", "kubernetes", "terraform"]),
    default="docker",
    help="Deployment target (default: docker)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./generated_code",
    help="Output directory (default: ./generated_code)",
)
@click.option("--project-name", type=str, help="Project name (default: derived from spec)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed generation output")
@click.option("--tdd", is_flag=True, help="Enable Test-First Code Generation (TDD approach)")
@handle_keyboard_interrupt
async def generate_code(
    agents, tasks, golden_data, deployment_target, output, project_name, verbose, tdd
):
    """
    Generate production-ready code from spec

    \b
    PURPOSE:
    ═══════════════════════════════════════════════════════════════════════════
    Generate complete production code from agent/task specifications.
    This is the final step after design validation.

    \b
    DIFFERENCE FROM OTHER COMMANDS:
    ═══════════════════════════════════════════════════════════════════════════
    • generate           - Full workflow (requirement → code)
    • codegen            - Specific components (tests/deployment/frontend/docs)
    • generate-code      - Production code only (agents.py, tasks.py, crew.py)

    \b
    GENERATED FILES:
    ═══════════════════════════════════════════════════════════════════════════
    \b
    Production Code:
    • src/agents.py           - Agent definitions
    • src/tasks.py            - Task definitions
    • src/crew.py             - Crew configuration
    • src/tools.py            - Custom tools
    • main.py                 - Entry point
    • requirements.txt        - Dependencies
    • README.md               - Documentation
    • .env.example            - Environment template
    \b
    Tests:
    • tests/test_agents.py    - Agent tests
    • tests/test_tasks.py     - Task tests
    • tests/test_crew.py      - Crew tests
    • tests/conftest.py       - Test configuration
    \b
    Deployment:
    • Dockerfile              - Container definition
    • docker-compose.yml      - Service orchestration
    • .dockerignore           - Docker ignore rules

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Basic code generation:
       $ caas generate-code \\
           --agents agents.json \\
           --tasks tasks.json

    \b
    2️⃣  With Golden Data (recommended):
       $ caas generate-code \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json

    \b
    3️⃣  Custom output & deployment target:
       $ caas generate-code \\
           --agents agents.json \\
           --tasks tasks.json \\
           --output ./my_project \\
           --deployment-target kubernetes

    \b
    4️⃣  With project name:
       $ caas generate-code \\
           --agents agents.json \\
           --tasks tasks.json \\
           --project-name "my_awesome_crew"

    \b
    5️⃣  Verbose output:
       $ caas generate-code \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json \\
           --verbose

    \b
    6️⃣  Test-First (TDD) mode:
       $ caas generate-code \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json \\
           --tdd

    \b
    TDD MODE:
    ═══════════════════════════════════════════════════════════════════════════
    When --tdd flag is enabled, code is generated using Test-Driven Development:
    • 🔴 RED Phase: Tests are generated FIRST from acceptance criteria
    • 🟢 GREEN Phase: Minimal implementation to pass tests
    • 🔵 REFACTOR Phase: Iterative refinement until all tests pass (max 3 iterations)

    TDD mode requires Golden Data with feature specifications and acceptance criteria.
    Tests are generated before implementation, ensuring high quality and coverage.

    \b
    WORKFLOW:
    ═══════════════════════════════════════════════════════════════════════════
    Design Phase (caas validate/fix) → generate-code → Production Code

    \b
    TYPICAL WORKFLOW:
       $ caas generate "Build chatbot" -o design/
       $ caas validate --agents design/agents.json --tasks design/tasks.json
       $ caas generate-code \\
           --agents design/agents.json \\
           --tasks design/tasks.json \\
           --golden-data design/golden_data.json \\
           --output production/

    \b
    NOTES:
    ═══════════════════════════════════════════════════════════════════════════
    • Requires valid agents.json and tasks.json
    • Golden Data is optional but highly recommended
    • Output directory will be created if it doesn't exist
    • Existing files will be overwritten
    """
    try:
        echo_info("Generating production-ready code from spec...")
        click.echo()

        # Load specifications
        echo_progress("Loading specifications...")
        agents_list = load_json(agents)
        tasks_list = load_json(tasks)

        if verbose:
            echo_info(f"Agents loaded: {len(agents_list)}")
            echo_info(f"Tasks loaded: {len(tasks_list)}")

        # Load golden data if provided
        golden_data_dict = None
        if golden_data:
            golden_data_dict = load_json(golden_data)
            if verbose:
                echo_info(
                    f"Golden Data loaded: {len(golden_data_dict.get('features', []))} features"
                )

        # Build spec
        spec = {"agents": agents_list, "tasks": tasks_list, "deployment_target": deployment_target}

        if golden_data_dict:
            spec["golden_data"] = golden_data_dict

        if project_name:
            spec["project_name"] = project_name

        # Initialize framework
        click.echo()
        echo_progress("Initializing framework...")
        framework = await initialize_framework()

        # Generate code
        click.echo()
        if tdd:
            echo_progress("Generating code using Test-First approach (TDD)...")
            click.echo()
            echo_info("🔴 RED Phase: Generating tests first...")
            echo_info("🟢 GREEN Phase: Generating minimal implementation...")
            echo_info("🔵 REFACTOR Phase: Iterative refinement...")
            click.echo()
        else:
            echo_progress("Generating production code...")
            click.echo()

        result = await framework.generate_code(
            spec=spec,
            output_dir=output,
            deployment_target=deployment_target,
            tdd_mode=tdd,  # Pass TDD flag to framework
        )

        await framework.close()

        # Check result
        if result.success:
            click.echo()
            echo_success("Code generation completed!")

            # Show summary
            click.echo()
            click.echo(click.style("Summary:", bold=True))
            click.echo(f"  Files generated:   {len(result.files)}")
            click.echo(f"  Output directory:  {output}")
            click.echo(f"  Deployment target: {deployment_target}")

            if verbose:
                click.echo()
                click.echo(click.style("Generated files:", bold=True))
                for file_path in sorted(result.files.keys()):
                    click.echo(f"  • {file_path}")

            # Show next steps
            click.echo()
            click.echo(click.style("Next steps:", bold=True))
            click.echo(f"  1. cd {output}")
            click.echo("  2. Review generated code")
            click.echo("  3. Create .env file: cp .env.example .env")
            click.echo("  4. Install dependencies: pip install -r requirements.txt")
            click.echo("  5. Run tests: pytest tests/")
            click.echo(f"  6. Run with {deployment_target}")

            return 0

        else:
            echo_error("Code generation failed!")
            if hasattr(result, "errors") and result.errors:
                click.echo()
                click.echo(click.style("Errors:", bold=True))
                for error in result.errors:
                    click.echo(f"  - {error}")
            return 1

    except ImportError as e:
        echo_error(f"Failed to import framework: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Code generation error: {e}")
        import traceback

        if verbose:
            echo_error(traceback.format_exc())
        return 1
