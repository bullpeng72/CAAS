"""
Generate Phase Command

Execute specific BMAD phase (0-5)
"""

import click
from pathlib import Path
from caas_cli.utils import (
    echo_success,
    echo_error,
    echo_info,
    echo_progress,
    echo_warning,
    handle_keyboard_interrupt,
    load_json,
    save_json,
    print_phase_banner,
    initialize_framework
)


@click.command(name="generate-phase")
@click.option(
    "--phase",
    type=click.IntRange(0, 5),
    required=True,
    help="BMAD phase to execute (0-5)"
)
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    help="Input directory from previous phase"
)
@click.option(
    "--requirement",
    "-r",
    type=str,
    help="Initial requirement (Phase 0 only)"
)
@click.option(
    "--domain",
    "-d",
    type=str,
    help="Domain hint (Phase 0 only)"
)
@click.option(
    "--deployment-target",
    type=click.Choice(["docker", "kubernetes", "terraform"]),
    default="docker",
    help="Deployment target (Phase 5 only)"
)
@click.option(
    "--workflow-type",
    type=click.Choice(["sequential", "hierarchical"]),
    help="Workflow type (Phase 1-5)"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./phase_output",
    help="Output directory (default: ./phase_output)"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed phase output"
)
@handle_keyboard_interrupt
async def generate_phase(
    phase,
    input,
    requirement,
    domain,
    deployment_target,
    workflow_type,
    output,
    verbose
):
    """
    Execute specific BMAD phase (0-5)

    \b
    BMAD PHASES:
    ═══════════════════════════════════════════════════════════════════════════
    Phase 0: Concretization
      • Input: Natural language requirement
      • Output: golden_data.json (structured requirements)
      • Purpose: Convert vague requirements into structured data

    Phase 1: Discovery
      • Input: golden_data.json
      • Output: requirement_analysis.json
      • Purpose: Analyze and refine requirements

    Phase 2: Architecture
      • Input: requirement_analysis.json
      • Output: architecture.json, agents.json, tasks.json
      • Purpose: Design system architecture

    Phase 3: Design
      • Input: architecture.json, agents.json, tasks.json
      • Output: Enhanced specs with traceability
      • Purpose: Detailed agent/task design

    Phase 4: Development
      • Input: Enhanced specs
      • Output: spec.yaml, validation reports
      • Purpose: Generate execution specifications

    Phase 5: Delivery
      • Input: spec.yaml
      • Output: Production code & deployment configs
      • Purpose: Generate deployable artifacts

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Phase 0 - Create Golden Data:
       $ caas generate-phase --phase 0 \\
           --requirement "Build a task management system" \\
           --domain TASK_MANAGEMENT \\
           --output ./phase0

    \b
    2️⃣  Phase 1 - Analyze Requirements:
       $ caas generate-phase --phase 1 \\
           --input ./phase0 \\
           --output ./phase1

    \b
    3️⃣  Phase 2 - Design Architecture:
       $ caas generate-phase --phase 2 \\
           --input ./phase1 \\
           --workflow-type sequential \\
           --output ./phase2

    \b
    4️⃣  Phase 3 - Detail Design:
       $ caas generate-phase --phase 3 \\
           --input ./phase2 \\
           --output ./phase3

    \b
    5️⃣  Phase 4 - Generate Specs:
       $ caas generate-phase --phase 4 \\
           --input ./phase3 \\
           --output ./phase4

    \b
    6️⃣  Phase 5 - Generate Code:
       $ caas generate-phase --phase 5 \\
           --input ./phase4 \\
           --deployment-target kubernetes \\
           --output ./phase5

    \b
    WORKFLOW:
    ═══════════════════════════════════════════════════════════════════════════
    Each phase builds on the previous:
    requirement → [Phase 0] → golden_data.json
                → [Phase 1] → requirement_analysis.json
                → [Phase 2] → architecture.json + agents/tasks
                → [Phase 3] → enhanced specs
                → [Phase 4] → spec.yaml
                → [Phase 5] → production code

    \b
    DEBUGGING:
    ═══════════════════════════════════════════════════════════════════════════
    Use this command to:
    • Debug specific phase issues
    • Re-run failed phases
    • Test phase modifications
    • Generate intermediate artifacts
    """
    try:
        print_phase_banner(phase, _get_phase_name(phase))

        # Validate inputs
        if phase == 0 and not requirement:
            echo_error("Phase 0 requires --requirement option")
            return 1

        if phase > 0 and not input:
            echo_error(f"Phase {phase} requires --input option (previous phase output)")
            return 1

        # Initialize framework
        echo_progress("Initializing framework...")
        framework = await initialize_framework()

        # Execute phase
        result = None
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        if phase == 0:
            result = await _execute_phase_0(framework, requirement, domain, output_path, verbose)
        elif phase == 1:
            result = await _execute_phase_1(framework, input, output_path, verbose)
        elif phase == 2:
            result = await _execute_phase_2(framework, input, workflow_type, output_path, verbose)
        elif phase == 3:
            result = await _execute_phase_3(framework, input, output_path, verbose)
        elif phase == 4:
            result = await _execute_phase_4(framework, input, output_path, verbose)
        elif phase == 5:
            result = await _execute_phase_5(
                framework, input, deployment_target, output_path, verbose
            )

        await framework.close()

        # Show success
        click.echo()
        echo_success(f"Phase {phase} completed!")
        echo_info(f"Output saved to: {output}")

        # Show next phase hint
        if phase < 5:
            click.echo()
            click.echo(click.style("Next step:", bold=True))
            click.echo(f"  caas generate-phase --phase {phase + 1} --input {output} --output ./phase{phase + 1}")

        return 0

    except ImportError as e:
        echo_error(f"Failed to import framework: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Phase {phase} error: {e}")
        import traceback
        if verbose:
            echo_error(traceback.format_exc())
        return 1


