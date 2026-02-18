"""
Validate Command

Run specific validators on agent/task design
"""


import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    handle_keyboard_interrupt,
    load_json,
    print_validation_results,
    save_json,
)


@click.command()
@click.option(
    "--validator",
    type=click.Choice(
        ["ontology", "golden", "dependency", "python311", "crewai", "all"]
    ),
    default="all",
    help="Validator to run (default: all)",
)
@click.option(
    "--agents",
    type=click.Path(exists=True),
    required=True,
    help="Path to agents.json file",
)
@click.option(
    "--tasks",
    type=click.Path(exists=True),
    required=True,
    help="Path to tasks.json file",
)
@click.option(
    "--golden-data",
    type=click.Path(exists=True),
    help="Path to golden_data.json (required for golden validator)",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Save validation report to JSON file"
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed validation output")
@handle_keyboard_interrupt
def validate(validator, agents, tasks, golden_data, output, verbose):
    """
    Run specific validators on agent/task design

    \b
    AVAILABLE VALIDATORS:
    ═══════════════════════════════════════════════════════════════════════════
    • ontology     - Validate agent/task ontology structure
    • golden       - Validate against Golden Data requirements
    • dependency   - Check task dependencies and ordering
    • python311    - Verify Python 3.11+ compatibility
    • crewai       - Validate CrewAI framework compliance
    • all          - Run all validators (default)

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Run all validators:
       $ caas validate --agents agents.json --tasks tasks.json

    \b
    2️⃣  Run ontology validation only:
       $ caas validate --validator ontology \\
           --agents agents.json --tasks tasks.json

    \b
    3️⃣  Validate against Golden Data:
       $ caas validate --validator golden \\
           --agents agents.json --tasks tasks.json \\
           --golden-data golden_data.json

    \b
    4️⃣  Save validation report:
       $ caas validate --agents agents.json --tasks tasks.json \\
           --output validation_report.json

    \b
    5️⃣  Verbose output:
       $ caas validate --validator all --agents agents.json --tasks tasks.json -v
    """
    try:
        echo_info(f"Running {validator} validation...")
        click.echo()

        # Load agents and tasks
        echo_progress("Loading agent and task specifications...")
        agents_list = load_json(agents)
        tasks_list = load_json(tasks)

        # Load golden data if needed
        golden_data_dict = None
        if golden_data:
            golden_data_dict = load_json(golden_data)
        elif validator == "golden":
            echo_error("Golden Data is required for 'golden' validator")
            echo_info("Use --golden-data option to provide golden_data.json")
            return

        # Run validation
        result = None

        if validator == "ontology":
            result = _validate_ontology(agents_list, tasks_list, verbose)
        elif validator == "golden":
            result = _validate_golden(
                agents_list, tasks_list, golden_data_dict, verbose
            )
        elif validator == "dependency":
            result = _validate_dependency(agents_list, tasks_list, verbose)
        elif validator == "python311":
            result = _validate_python311(agents_list, tasks_list, verbose)
        elif validator == "crewai":
            result = _validate_crewai(agents_list, tasks_list, verbose)
        elif validator == "all":
            result = _validate_all(agents_list, tasks_list, golden_data_dict, verbose)

        # Print results
        click.echo()
        print_validation_results(result)

        # Save report if requested
        if output:
            click.echo()
            save_json(output, result)

        # Exit with error code if validation failed
        if hasattr(result, "is_valid") and not result.is_valid:
            return 1

    except ImportError as e:
        echo_error(f"Failed to import validation modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Validation error: {e}")
        import traceback

        if verbose:
            echo_error(traceback.format_exc())
        return 1


def _validate_ontology(agents_list, tasks_list, verbose):
    """Run ontology validation"""
    from caas_framework.validation.ontology_validator import OntologyValidator

    echo_progress("Validating ontology structure...")

    validator = OntologyValidator()
    result = validator.validate_agents_and_tasks(agents_list, tasks_list)

    if verbose:
        click.echo()
        echo_info("Ontology Validation Details:")
        click.echo(f"  Agents validated: {len(agents_list)}")
        click.echo(f"  Tasks validated: {len(tasks_list)}")

    return result


def _validate_golden(agents_list, tasks_list, golden_data, verbose):
    """Run golden data validation"""
    from caas_framework.models.specifications import (
        ConcretizedRequirement as GoldenData,
    )
    from caas_framework.validation.golden_validator import GoldenDataValidator

    echo_progress("Validating against Golden Data...")

    # Convert dict to GoldenData model if needed
    if isinstance(golden_data, dict):
        golden_data = GoldenData(**golden_data)

    validator = GoldenDataValidator(golden_data)
    result = validator.validate(agents_list, tasks_list)

    if verbose:
        click.echo()
        echo_info("Golden Data Validation Details:")
        click.echo(f"  Features in Golden Data: {len(golden_data.features)}")
        click.echo(f"  Agents validated: {len(agents_list)}")
        click.echo(f"  Tasks validated: {len(tasks_list)}")

    return result


def _validate_dependency(agents_list, tasks_list, verbose):
    """Run dependency validation"""
    from caas_framework.models.validation import ValidationIssue, ValidationResult, ValidationSeverity
    from caas_framework.validation.dependency_validator import DependencyValidator

    echo_progress("Validating task dependencies...")

    validator = DependencyValidator(tasks_list)
    is_valid, issues = validator.validate()

    # Convert dependency issues to ValidationIssue objects
    validation_issues = []
    for issue in issues:
        validation_issues.append(
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="dependency",
                message=str(issue),
            )
        )

    result = ValidationResult(is_valid=is_valid, issues=validation_issues)

    if verbose:
        click.echo()
        echo_info("Dependency Validation Details:")
        click.echo(f"  Tasks validated: {len(tasks_list)}")
        click.echo(f"  Issues found: {len(issues)}")

    return result


