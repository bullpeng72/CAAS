"""
Generate Command

Generate CrewAI agents from requirements - Uses caas_framework directly
"""

import asyncio
import time
from pathlib import Path

import click

# Load .env file for API keys
from dotenv import load_dotenv

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)

# Try to load .env from current directory or project root
env_paths = [Path.cwd() / ".env", Path(__file__).parent.parent.parent / ".env"]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break


@click.command()
@click.argument("requirement")
@click.option(
    "--domain",
    "-d",
    type=str,
    help="Domain hint for better code generation (FINANCE, HEALTHCARE, E_COMMERCE, TASK_MANAGEMENT, DATA_ANALYSIS, etc.)",
)
@click.option(
    "--deployment",
    type=click.Choice(["docker", "kubernetes", "serverless"]),
    default="docker",
    help="Deployment target - generates corresponding config files (default: docker)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./generated",
    help="Output directory for generated code (default: ./generated)",
)
@click.option(
    "--no-validation",
    is_flag=True,
    help="Disable all validation (syntax, traceability, completeness) - faster but risky",
)
@click.option(
    "--no-auto-fix", is_flag=True, help="Disable automatic error fixing - will fail fast on errors"
)
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    help="[Phase 0] Use pre-existing Golden Data JSON file (skip requirement analysis)",
)
@click.option(
    "--no-traceability",
    is_flag=True,
    help="[Phase 2] Disable traceability tracking (requirement → agent → task mapping)",
)
@click.option(
    "--no-completeness",
    is_flag=True,
    help="[Phase 3] Disable completeness validation (ensures all requirements are implemented)",
)
@click.option(
    "--gap-filling",
    is_flag=True,
    help="[Phase 0] Enable automatic gap filling for missing features",
)
@click.option(
    "--workflow-type",
    "-w",
    type=click.Choice(["sequential", "hierarchical", "auto"]),
    default="auto",
    help="""Workflow process type:
    \b
    • sequential: Linear execution (simple workflows, 2-3 agents)
    • hierarchical: Manager-based delegation (complex workflows, 5+ agents, FINANCE/HEALTHCARE domains)
    • auto: Automatic selection based on complexity (recommended)""",
)
@click.option(
    "--plan-mode",
    is_flag=True,
    help="[Phase 3] Enable Plan Mode - interactive approval gates for each phase (Discovery, Design, Code)",
)
@click.option(
    "--verbosity",
    "-v",
    type=click.Choice(["quiet", "minimal", "normal", "verbose", "debug"]),
    default="normal",
    help="""Progress reporting verbosity level:
    \b
    • quiet: No progress output (errors only)
    • minimal: Phase start/complete only
    • normal: Standard progress updates (default)
    • verbose: Detailed progress with validation results
    • debug: Full diagnostic output with internal events""",
)
@click.option(
    "--distributed",
    is_flag=True,
    help="Enable distributed parallel execution for large projects (30-50%% speedup)",
)
@click.option(
    "--workers", type=int, help="Number of workers for distributed execution (default: CPU count)"
)
@handle_keyboard_interrupt
def generate(
    requirement,
    domain,
    deployment,
    output,
    no_validation,
    no_auto_fix,
    golden_data,
    no_traceability,
    no_completeness,
    gap_filling,
    workflow_type,
    plan_mode,
    verbosity,
    distributed,
    workers,
):
    """
    \b
    Generate complete CrewAI multi-agent system from natural language requirements

    \b
    🔄 BMAD PHASES EXECUTED:
    ═══════════════════════════════════════════════════════════════════════════
    Phase 0: Requirements Analysis  → Golden Data (구조화된 요구사항)
    Phase 1: Modeling               → Agents & Tasks 설계
    Phase 2: Architecture           → 시스템 아키텍처 + Traceability 검증
    Phase 3: Development            → 프로덕션 코드 생성 + Completeness 검증
    Phase 4: Deployment             → Docker/Kubernetes 설정 생성

    \b
    📦 GENERATED ARTIFACTS:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    Production Code:
    • src/agents.py          - CrewAI agent definitions
    • src/tasks.py           - CrewAI task definitions
    • src/crew.py            - Crew configuration (sequential/hierarchical)
    • src/tools.py           - Custom tool implementations
    • main.py                - Entry point
    • requirements.txt       - Dependencies
    • README.md              - Project documentation
    • tests/                 - Unit & integration tests

    \b
    Deployment:
    • Dockerfile             - Container definition
    • docker-compose.yml     - Multi-service orchestration
    • kubernetes/            - K8s manifests (if deployment=kubernetes)

    \b
    BMAD Phase Artifacts:
    • golden_data.json              - Structured requirements (Phase 0)
    • requirement_analysis.json     - Requirement analysis report (Phase 0)
    • agents.json                   - Agent specifications (Phase 1)
    • tasks.json                    - Task specifications (Phase 1)
    • architecture.json             - Architecture design (Phase 2)
    • traceability_report.md        - Traceability analysis (Phase 2)
    • traceability_matrix.json      - Full traceability matrix (Phase 2)
    • completeness_report.json      - Completeness analysis (Phase 3)
    • completeness_report.md        - Completeness text report (Phase 3)

    \b
    Documentation Artifacts (if ARTIFACT_GENERATION_ENABLED=true in .env):
    • ./artifacts/[ProjectName]/project_proposal_*.md       - Project proposal
    • ./artifacts/[ProjectName]/requirements_spec_*.md      - Requirements specification
    • ./artifacts/[ProjectName]/architecture_design_*.md    - Architecture design doc
    • ./artifacts/[ProjectName]/agent_design_*.md           - Agent design doc
    • ./artifacts/[ProjectName]/api_design_*.md             - API design doc

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Simple generation (auto workflow selection):
       $ caas generate "Build a task management system"

    \b
    2️⃣  With domain hint for better code generation:
       $ caas generate "Build a trading platform" --domain FINANCE

    \b
    3️⃣  Force hierarchical workflow (manager-based):
       $ caas generate "Build a healthcare system" \\
           --domain HEALTHCARE \\
           --workflow-type hierarchical

    \b
    4️⃣  Custom output directory & Kubernetes deployment:
       $ caas generate "Build an e-commerce store" \\
           --output ./my-store \\
           --deployment kubernetes

    \b
    5️⃣  Use pre-existing Golden Data (skip Phase 0):
       $ caas generate "Build a system" \\
           --golden-data ./existing_golden.json

    \b
    6️⃣  Fast mode (skip validation - use with caution):
       $ caas generate "Build a chatbot" \\
           --no-validation \\
           --no-traceability \\
           --no-completeness

    \b
    7️⃣  Plan Mode (interactive approval gates at each phase):
       $ caas generate "Build a blog system" \\
           --plan-mode \\
           --verbosity verbose

    \b
    8️⃣  Quiet mode (minimal output, errors only):
       $ caas generate "Build an API" \\
           --verbosity quiet \\
           --output ./output

    \b
    9️⃣  Debug mode (full diagnostic output):
       $ caas generate "Build a trading bot" \\
           --domain FINANCE \\
           --verbosity debug

    \b
    🎯 WORKFLOW SELECTION:
    ═══════════════════════════════════════════════════════════════════════════
    • Auto-selects HIERARCHICAL when:
      - 5+ agents needed
      - Complex domain (FINANCE, HEALTHCARE, WORKFLOW)
      - Complex coordination required
      - Complexity score ≥ 60

    • Auto-selects SEQUENTIAL when:
      - 2-3 agents
      - Simple domain (TASK_MANAGEMENT, CHATBOT)
      - Linear workflow

    \b
    ⚠️  REQUIREMENTS:
    ═══════════════════════════════════════════════════════════════════════════
    • OPENAI_API_KEY environment variable must be set
    • Python 3.11+ required
    • No API server needed - uses caas_framework directly

    \b
    📚 See also:
       caas analyze-gaps --help    (Requirement refinement)
       caas traceability --help    (Phase 2 verification)
    """
    import json

    def serialize_completeness_report(report):
        """
        Serialize CompletenessReport to JSON-compatible dict.
        Handles nested Pydantic models and dataclasses.
        """
        from dataclasses import fields, is_dataclass

        result = {}
        for field in fields(report):
            value = getattr(report, field.name)

            if isinstance(value, list):
                # Handle list of objects
                serialized_list = []
                for item in value:
                    if hasattr(item, "model_dump"):
                        # Pydantic BaseModel (e.g., FeatureSpec, FeatureImplementation)
                        serialized_list.append(item.model_dump())
                    elif is_dataclass(item) and not isinstance(item, type):
                        # Nested dataclass
                        serialized_list.append(serialize_completeness_report(item))
                    else:
                        # Primitive type
                        serialized_list.append(item)
                result[field.name] = serialized_list
            elif hasattr(value, "model_dump"):
                # Single Pydantic object
                result[field.name] = value.model_dump()
            elif is_dataclass(value) and not isinstance(value, type):
                # Nested dataclass
                result[field.name] = serialize_completeness_report(value)
            else:
                # Primitive type
                result[field.name] = value

        return result

    # Load golden data if provided
    golden_data_dict = None
    if golden_data:
        try:
            with open(golden_data, "r", encoding="utf-8") as f:
                golden_data_dict = json.load(f)
            echo_info(f"Loaded Golden Data from: {golden_data}")
        except Exception as e:
            echo_error(f"Failed to load golden data: {e}")
            return

    # Show configuration
    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║                  CAAS Code Generation                        ║
