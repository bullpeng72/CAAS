"""
Fix Command

Auto-fix design issues using 3-level strategy
"""

from pathlib import Path

import click
from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
    initialize_framework,
    load_json,
    save_json,
)


@click.command()
@click.option(
    "--agents", type=click.Path(exists=True), required=True, help="Path to agents.json file"
)
@click.option(
    "--tasks", type=click.Path(exists=True), required=True, help="Path to tasks.json file"
)
@click.option(
    "--golden-data",
    type=click.Path(exists=True),
    required=True,
    help="Path to golden_data.json (required for validation)",
)
@click.option(
    "--level",
    type=click.IntRange(1, 3),
    default=3,
    help="""Fix level (default: 3):
    \b
    Level 1: Template-based (fast, deterministic)
    Level 2: Rule-based (medium, pattern-matching)
    Level 3: LLM-based (slow, intelligent)""",
)
@click.option("--max-iterations", type=int, default=3, help="Maximum fix iterations (default: 3)")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./fixed_output",
    help="Output directory (default: ./fixed_output)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed fixing output")
@handle_keyboard_interrupt
async def fix(agents, tasks, golden_data, level, max_iterations, output, verbose):
    """
    Auto-fix design issues using 3-level strategy

    \b
    FIX LEVELS:
    ═══════════════════════════════════════════════════════════════════════════
    Level 1: Template-based
      • Fast and deterministic
      • Fixes common structural issues
      • No LLM calls required
      • Examples: Missing fields, invalid types

    Level 2: Rule-based
      • Medium complexity
      • Pattern-matching fixes
      • No LLM calls required
      • Examples: Dependency cycles, naming conflicts

    Level 3: LLM-based (Recommended)
      • Intelligent context-aware fixes
      • Requires LLM API
      • Handles complex semantic issues
      • Examples: Logic errors, requirement mismatches

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Auto-fix with LLM (recommended):
       $ caas fix \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json

    \b
    2️⃣  Quick template-based fixes only:
       $ caas fix \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json \\
           --level 1

    \b
    3️⃣  Rule-based fixes (no LLM):
       $ caas fix \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json \\
           --level 2

    \b
    4️⃣  Multiple iterations:
       $ caas fix \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json \\
           --max-iterations 5

    \b
    5️⃣  Custom output directory:
       $ caas fix \\
           --agents agents.json \\
           --tasks tasks.json \\
           --golden-data golden_data.json \\
           --output ./my_fixes

    \b
    FIX WORKFLOW:
    ═══════════════════════════════════════════════════════════════════════════
    1. Validate design against Golden Data
    2. Identify issues and categorize by severity
    3. Apply fixes based on selected level
    4. Re-validate to confirm fixes
    5. Iterate if issues remain (up to max-iterations)
    6. Save fixed agents.json and tasks.json

    \b
    OUTPUT:
    ═══════════════════════════════════════════════════════════════════════════
    • fixed_agents.json      - Corrected agent specifications
    • fixed_tasks.json       - Corrected task specifications
    • fix_report.json        - Detailed fix report with changes
    """
    try:
        echo_info(f"Auto-fixing with Level {level} strategy...")
        click.echo()

        # Load specifications
        echo_progress("Loading specifications...")
        agents_list = load_json(agents)
        tasks_list = load_json(tasks)
        golden_data_dict = load_json(golden_data)

        if verbose:
            echo_info(f"Agents: {len(agents_list)}")
            echo_info(f"Tasks: {len(tasks_list)}")
            echo_info(f"Golden Data features: {len(golden_data_dict.get('features', []))}")

        # Step 1: Validate to identify issues
        click.echo()
        echo_progress("Step 1/3: Validating design...")

        from caas_framework.models.specifications import ConcretizedRequirement as GoldenData
        from caas_framework.validation.golden_validator import GoldenDataValidator

        golden = GoldenData(**golden_data_dict)
        validator = GoldenDataValidator(golden)
        validation_report = validator.validate(agents_list, tasks_list)

        if not hasattr(validation_report, "errors") or not validation_report.errors:
            echo_success("No issues found! Design is valid.")
            return 0

        click.echo()
        echo_info(f"Found {len(validation_report.errors)} issues to fix")
        if verbose:
            for i, error in enumerate(validation_report.errors[:5], 1):
                click.echo(f"  {i}. {error}")
            if len(validation_report.errors) > 5:
                click.echo(f"  ... and {len(validation_report.errors) - 5} more")

        # Step 2: Apply fixes based on level
        click.echo()
        echo_progress(f"Step 2/3: Applying Level {level} fixes...")

        if level == 3:
            # LLM-based fixing
            fixed_result = await _fix_with_llm(
                agents_list, tasks_list, golden, validation_report, max_iterations, verbose
            )
        elif level == 2:
            # Rule-based fixing
            fixed_result = await _fix_with_rules(
                agents_list, tasks_list, golden, validation_report, verbose
            )
        else:
            # Template-based fixing
            fixed_result = await _fix_with_templates(
                agents_list, tasks_list, validation_report, verbose
            )

        # Step 3: Save fixed design
        click.echo()
        echo_progress("Step 3/3: Saving fixed design...")

        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save fixed agents and tasks
        save_json(output_path / "fixed_agents.json", fixed_result["agents"])
        save_json(output_path / "fixed_tasks.json", fixed_result["tasks"])

        # Save fix report
        fix_report = {
            "level": level,
            "iterations": fixed_result.get("iterations", 1),
            "issues_found": len(validation_report.errors),
            "issues_fixed": fixed_result.get("issues_fixed", 0),
            "changes": fixed_result.get("changes", []),
            "success": fixed_result.get("success", True),
        }
        save_json(output_path / "fix_report.json", fix_report)

        # Show summary
        click.echo()
        click.echo(click.style("Fix Summary:", bold=True))
        click.echo(f"  Level: {level}")
        click.echo(f"  Iterations: {fix_report['iterations']}")
        click.echo(f"  Issues found: {fix_report['issues_found']}")
        click.echo(f"  Issues fixed: {fix_report['issues_fixed']}")
        click.echo(f"  Changes made: {len(fix_report['changes'])}")

        if fix_report["success"]:
            echo_success("Auto-fix completed successfully!")
        else:
            echo_warning("Auto-fix completed with some remaining issues")

        # Show next steps
        click.echo()
        click.echo(click.style("Next steps:", bold=True))
        click.echo(f"  1. Review fixed files in {output}/")
        click.echo(f"  2. Check fix_report.json for details")
        click.echo(
            f"  3. Re-validate: caas validate --agents {output}/fixed_agents.json --tasks {output}/fixed_tasks.json"
        )

        return 0 if fix_report["success"] else 1

    except ImportError as e:
        echo_error(f"Failed to import fix modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Fix error: {e}")
        import traceback

        if verbose:
            echo_error(traceback.format_exc())
        return 1