def _validate_python311(agents_list, tasks_list, verbose):
    """Run Python 3.11+ compatibility validation"""
    from caas_framework.validation.python311_validator import Python311Validator

    echo_progress("Validating Python 3.11+ compatibility...")

    # Build synthetic code from agent/task specs for validation
    files = {}
    for i, agent in enumerate(agents_list):
        name = agent.get("name", f"agent_{i}") if isinstance(agent, dict) else f"agent_{i}"
        role = agent.get("role", "Agent") if isinstance(agent, dict) else "Agent"
        goal = agent.get("goal", "") if isinstance(agent, dict) else ""
        files[f"agent_{i}.py"] = f'# Agent: {name}\n# Role: {role}\n# Goal: {goal}\n'
    for i, task in enumerate(tasks_list):
        name = task.get("name", f"task_{i}") if isinstance(task, dict) else f"task_{i}"
        files[f"task_{i}.py"] = f'# Task: {name}\n'

    validator = Python311Validator()
    result = validator.validate(files)

    if verbose:
        click.echo()
        echo_info("Python 3.11+ Validation Details:")
        click.echo(f"  Agents validated: {len(agents_list)}")
        click.echo(f"  Tasks validated: {len(tasks_list)}")

    return result


def _validate_crewai(agents_list, tasks_list, verbose):
    """Run CrewAI framework compliance validation"""
    from caas_framework.models.validation import ValidationResult
    from caas_framework.validation.crewai_validator import CrewAIValidator

    echo_progress("Validating CrewAI framework compliance...")

    validator = CrewAIValidator()
    all_issues = []

    # Validate each agent's synthesized code
    for agent in agents_list:
        if isinstance(agent, dict):
            name = agent.get("name", "Agent")
            role = agent.get("role", "Role")
            goal = agent.get("goal", "Goal")
            backstory = agent.get("backstory", "Backstory")
            tools_str = str(agent.get("tools", []))
        else:
            name, role, goal, backstory, tools_str = "Agent", "Role", "Goal", "Backstory", "[]"
        code = (
            f"from crewai import Agent\n"
            f"{name.replace(' ', '_')} = Agent(\n"
            f"    role='{role}',\n"
            f"    goal='{goal}',\n"
            f"    backstory='{backstory}',\n"
            f"    tools={tools_str},\n"
            f")\n"
        )
        agent_result = validator.validate_agent_code(code)
        all_issues.extend(agent_result.issues)

    # Validate each task's synthesized code
    for task in tasks_list:
        if isinstance(task, dict):
            name = task.get("name", "Task")
            desc = task.get("description", "Description")
            output = task.get("expected_output", "Output")
        else:
            name, desc, output = "Task", "Description", "Output"
        code = (
            f"from crewai import Task\n"
            f"{name.replace(' ', '_')} = Task(\n"
            f"    description='{desc}',\n"
            f"    expected_output='{output}',\n"
            f")\n"
        )
        task_result = validator.validate_task_code(code)
        all_issues.extend(task_result.issues)

    from caas_framework.models.validation import ValidationSeverity
    is_valid = all(
        (i.severity.value if hasattr(i.severity, "value") else i.severity) != "error"
        for i in all_issues
    )
    result = ValidationResult(is_valid=is_valid, issues=all_issues)

    if verbose:
        click.echo()
        echo_info("CrewAI Validation Details:")
        click.echo(f"  Agents validated: {len(agents_list)}")
        click.echo(f"  Tasks validated: {len(tasks_list)}")

    return result


def _validate_all(agents_list, tasks_list, golden_data, verbose):
    """Run all validators"""
    from caas_framework.models.specifications import (
        ConcretizedRequirement as GoldenData,
    )
    from caas_framework.validation.orchestrator import ValidationOrchestrator

    echo_progress("Running all validators...")

    # Convert dict to GoldenData model if provided
    golden_data_obj = None
    if golden_data:
        if isinstance(golden_data, dict):
            golden_data_obj = GoldenData(**golden_data)
        else:
            golden_data_obj = golden_data

    orchestrator = ValidationOrchestrator(golden_data=golden_data_obj)
    result = orchestrator.validate_design(agents_list, tasks_list)

    if verbose:
        click.echo()
        echo_info("All Validators Results:")
        click.echo(f"  Agents validated: {len(agents_list)}")
        click.echo(f"  Tasks validated: {len(tasks_list)}")
        if golden_data_obj:
            click.echo(f"  Golden Data features: {len(golden_data_obj.features)}")

    return result