║            (Using caas_framework directly)                   ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    echo_info(f"Requirement: {requirement}")
    if domain:
        echo_info(f"Domain: {domain}")
    echo_info(f"Deployment: {deployment}")
    echo_info(f"Output: {output}")
    echo_info(f"Workflow Type: {workflow_type}")
    echo_info(f"Plan Mode: {'Enabled' if plan_mode else 'Disabled'}")
    echo_info(f"Verbosity: {verbosity}")
    echo_info(f"Validation: {'Enabled' if not no_validation else 'Disabled'}")
    echo_info(f"Auto-fix: {'Enabled' if not no_auto_fix else 'Disabled'}")
    echo_info(f"Phase 2 Traceability: {'Enabled' if not no_traceability else 'Disabled'}")
    echo_info(f"Phase 3 Completeness: {'Enabled' if not no_completeness else 'Disabled'}")
    echo_info(f"Gap Filling: {'Enabled' if gap_filling else 'Disabled'}")
    if distributed:
        workers_str = f"{workers} workers" if workers else "auto workers"
        echo_info(f"Distributed Execution: Enabled ({workers_str}) - 30-50% speedup")
    click.echo()

    try:
        from caas_framework import CrewAIFramework
        from caas_framework.config.loader import load_config
        from caas_framework.config.settings import ValidationConfig
        from caas_framework.reporting import VerbosityLevel

        # Load framework configuration from .env (includes artifact settings)
        config = load_config()

        # Override validation settings from CLI flags
        config.validation = ValidationConfig(enabled=not no_validation, auto_fix=not no_auto_fix)

        # Run generation
        async def run_generation():
            echo_progress("Initializing framework...")

            framework = CrewAIFramework(llm_provider="openai", config=config)

            await framework.initialize()
            echo_success("Framework initialized")

            click.echo()

            # Create progress tracker for Rich UI
            from caas_cli.progress_tracker import SimpleProgressReporter

            progress_tracker = SimpleProgressReporter()

            echo_progress("Generating code...")
            click.echo()

            start_time = time.time()

            # Generate from requirement with Phase 1-3 parameters
            # Prepare workflow_type (None for auto-selection)
            selected_workflow_type = None if workflow_type == "auto" else workflow_type

            with progress_tracker:
                result = await framework.generate_from_requirement(
                    requirement=requirement,
                    domain=domain,
                    golden_data=golden_data_dict,
                    deployment_target=deployment,
                    workflow_type=selected_workflow_type,
                    enable_traceability=not no_traceability,
                    enable_completeness_validation=not no_completeness,
                    enable_gap_filling=gap_filling,
                    plan_mode=plan_mode,
                    verbosity=verbosity,
                    distributed=distributed,
                    max_workers=workers,
                    progress_reporter=progress_tracker,
                )

            generation_time = time.time() - start_time

            await framework.close()

            return result, generation_time

        # Run async generation
        result, generation_time = asyncio.run(run_generation())

        # Check result
        if result.success:
            click.echo()
            echo_success("Generation completed!")

            # Show summary
            click.echo()
            click.echo(click.style("Summary:", bold=True))
            click.echo(
                f"  Phases completed:  {', '.join([p.value for p in result.phases_completed])}"
            )

            # Phase 1: Features
            if result.golden_data and result.golden_data.features:
                click.echo(f"  Features extracted: {len(result.golden_data.features)}")

            click.echo(f"  Agents generated:  {len(result.agent_specs)}")
            click.echo(f"  Tasks generated:   {len(result.task_specs)}")
            if result.generated_code:
                click.echo(f"  Files generated:   {len(result.generated_code)}")
            click.echo(f"  Generation time:   {generation_time:.2f}s")

            # Phase 2: Traceability
            if result.traceability_matrix:
                click.echo()
                click.echo(click.style("Phase 2 - Traceability:", bold=True))
                click.echo(f"  Features tracked:  {len(result.traceability_matrix.features)}")
                click.echo(f"  Tasks tracked:     {len(result.traceability_matrix.tasks)}")
                click.echo(f"  Code files tracked: {len(result.traceability_matrix.code_files)}")

            # Phase 3: Completeness
            if result.completeness_report:
                click.echo()
                click.echo(click.style("Phase 3 - Completeness:", bold=True))
                report = result.completeness_report
                click.echo(f"  Total features:     {report.total_features}")
                click.echo(f"  Fully implemented:  {report.fully_implemented}")
                click.echo(f"  Partial:            {report.partially_implemented}")
                click.echo(f"  Not implemented:    {report.not_implemented}")
                click.echo(f"  Implementation rate: {report.implementation_rate:.1f}%")
                click.echo(f"  Completeness score:  {report.completeness_score:.1f}/100")
                if report.is_complete:
                    echo_success("  Status: ✅ COMPLETE")
                else:
                    echo_warning("  Status: ⚠️  INCOMPLETE")

            # Gap Filling
            if result.gap_filling_result:
                click.echo()
                click.echo(click.style("Gap Filling:", bold=True))
                gap_result = result.gap_filling_result
                click.echo(f"  Features filled:   {len(gap_result.features_filled)}")
                click.echo(f"  Files updated:     {len(gap_result.updated_files)}")
                if gap_result.success:
                    echo_success("  Status: ✅ SUCCESS")
                else:
                    echo_warning(f"  Status: ⚠️  PARTIAL ({len(gap_result.errors)} errors)")

            # Validation summary
            if result.validation_reports:
                click.echo()
                click.echo(f"  Validation runs:   {len(result.validation_reports)}")

            # Create output directory
            click.echo()
            output_path = Path(output)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save generated code (if available)
            if result.generated_code:
                echo_progress(f"Saving code to {output}...")

                for file_path, content in result.generated_code.items():
                    file_full_path = output_path / file_path
                    file_full_path.parent.mkdir(parents=True, exist_ok=True)

                    # Convert content to string if it's a dict
                    if isinstance(content, dict):
                        import json

                        content = json.dumps(content, indent=2, ensure_ascii=False)
                    elif not isinstance(content, str):
                        content = str(content)

                    with open(file_full_path, "w", encoding="utf-8") as f:
                        f.write(content)

                echo_success(f"Code saved to: {output}")
                click.echo()

                # Display boundaries violations
                if result.boundaries_violations:
                    click.echo()
                    echo_warning(
                        f"⚠️  Security Boundary Violations Detected: {len(result.boundaries_violations)}"
                    )
                    for violation in result.boundaries_violations:
                        click.echo(f"  ❌ {violation}")
                    click.echo()
                    echo_info(
                        "💡 Review the generated code and ensure these violations are acceptable."
                    )
                    click.echo()

                # Display quality evaluation
                if result.quality_evaluation:
                    quality = result.quality_evaluation
                    score = quality.get("overall_score", 0)
                    if quality.get("passed", False):
                        echo_success(f"✅ Quality Score: {score:.1f}/10")
                    else:
                        echo_warning(f"⚠️  Quality Score: {score:.1f}/10 (Below threshold)")
                    click.echo()

                # Display security scan results
                if result.security_report:
                    security = result.security_report
                    total_issues = security.get("total_issues", 0)
                    critical = security.get("critical_count", 0)
                    high = security.get("high_count", 0)
                    medium = security.get("medium_count", 0)
                    low = security.get("low_count", 0)

                    if security.get("is_safe"):
                        if total_issues == 0:
                            echo_success("🔒 Security scan: No issues found")
                        else:
                            echo_success(
                                f"🔒 Security scan: {total_issues} low-priority issues ({low}L, {medium}M)"
                            )
                    else:
                        echo_warning(f"⚠️  Security scan: {total_issues} issues found")
                        if critical > 0:
                            click.echo(f"     🔴 Critical: {critical}")
                        if high > 0:
                            click.echo(f"     🟠 High: {high}")
                        if medium > 0:
                            click.echo(f"     🟡 Medium: {medium}")
                        if low > 0:
                            click.echo(f"     🟢 Low: {low}")

                        # Show first 3 critical/high issues
                        issues = security.get("issues", [])
                        critical_high = [
                            i for i in issues if i.get("severity") in ("critical", "high")
                        ]
                        if critical_high:
                            click.echo()
                            echo_warning("  Top security issues:")
                            for issue in critical_high[:3]:
                                severity_emoji = (
                                    "🔴" if issue.get("severity") == "critical" else "🟠"
                                )
                                file_path = issue.get("file_path", "unknown")
                                line = issue.get("line_number", "?")
                                location = f"{file_path}:{line}"
                                text = issue.get("issue_text", "Unknown issue")
                                click.echo(f"    {severity_emoji} [{location}] {text}")

                            if len(critical_high) > 3:
                                click.echo(
                                    f"    ... and {len(critical_high) - 3} more critical/high issues"
                                )

                    click.echo()

                # Display validation results (syntax, imports, compatibility)
                if result.validation_reports:
                    for validation in result.validation_reports:
                        if validation.get("type") == "python311_compatibility":
                            error_count = validation.get("error_count", 0)
                            warning_count = validation.get("warning_count", 0)
                            info_count = validation.get("info_count", 0)

                            if validation.get("is_valid"):
                                if warning_count > 0 or info_count > 0:
                                    echo_success(
                                        f"✅ Code quality checks passed ({warning_count} warnings, {info_count} info)"
                                    )
                                else:
                                    echo_success("✅ Code quality checks passed")
                            else:
                                echo_warning(
                                    f"⚠️  Code quality issues: {error_count} errors, {warning_count} warnings"
                                )

                                # Display first 5 errors/warnings
                                issues = validation.get("issues", [])
                                errors = [i for i in issues if i.get("severity") == "error"]
                                warnings = [i for i in issues if i.get("severity") == "warning"]

                                for error in errors[:3]:
                                    file_loc = (
                                        f"{error.get('file', 'unknown')}:{error.get('line', '?')}"
                                    )
                                    click.echo(f"  ❌ [{file_loc}] {error.get('message', '')}")

                                if len(errors) > 3:
                                    click.echo(f"  ... and {len(errors) - 3} more errors")

                                for warning in warnings[:2]:
                                    file_loc = f"{warning.get('file', 'unknown')}:{warning.get('line', '?')}"
                                    click.echo(f"  ⚠️  [{file_loc}] {warning.get('message', '')}")

                                if len(warnings) > 2:
                                    click.echo(f"  ... and {len(warnings) - 2} more warnings")

                            click.echo()
            else:
                echo_warning("No generated code files (Phase 5 may not have completed)")
                click.echo()

            # Save BMAD artifacts (always save, regardless of generated_code)
            echo_progress("Saving BMAD artifacts...")
            artifacts_saved = []

            # Phase 0: Golden Data
            if result.golden_data:
                golden_file = output_path / "golden_data.json"
                try:
                    with open(golden_file, "w", encoding="utf-8") as f:
                        json.dump(result.golden_data.model_dump(), f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("golden_data.json (Phase 0)")
                except Exception as e:
                    echo_warning(f"Failed to save golden_data.json: {e}")

            # Phase 0: Requirement Analysis
            if result.requirement_analysis:
                req_file = output_path / "requirement_analysis.json"
                try:
                    with open(req_file, "w", encoding="utf-8") as f:
                        json.dump(result.requirement_analysis, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("requirement_analysis.json (Phase 0)")
                except Exception as e:
                    echo_warning(f"Failed to save requirement_analysis.json: {e}")

            # Phase 1: Agent Specs
            if result.agent_specs:
                agents_file = output_path / "agents.json"
                try:
                    agents_data = [agent.model_dump() for agent in result.agent_specs]
                    with open(agents_file, "w", encoding="utf-8") as f:
                        json.dump(agents_data, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("agents.json (Phase 1)")
                except Exception as e:
                    echo_warning(f"Failed to save agents.json: {e}")

            # Phase 1: Task Specs
            if result.task_specs:
                tasks_file = output_path / "tasks.json"
                try:
                    tasks_data = [task.model_dump() for task in result.task_specs]
                    with open(tasks_file, "w", encoding="utf-8") as f:
                        json.dump(tasks_data, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("tasks.json (Phase 1)")
                except Exception as e:
                    echo_warning(f"Failed to save tasks.json: {e}")

            # Phase 2: Architecture Design
            if result.architecture_design:
                arch_file = output_path / "architecture.json"
                try:
                    with open(arch_file, "w", encoding="utf-8") as f:
                        json.dump(result.architecture_design, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("architecture.json (Phase 2)")
                except Exception as e:
                    echo_warning(f"Failed to save architecture.json: {e}")

            # Phase 2: Traceability Report
            if result.traceability_report:
                trace_file = output_path / "traceability_report.md"
                try:
                    with open(trace_file, "w", encoding="utf-8") as f:
                        f.write(result.traceability_report)
                    artifacts_saved.append("traceability_report.md (Phase 2)")
                except Exception as e:
                    echo_warning(f"Failed to save traceability_report.md: {e}")

            # Phase 2: Traceability Matrix
            if result.traceability_matrix:
                matrix_file = output_path / "traceability_matrix.json"
                try:
                    with open(matrix_file, "w", encoding="utf-8") as f:
                        # TraceabilityMatrix uses export_to_dict() method
                        json.dump(
                            result.traceability_matrix.export_to_dict(),
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )
                    artifacts_saved.append("traceability_matrix.json (Phase 2)")
                except Exception as e:
                    echo_warning(f"Failed to save traceability_matrix.json: {e}")

            # Phase 3: Completeness Report
            if result.completeness_report:
                comp_file = output_path / "completeness_report.json"
                try:
                    with open(comp_file, "w", encoding="utf-8") as f:
                        # CompletenessReport contains nested Pydantic models
                        serialized_report = serialize_completeness_report(
                            result.completeness_report
                        )
                        json.dump(serialized_report, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("completeness_report.json (Phase 3)")
                except Exception as e:
                    echo_warning(f"Failed to save completeness_report.json: {e}")

            # Phase 3: Completeness Text Report
            if result.completeness_text_report:
                comp_text_file = output_path / "completeness_report.md"
                try:
                    with open(comp_text_file, "w", encoding="utf-8") as f:
                        f.write(result.completeness_text_report)
                    artifacts_saved.append("completeness_report.md (Phase 3)")
                except Exception as e:
                    echo_warning(f"Failed to save completeness_report.md: {e}")

            # Quality Validation Reports
            if result.validation_reports:
                validation_file = output_path / "validation_reports.json"
                try:
                    with open(validation_file, "w", encoding="utf-8") as f:
                        json.dump(result.validation_reports, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("validation_reports.json (Quality)")
                except Exception as e:
                    echo_warning(f"Failed to save validation_reports.json: {e}")

            # Security Scan Report
            if result.security_report:
                security_file = output_path / "security_report.json"
                try:
                    with open(security_file, "w", encoding="utf-8") as f:
                        json.dump(result.security_report, f, indent=2, ensure_ascii=False)
                    artifacts_saved.append("security_report.json (Security)")
                except Exception as e:
                    echo_warning(f"Failed to save security_report.json: {e}")

            # Show artifacts saved
            if artifacts_saved:
                echo_success(f"Saved {len(artifacts_saved)} BMAD artifacts:")
                for artifact in artifacts_saved:
                    click.echo(f"  ✓ {artifact}")
            else:
                echo_warning("No BMAD artifacts were generated")

            # Save spec YAML if available
            if result.spec_yaml and not result.generated_code:
                spec_file = output_path / "crew_spec.yaml"
                try:
                    with open(spec_file, "w", encoding="utf-8") as f:
                        f.write(result.spec_yaml)
                    echo_success(f"Spec YAML saved to: {spec_file}")
                except Exception as e:
                    echo_warning(f"Failed to save spec.yaml: {e}")

            # Show next steps
            click.echo()
            click.echo(click.style("Next steps:", bold=True))
            click.echo(f"  1. cd {output}")
            if result.generated_code:
                click.echo("  2. Review generated code")
                click.echo("  3. Review BMAD artifacts (*.json, *.md)")
                click.echo("  4. Install dependencies: pip install -r requirements.txt")
                click.echo(f"  5. Run with {deployment}")
            else:
                click.echo("  2. Review BMAD artifacts (*.json, *.md)")
                click.echo("  3. Use artifacts for code generation:")
                click.echo(
                    f"     caas codegen --component all --agents {output}/agents.json --tasks {output}/tasks.json"
                )

        else:
            echo_error("Generation failed!")
            if result.errors:
                click.echo()
                click.echo(click.style("Errors:", bold=True))
                for error in result.errors:
                    click.echo(f"  - {error}")

    except ImportError as e:
        echo_error(f"Failed to import caas_framework: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
    except Exception as e:
        echo_error(f"Error: {e}")
        import traceback

        echo_error(traceback.format_exc())