def _get_phase_name(phase: int) -> str:
    """Get phase name"""
    names = {
        0: "Concretization (Golden Data)",
        1: "Discovery (Requirement Analysis)",
        2: "Architecture (System Design)",
        3: "Design (Agent/Task Design)",
        4: "Development (Spec Generation)",
        5: "Delivery (Code Generation)"
    }
    return names.get(phase, "Unknown")


async def _execute_phase_0(framework, requirement, domain, output_path, verbose):
    """Phase 0: Concretization"""
    echo_progress("Generating Golden Data from requirement...")

    from caas_framework.bmad.engine import BMADEngine

    engine = BMADEngine(
        llm_plugin=framework.llm_plugin,
        validation_orchestrator=framework.validation_orchestrator
    )

    golden_data = await engine._phase_0_concretization(requirement, domain)

    if verbose:
        click.echo()
        echo_info(f"Features extracted: {len(golden_data.features)}")
        echo_info(f"Functional requirements: {len(golden_data.functional_requirements)}")
        echo_info(f"Non-functional requirements: {len(golden_data.non_functional_requirements)}")

    # Save golden data
    save_json(output_path / "golden_data.json", golden_data)

    return golden_data


async def _execute_phase_1(framework, input_dir, output_path, verbose):
    """Phase 1: Discovery"""
    echo_progress("Analyzing requirements...")

    # Load golden data
    golden_data_dict = load_json(Path(input_dir) / "golden_data.json")

    from caas_framework.bmad.engine import BMADEngine
    from caas_framework.models.specifications import ConcretizedRequirement as GoldenData

    golden_data = GoldenData(**golden_data_dict)

    engine = BMADEngine(
        llm_plugin=framework.llm_plugin,
        validation_orchestrator=framework.validation_orchestrator
    )

    analysis = await engine._phase_1_discovery(golden_data)

    if verbose:
        click.echo()
        echo_info(f"Analysis completed")

    # Save analysis
    save_json(output_path / "requirement_analysis.json", analysis)

    return analysis