async def _fix_with_llm(
    agents_list, tasks_list, golden_data, validation_report, max_iterations, verbose
):
    """Fix using LLM (Level 3)"""
    from caas_framework.fixing.auto_fixer import AutoFixer

    echo_info("Using LLM-based intelligent fixing...")

    # Initialize framework
    framework = await initialize_framework()

    try:
        # Get LLM plugin from framework
        llm_plugin = framework.llm_plugin

        # Create auto fixer
        fixer = AutoFixer(golden_data=golden_data, llm_plugin=llm_plugin)

        # Apply fixes
        result = await fixer.fix_design(agents_list, tasks_list, validation_report, max_iterations)

        if verbose:
            click.echo()
            echo_info(f"Completed {result.iterations_used} iterations")
            echo_info(f"Fixed {result.issues_fixed} issues")

        await framework.close()

        return {
            "agents": result.fixed_output["agents"],
            "tasks": result.fixed_output["tasks"],
            "iterations": result.iterations_used,
            "issues_fixed": result.issues_fixed,
            "changes": result.changes_made,
            "success": result.success,
        }

    except Exception as e:
        await framework.close()
        raise e


async def _fix_with_rules(agents_list, tasks_list, golden_data, validation_report, verbose):
    """Fix using rules (Level 2)"""
    from caas_framework.fixing.auto_fixer import AutoFixer

    echo_info("Using rule-based pattern matching...")

    fixer = AutoFixer(golden_data=golden_data, llm_plugin=None)

    # Apply template fixes first
    result = await fixer._apply_template_fixes(agents_list, tasks_list, validation_report)

    # Then apply rule-based fixes
    result = await fixer._apply_rule_fixes(result["agents"], result["tasks"], validation_report)

    if verbose:
        click.echo()
        echo_info(f"Applied template and rule-based fixes")
        echo_info(f"Changes made: {len(result.get('changes', []))}")

    return {
        "agents": result["agents"],
        "tasks": result["tasks"],
        "iterations": 1,
        "issues_fixed": len(result.get("changes", [])),
        "changes": result.get("changes", []),
        "success": True,
    }


async def _fix_with_templates(agents_list, tasks_list, validation_report, verbose):
    """Fix using templates (Level 1)"""
    from caas_framework.fixing.auto_fixer import AutoFixer

    echo_info("Using template-based deterministic fixes...")

    fixer = AutoFixer(golden_data=None, llm_plugin=None)

    # Apply only template fixes
    result = await fixer._apply_template_fixes(agents_list, tasks_list, validation_report)

    if verbose:
        click.echo()
        echo_info(f"Applied template fixes")
        echo_info(f"Changes made: {len(result.get('changes', []))}")

    return {
        "agents": result["agents"],
        "tasks": result["tasks"],
        "iterations": 1,
        "issues_fixed": len(result.get("changes", [])),
        "changes": result.get("changes", []),
        "success": True,
    }
