"""
CAAS CLI Main Entry Point

Command-line interface for generating CrewAI agents.
"""

import click

from caas_cli.commands import (  # Phase 1: Core Features; Phase 2: Advanced Features; Phase 3: Management Features
    analyze_gaps,
    codegen_cmd,
    config,
    download,
    env,
    expand_requirement,
    fix_cmd,
    generate,
    generate_code_cmd,
    generate_phase,
    init,
    interactive_questions,
    list_projects,
    plugins_cmd,
    session_cmd,
    status,
    test_cmd,
    traceability,
    validate_cmd,
    workflow_cmd,
)


@click.group()
@click.version_option(version="0.2.0")
@click.pass_context
def cli(ctx):
    """
    \b
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║  CAAS - CrewAI Agent Auto-generation System                               ║
    ║                                                                           ║
    ║  Generate production-ready CrewAI multi-agent systems from natural        ║
    ║  language requirements using BMAD (Business-Modeling-Architecture-        ║
    ║  Development) methodology.                                                ║
    ╚═══════════════════════════════════════════════════════════════════════════╝

    \b
    🔄 BMAD WORKFLOW PHASES
    ═══════════════════════════════════════════════════════════════════════════
    Phase 0: Requirements Analysis  → Golden Data (구조화된 요구사항 정의)
    Phase 1: Modeling               → Agents & Tasks 설계
    Phase 2: Architecture           → 시스템 아키텍처 설계 (Traceability 검증)
    Phase 3: Development            → 프로덕션 코드 생성 (Completeness 검증)
    Phase 4: Deployment             → 배포 설정 생성 (Docker/K8s)

    \b
    📋 COMMAND CATEGORIES
    ═══════════════════════════════════════════════════════════════════════════

    \b
    🔧 SETUP & CONFIGURATION
       init                   Initialize CAAS configuration (interactive wizard)
       config                 Manage configuration settings (get/set/list/reset)
       env                    Manage .env file (create/validate/show help)

    \b
    📝 REQUIREMENT REFINEMENT (Phase 0)
       analyze-gaps          Analyze requirement gaps against Golden Data
       expand                Auto-expand requirements to fill gaps
       questions             Interactive question-driven requirement clarification

    \b
    🚀 CODE GENERATION
    \b
       generate              Full workflow: Requirement text → Complete system
                             ├─ All BMAD phases (0-5)
                             ├─ Auto workflow selection
                             ├─ Built-in validation
                             └─ Time: 5-10 min
    \b
       generate-code         Fast: agents.json + tasks.json → Production code
                             ├─ Production code only (agents.py, crew.py, main.py)
                             ├─ Use after design validation
                             ├─ Skip Phase 0-4
                             └─ Time: 1-2 min ⚡
    \b
       codegen               Selective: Generate specific components
                             ├─ tests, deployment, frontend, docs, cicd
                             ├─ Regenerate parts without full rebuild
                             └─ Time: 30 sec - 1 min ⚡⚡
    \b
       generate-phase        Debug: Execute specific BMAD phase (0-5)
                             ├─ Phase-by-phase execution
                             ├─ For troubleshooting
                             └─ Advanced users only

    \b
    ✅ VALIDATION & FIXING
    \b
       validate              Check design quality (6 validators available)
                             ├─ ontology, golden, dependency, python311, crewai, all
                             ├─ Individual or combined
                             └─ Outputs: Validation reports (JSON/text)
    \b
       fix                   Auto-fix design issues (3-level strategy)
                             ├─ Level 1: Template-based (fast, deterministic)
                             ├─ Level 2: Rule-based (medium, pattern-matching)
                             ├─ Level 3: LLM-based (smart, recommended) ⭐
                             └─ Max iterations: configurable
    \b
       traceability          Track requirement → agent → task → code
                             ├─ Ensure complete implementation
                             ├─ Coverage analysis
                             └─ Outputs: Traceability matrix + report

    \b
    🧪 TESTING
    \b
       test                  Execute tests on generated code
                             ├─ run: Execute pytest with coverage report
                             ├─ coverage: Check coverage threshold (default: 80%)
                             ├─ validate: Validate test syntax & imports
                             └─ Supports: unit tests, integration tests, e2e tests

    \b
    🔌 PLUGIN MANAGEMENT
    \b
       plugins               Manage plugins (6 subcommands)
                             ├─ list: Show all available plugins
                             ├─ status: Check plugin health & connectivity
                             ├─ info: Display plugin details & capabilities
                             ├─ enable: Activate a plugin
                             ├─ disable: Deactivate a plugin
                             └─ configure: Update plugin settings
    \b
                             Supported plugins: LLM, tools, storage, monitoring

    \b
    📊 SESSION & WORKFLOW
    \b
       session               Manage workflow sessions (7 subcommands)
                             ├─ create: Start new session
                             ├─ list: Show all sessions
                             ├─ switch: Change active session
                             ├─ show: Display session details
                             ├─ delete: Remove session
                             ├─ pause: Suspend session
                             └─ resume: Restart paused session
    \b
       workflow              Control workflow execution (6 subcommands)
                             ├─ pause: Pause running workflow
                             ├─ resume: Continue paused workflow
                             ├─ progress: Show current progress (BMAD phases)
                             ├─ cancel: Abort workflow gracefully
                             ├─ list: Show all active workflows
                             └─ retry: Retry failed phase

    \b
    📦 RESULTS MANAGEMENT
    \b
       status                Check project generation status
                             └─ Real-time progress tracking with phase indicators
    \b
       download              Download generated code & artifacts
                             └─ ZIP archive with all outputs (code, tests, docs, deployment)
    \b
       list                  List all projects
                             └─ Table view with status, date, domain

    \b
    🔀 WORKFLOW PATTERNS
    ═══════════════════════════════════════════════════════════════════════════

    \b
    ⚡ SIMPLE (빠른 생성):  init → generate
       $ caas init                                    # Setup configuration
       $ caas env --create                            # Create .env file
       $ caas generate "Build a task management system" -o ./output

    \b
    🎯 COMPLETE (요구사항 정제):  generate → analyze → expand → regenerate
       $ caas generate "e-commerce platform" -o ./design
       $ caas analyze-gaps "e-commerce platform" -g ./design/golden_data.json
       $ caas questions -g gaps.json -d E_COMMERCE
       $ caas expand "e-commerce platform" -g ./design/golden_data.json --gaps gaps.json
       $ caas generate "e-commerce platform" --golden-data expanded_golden.json

    \b
    🔧 VALIDATE & FIX (설계 검증):  generate → validate → fix → generate-code
       $ caas generate "Build chatbot" -o ./design
       $ caas validate --agents ./design/agents.json --tasks ./design/tasks.json \\
           --golden-data ./design/golden_data.json
       $ caas fix --agents ./design/agents.json --tasks ./design/tasks.json \\
           --golden-data ./design/golden_data.json --level 3
       $ caas generate-code --agents ./design/fixed_agents.json \\
           --tasks ./design/fixed_tasks.json -o ./production

    \b
    🚀 FAST ITERATION (빠른 반복):  design → validate → generate-code
       $ caas generate "API server" -o ./design
       $ caas validate --agents ./design/agents.json --tasks ./design/tasks.json
       $ caas generate-code --agents ./design/agents.json \\
           --tasks ./design/tasks.json \\
           --golden-data ./design/golden_data.json -o ./code

    \b
    💡 QUICK START EXAMPLES
    ═══════════════════════════════════════════════════════════════════════════

    \b
    # Full workflow: Requirement → Code
    $ caas generate "Build a financial trading system" --domain FINANCE -o ./output

    \b
    # Fast code generation from existing specs
    $ caas generate-code --agents agents.json --tasks tasks.json \\
        --golden-data golden_data.json -o ./code

    \b
    # Component-only generation
    $ caas codegen --component tests --agents agents.json --tasks tasks.json

    \b
    # Validation & auto-fix
    $ caas validate --validator all --agents agents.json --tasks tasks.json
    $ caas fix --agents agents.json --tasks tasks.json --golden-data golden.json

    \b
    # Phase-by-phase debugging
    $ caas generate-phase --phase 0 --requirement "Build API" -o phase0
    $ caas generate-phase --phase 1 --input phase0 -o phase1

    \b
    🔍 KEY FEATURES (v0.2.0)
    ═══════════════════════════════════════════════════════════════════════════
    \b
    ✨ Code Generation (4 methods):
       ├─ Full workflow: requirement → complete system (5-10 min)
       ├─ Spec-based: agents.json → production code (1-2 min) ⚡
       ├─ Component-only: tests/deployment/frontend/docs/cicd (30 sec)
       └─ Phase-by-phase: execute specific BMAD phase (debugging)
    \b
    ✅ Validation & Fixing:
       ├─ 6 validators: ontology, golden, dependency, python311, crewai, all
       ├─ 3-level auto-fix: template (fast), rule (medium), LLM (smart)
       ├─ Traceability matrix: requirement → agent → task → code mapping
       └─ Iterative fixing: max iterations configurable
    \b
    🧪 Testing & Quality:
       ├─ Automated test generation: unit, integration, e2e tests
       ├─ Coverage checking: configurable threshold (default 80%)
       ├─ Test execution: pytest with detailed reports
       └─ Syntax validation: import checks, type hints validation
    \b
    📦 Management:
       ├─ Session management: create, switch, pause, resume sessions
       ├─ Workflow control: pause, resume, progress tracking, retry
       ├─ Plugin system: LLM (OpenAI/Anthropic), tools, storage
       └─ Real-time monitoring: progress indicators, phase tracking
    \b
    🚀 Production-Ready:
       ├─ Deployment: Docker, Kubernetes, Terraform configs
       ├─ CI/CD pipelines: GitHub Actions, GitLab CI, Jenkins
       ├─ Workflow selection: sequential/hierarchical (auto-detect)
       ├─ Domain awareness: 10+ domains (FINANCE, E_COMMERCE, etc.)
       └─ Gap filling: analyze → expand → interactive questions

    \b
    📚 For detailed command help:
       $ caas <command> --help

    \b
    🌐 Documentation: https://github.com/your-org/caas
    """
    ctx.ensure_object(dict)


# Register commands
cli.add_command(generate.generate)
cli.add_command(init.init)
cli.add_command(config.config)
cli.add_command(env.env)
cli.add_command(status.status)
cli.add_command(list_projects.list_cmd)
cli.add_command(download.download)
cli.add_command(analyze_gaps.analyze_gaps, name="analyze-gaps")
cli.add_command(expand_requirement.expand)
cli.add_command(interactive_questions.questions)
cli.add_command(traceability.traceability)

# Phase 1: Core Features
cli.add_command(validate_cmd.validate)
cli.add_command(codegen_cmd.codegen)
cli.add_command(generate_code_cmd.generate_code)
cli.add_command(fix_cmd.fix)

# Phase 2: Advanced Features
cli.add_command(generate_phase.generate_phase)
cli.add_command(test_cmd.test)

# Phase 3: Management Features
cli.add_command(session_cmd.session)
cli.add_command(workflow_cmd.workflow)
cli.add_command(plugins_cmd.plugins)


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