async def _execute_phase_2(framework, input_dir, workflow_type, output_path, verbose):
    """Phase 2: Architecture"""
    echo_progress("Designing system architecture...")

    # Load previous phase data
    input_path = Path(input_dir)
    golden_data_dict = load_json(input_path / "golden_data.json")
    analysis = load_json(input_path / "requirement_analysis.json")

    from caas_framework.bmad.engine import BMADEngine
    from caas_framework.models.specifications import ConcretizedRequirement as GoldenData

    golden_data = GoldenData(**golden_data_dict)

    engine = BMADEngine(
        llm_plugin=framework.llm_plugin,
        validation_orchestrator=framework.validation_orchestrator
    )

    architecture, agents, tasks = await engine._phase_2_architecture(
        golden_data,
        analysis,
        workflow_type
    )

    if verbose:
        click.echo()
        echo_info(f"Agents designed: {len(agents)}")
        echo_info(f"Tasks designed: {len(tasks)}")

    # Save outputs
    save_json(output_path / "architecture.json", architecture)
    save_json(output_path / "agents.json", agents)
    save_json(output_path / "tasks.json", tasks)

    return {"architecture": architecture, "agents": agents, "tasks": tasks}


async def _execute_phase_3(framework, input_dir, output_path, verbose):
    """Phase 3: Design"""
    echo_progress("Refining agent/task design...")

    # Load previous phase data
    input_path = Path(input_dir)
    golden_data_dict = load_json(input_path / "golden_data.json")
    agents = load_json(input_path / "agents.json")
    tasks = load_json(input_path / "tasks.json")

    from caas_framework.bmad.engine import BMADEngine
    from caas_framework.models.specifications import ConcretizedRequirement as GoldenData

    golden_data = GoldenData(**golden_data_dict)

    engine = BMADEngine(
        llm_plugin=framework.llm_plugin,
        validation_orchestrator=framework.validation_orchestrator
    )

    enhanced_agents, enhanced_tasks, traceability = await engine._phase_3_design(
        golden_data,
        agents,
        tasks
    )

    if verbose:
        click.echo()
        echo_info(f"Enhanced agents: {len(enhanced_agents)}")
        echo_info(f"Enhanced tasks: {len(enhanced_tasks)}")
        if traceability:
            echo_info("Traceability matrix generated")

    # Save outputs
    save_json(output_path / "enhanced_agents.json", enhanced_agents)
    save_json(output_path / "enhanced_tasks.json", enhanced_tasks)
    if traceability:
        save_json(output_path / "traceability_matrix.json", traceability)

    return {
        "agents": enhanced_agents,
        "tasks": enhanced_tasks,
        "traceability": traceability
    }


async def _execute_phase_4(framework, input_dir, output_path, verbose):
    """Phase 4: Development"""
    echo_progress("Generating execution specifications...")

    # Load previous phase data
    input_path = Path(input_dir)
    agents = load_json(input_path / "enhanced_agents.json")
    tasks = load_json(input_path / "enhanced_tasks.json")

    from caas_framework.bmad.engine import BMADEngine

    engine = BMADEngine(
        llm_plugin=framework.llm_plugin,
        validation_orchestrator=framework.validation_orchestrator
    )

    spec_yaml, validation_reports = await engine._phase_4_development(agents, tasks)

    if verbose:
        click.echo()
        echo_info("Spec YAML generated")
        echo_info(f"Validation reports: {len(validation_reports)}")

    # Save outputs
    with open(output_path / "spec.yaml", "w", encoding="utf-8") as f:
        f.write(spec_yaml)
    echo_success(f"Saved to: {output_path / 'spec.yaml'}")

    if validation_reports:
        save_json(output_path / "validation_reports.json", validation_reports)

    return {"spec": spec_yaml, "validation_reports": validation_reports}


async def _execute_phase_5(framework, input_dir, deployment_target, output_path, verbose):
    """Phase 5: Delivery"""
    echo_progress("Generating production code...")

    # Load previous phase data
    input_path = Path(input_dir)

    with open(input_path / "spec.yaml", "r", encoding="utf-8") as f:
        spec_yaml = f.read()

    from caas_framework.bmad.engine import BMADEngine

    engine = BMADEngine(
        llm_plugin=framework.llm_plugin,
        validation_orchestrator=framework.validation_orchestrator
    )

    generated_code = await engine._phase_5_delivery(spec_yaml, deployment_target)

    if verbose:
        click.echo()
        echo_info(f"Files generated: {len(generated_code)}")

    # Save generated files
    from caas_cli.utils import save_files
    save_files(output_path, generated_code)

    return generated_code
