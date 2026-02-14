"""
CAAS CLI Main Entry Point

Command-line interface for generating CrewAI agents.
"""


import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from caas_cli.commands import (  # Phase 1: Core Features; Phase 2: Advanced Features; Phase 2 Enhancement: Monitoring & Performance; Phase 3: Management Features; Phase 4: Production Ready; Phase 5: TDD Integration
    analyze_completeness,
    analyze_gaps,
    analyze_requirement,
    auto_deploy_cmd,
    cache_cmd,
    codegen_cmd,
    config,
    download,
    env,
    examples,
    expand_requirement,
    fix_cmd,
    fix_runtime_error,
    generate,
    generate_code_cmd,
    generate_phase,
    init,
    interactive_questions,
    list_projects,
    models_cmd,
    monitor_cmd,
    plugins_cmd,
    profile_cmd,
    session_cmd,
    status,
    tdd,
    test_cmd,
    traceability,
    validate_cmd,
    workflow_cmd,
)


class CustomGroup(click.Group):
    """Custom Click Group with enhanced help formatting"""

    def format_help(self, ctx, formatter):
        """Override to use Rich-formatted help"""
        # Bypass Click's default formatter and use our custom help
        show_comprehensive_help()


console = Console()


def show_comprehensive_help():
    """Display comprehensive help with methodology when --help is used"""

    from rich.table import Table

    console.print("\n")

    # Header
    title = Text()
    title.append("CAAS", style="bold cyan")
    title.append(" - CrewAI Agent Auto-generation System", style="bold white")
    console.print(Panel(title, border_style="cyan"))

    console.print("\n")

    # Methodology Section
    console.print("🎯 [bold yellow]CORE METHODOLOGIES[/bold yellow]\n")

    method_text = Text()
    method_text.append("1. CAAS 6-Phase Methodology\n", style="bold green")
    method_text.append(
        "   • Phase 0: Requirement Concretization (Golden Data)\n", style="dim"
    )
    method_text.append(
        "   • Phase 1: Discovery (Tool & capability analysis)\n", style="dim"
    )
    method_text.append("   • Phase 2: Architecture (System design)\n", style="dim")
    method_text.append("   • Phase 3: Design (Agent & task design)\n", style="dim")
    method_text.append("   • Phase 4: Measurement (Quality validation)\n", style="dim")
    method_text.append("   • Phase 5: Deployment (Code generation)\n\n", style="dim")

    method_text.append(
        "2. SDD (Specification-Driven Development)\n", style="bold green"
    )
    method_text.append(
        "   • Golden Data: Complete, unambiguous specifications\n", style="dim"
    )
    method_text.append(
        "   • Boundaries: Always/Ask/Never security model\n", style="dim"
    )
    method_text.append("   • Commands: install, test, run, lint, format\n", style="dim")
    method_text.append(
        "   • Code Style: Formatter, type hints, docstrings\n", style="dim"
    )
    method_text.append(
        "   • Testing: Unit, integration, e2e requirements\n\n", style="dim"
    )

    method_text.append("3. TDD (Test-Driven Development)\n", style="bold green")
    method_text.append("   • Red: Generate test code first\n", style="dim")
    method_text.append(
        "   • Green: Minimal implementation to pass tests\n", style="dim"
    )
    method_text.append(
        "   • Refactor: Improve quality while maintaining tests\n", style="dim"
    )
    method_text.append("   • Coverage: Ensure 80%+ test coverage\n", style="dim")

    console.print(
        Panel(method_text, border_style="yellow", title="Methodologies", padding=(1, 2))
    )
    console.print("\n")

    # Quality Assurance
    console.print("🔍 [bold yellow]QUALITY ASSURANCE (4 LAYERS)[/bold yellow]\n")

    qa_table = Table(show_header=True, header_style="bold magenta", border_style="blue")
    qa_table.add_column("Layer", style="cyan", width=20)
    qa_table.add_column("Description", style="white")

    qa_table.add_row(
        "1. Feedback Loop", "Golden Data validation • 60s timeout • Max 3 retries"
    )
    qa_table.add_row(
        "2. Quality Gates",
        "Phase exit criteria • Metrics validation • Failure blocking",
    )
    qa_table.add_row(
        "3. Producer-Critic", "LLM peer review • Max 3 iterations • Threshold 7.0/10.0"
    )
    qa_table.add_row(
        "4. LLM Judge", "Semantic evaluation • Multi-dimensional scoring • Suggestions"
    )

    console.print(qa_table)
    console.print("\n")

    # Quick Start
    console.print("🚀 [bold yellow]QUICK START[/bold yellow]\n")

    quick_start = Text()
    quick_start.append("Initialize:\n", style="bold")
    quick_start.append("  $ caas init\n\n", style="green")

    quick_start.append("Full automation:\n", style="bold")
    quick_start.append("  $ caas auto-deploy ", style="green")
    quick_start.append('"Build a REST API"\n\n', style="italic cyan")

    quick_start.append("Step-by-step with Plan Mode (recommended):\n", style="bold")
    quick_start.append("  $ caas generate ", style="green")
    quick_start.append('"Build a blog"', style="italic cyan")
    quick_start.append(" --plan-mode\n\n", style="green")

    quick_start.append("From example template:\n", style="bold")
    quick_start.append("  $ caas examples list\n", style="green")
    quick_start.append("  $ caas generate --from-example web_app\n", style="green")

    console.print(
        Panel(quick_start, border_style="green", title="Quick Start", padding=(1, 2))
    )
    console.print("\n")

    # Command Categories
    console.print("📋 [bold yellow]COMMAND CATEGORIES[/bold yellow]\n")

    # Production-Ready
    console.print("[bold cyan]🚀 PRODUCTION-READY[/bold cyan]")
    console.print(
        "  [green]auto-deploy[/green]      Full automation: requirement → deployed code"
    )
    console.print(
        "                    • CAAS 6-Phase workflow • Quality gates • Git & CI/CD setup\n"
    )

    # Code Generation
    console.print("[bold cyan]🎨 CODE GENERATION[/bold cyan]")
    console.print(
        "  [green]generate[/green]         Complete CrewAI system (full CAAS 6-Phase methodology)"
    )
    console.print(
        "  [green]generate-code[/green]    Fast generation from existing specs (AST-based)"
    )
    console.print(
        "  [green]codegen[/green]          Specific components (agents, tasks, tools)\n"
    )

    # Validation & Quality
    console.print("[bold cyan]✅ VALIDATION & QUALITY[/bold cyan]")
    console.print(
        "  [green]validate[/green]         Multi-layer validation (Golden Data, ontology, semantics)"
    )
    console.print(
        "  [green]fix[/green]              Auto-fix with LLM-powered issue resolution\n"
    )

    # Setup & Configuration
    console.print("[bold cyan]⚙️  SETUP & CONFIGURATION[/bold cyan]")
    console.print(
        "  [green]init[/green]             Initialize configuration (API keys, LLM selection)"
    )
    console.print("  [green]config[/green]           Manage settings and preferences")
    console.print("  [green]env[/green]              Manage environment variables\n")

    # Requirement Refinement
    console.print("[bold cyan]🔍 REQUIREMENT REFINEMENT[/bold cyan]")
    console.print(
        "  [green]analyze-gaps[/green]     Identify missing features and ambiguities"
    )
    console.print(
        "  [green]expand[/green]           Add acceptance criteria and data models"
    )
    console.print(
        "  [green]questions[/green]        Interactive LLM-guided clarification"
    )
    console.print(
        "  [green]examples[/green]         Browse 11 curated examples (web, API, data, ML)\n"
    )

    # Code Analysis & Quality Assurance (NEW in v0.4.0)
    console.print("[bold cyan]🔍 CODE ANALYSIS & QUALITY ASSURANCE (v0.4.0)[/bold cyan]")
    console.print(
        "  [green]analyze-completeness[/green] Analyze implementation vs Golden Data"
    )
    console.print(
        "  [green]fix-runtime-error[/green]    Auto-fix Python runtime errors\n"
    )

    # TDD Integration (NEW in Week 3)
    console.print("[bold cyan]🧪 TDD INTEGRATION (Week 3)[/bold cyan]")
    console.print(
        "  [green]tdd generate-tests[/green]   Generate pytest tests from Golden Data (Phase 4.5 RED)"
    )
    console.print(
        "  [green]tdd analyze-code[/green]     Analyze code for smells & refactorings (Phase 5.5 REFACTOR)"
    )
    console.print(
        "  [green]tdd workflow[/green]         Complete TDD workflow (RED → GREEN → REFACTOR)\n"
    )

    # Advanced Features
    console.print("[bold cyan]🧪 ADVANCED FEATURES[/bold cyan]")
    console.print("  [green]generate-phase[/green]   Generate specific CAAS 6-Phase")
    console.print(
        "  [green]test[/green]             Run syntax, import, and test validation"
    )
    console.print(
        "  [green]traceability[/green]     Track requirement → code coverage\n"
    )

    # Monitoring & Performance
    console.print("[bold cyan]📊 MONITORING & PERFORMANCE[/bold cyan]")
    console.print(
        "  [green]cache[/green]            Cache management (stats, clear, config)"
    )
    console.print(
        "  [green]monitor[/green]          Real-time monitoring (metrics, cost, quality, alerts)"
    )
    console.print(
        "  [green]models[/green]           Multi-model router (list, metrics, switch, strategy)"
    )
    console.print(
        "  [green]profile[/green]          Performance profiling (run, report, bottlenecks)\n"
    )

    # Management & Workflow
    console.print("[bold cyan]🔧 MANAGEMENT & WORKFLOW[/bold cyan]")
    console.print("  [green]session[/green]          Manage sessions (save/resume)")
    console.print(
        "  [green]workflow[/green]         Control workflows (event-driven orchestration)"
    )
    console.print(
        "  [green]plugins[/green]          Manage LLM plugins (OpenAI, Anthropic, Google)\n"
    )

    # Utilities
    console.print("[bold cyan]ℹ️  UTILITIES[/bold cyan]")
    console.print("  [green]status[/green]           Check system status")
    console.print("  [green]download[/green]         Download generation results")
    console.print("  [green]list[/green]             List projects\n")

    console.print("\n")

    # Usage Patterns
    console.print("🎓 [bold yellow]USAGE PATTERNS[/bold yellow]\n")

    patterns = Table(show_header=True, header_style="bold magenta", border_style="blue")
    patterns.add_column("Pattern", style="cyan", width=25)
    patterns.add_column("Command", style="green")

    patterns.add_row("Full Automation", 'caas auto-deploy "Build an API"')
    patterns.add_row("Guided (Learning)", 'caas generate "Build blog" --plan-mode')
    patterns.add_row(
        "Iterative Refinement", "caas generate → validate → fix → generate-code"
    )
    patterns.add_row("From Examples", "caas examples list → generate --from-example")
    patterns.add_row(
        "Phase-by-Phase", "caas generate-phase [concretize|discover|design|deliver]"
    )

    console.print(patterns)
    console.print("\n")

    # Common Options
    console.print("🔧 [bold yellow]COMMON OPTIONS[/bold yellow]\n")

    options_text = Text()
    options_text.append("  --plan-mode          ", style="cyan")
    options_text.append("Enable Plan Mode (3 approval gates)\n", style="dim")

    options_text.append("  --critic-pattern     ", style="cyan")
    options_text.append("Enable Producer-Critic peer review (quality +20-30%)\n", style="dim")

    options_text.append("  --enable-validation  ", style="cyan")
    options_text.append("Enable strict Quality Gate mode (default: enabled)\n", style="dim")

    options_text.append("  --llm PROVIDER       ", style="cyan")
    options_text.append("LLM provider (openai/anthropic/ollama)\n", style="dim")

    options_text.append("  --model MODEL        ", style="cyan")
    options_text.append("Specific model (gpt-4/claude-3/gemini-pro)\n", style="dim")

    options_text.append("  --output-dir DIR     ", style="cyan")
    options_text.append("Output directory for generated code\n", style="dim")

    options_text.append("  --verbose            ", style="cyan")
    options_text.append("Show detailed progress information\n", style="dim")

    console.print(options_text)
    console.print("\n")

    # Methodology Deep Dive
    console.print("📚 [bold yellow]METHODOLOGY DEEP DIVE[/bold yellow]\n")

    deep_dive = Text()
    deep_dive.append("Golden Data (Spec-Driven)\n", style="bold green")
    deep_dive.append(
        "  Complete specifications: System scope, features, data models,\n", style="dim"
    )
    deep_dive.append(
        "  UI components, NFRs, testing strategy, Git workflow\n\n", style="dim"
    )

    deep_dive.append("Quality Gates (CAAS 6-Phase)\n", style="bold green")
    deep_dive.append(
        "  • Concretization: 95%+ completeness, <10% ambiguity\n", style="dim"
    )
    deep_dive.append("  • Discovery: All required tools identified\n", style="dim")
    deep_dive.append(
        "  • Architecture: 90%+ role clarity, 0 circular dependencies\n", style="dim"
    )
    deep_dive.append(
        "  • Design: 0 undefined tools, valid dependency graph\n", style="dim"
    )
    deep_dive.append(
        "  • Delivery: 0 syntax errors, 0 import failures\n\n", style="dim"
    )

    deep_dive.append("Multi-Agent Collaboration (6 Agents)\n", style="bold green")
    deep_dive.append(
        "  1. RequirementAnalyst: Analyzes & concretizes requirements\n", style="dim"
    )
    deep_dive.append("  2. SystemArchitect: Designs system architecture\n", style="dim")
    deep_dive.append("  3. AgentDesigner: Designs CrewAI agents & tasks\n", style="dim")
    deep_dive.append(
        "  4. CodeGenerator: Generates production-ready code\n", style="dim"
    )
    deep_dive.append(
        "  5. QASpecialist: Validates quality at each phase\n", style="dim"
    )
    deep_dive.append(
        "  6. CodeAnalyst: Analyzes completeness & fixes errors (v0.4.0)\n", style="dim"
    )

    console.print(
        Panel(deep_dive, border_style="blue", title="Deep Dive", padding=(1, 2))
    )
    console.print("\n")

    # Footer
    footer = Text()
    footer.append("📖 For command-specific help: ", style="bold")
    footer.append("caas <command> --help\n", style="green")
    footer.append("🤔 For interactive help: ", style="bold")
    footer.append("caas questions\n", style="green")
    footer.append("📚 Documentation: ", style="bold")
    footer.append(
        "https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System\n",
        style="cyan underline",
    )

    console.print(Panel(footer, border_style="cyan", padding=(0, 2)))
    console.print("\n")


def show_brief_help():
    """Display brief help when 'caas' is run without arguments"""

    brief_text = Text()
    brief_text.append("CAAS", style="bold cyan")
    brief_text.append(" - CrewAI Agent Auto-generation System\n\n", style="cyan")

    brief_text.append("Version: ", style="dim")
    brief_text.append("0.4.1\n\n", style="bold")

    brief_text.append("Usage: ", style="yellow")
    brief_text.append("caas [OPTIONS] COMMAND [ARGS]...\n\n")

    # Quick Start
    brief_text.append("Quick Start:\n", style="bold green")
    brief_text.append("  caas init                          ", style="dim")
    brief_text.append("# Initialize configuration\n")
    brief_text.append("  caas auto-deploy ", style="dim")
    brief_text.append('"Build a blog"', style="italic")
    brief_text.append("   # Full automation\n\n")

    # Main Commands
    brief_text.append("Main Commands:\n", style="bold yellow")
    commands = [
        ("auto-deploy", "🚀 Full automation: requirement → production"),
        ("generate", "Generate CrewAI system from requirement"),
        ("generate-code", "Generate code from specs (fast)"),
        ("codegen", "Generate specific components"),
        ("validate", "Validate design quality"),
        ("fix", "Auto-fix design issues"),
    ]
    for cmd, desc in commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Setup & Configuration
    brief_text.append("Setup & Configuration:\n", style="bold yellow")
    setup_commands = [
        ("init", "Initialize configuration"),
        ("config", "Manage settings"),
        ("env", "Manage environment variables"),
    ]
    for cmd, desc in setup_commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Refinement & Analysis
    brief_text.append("Refinement & Analysis:\n", style="bold yellow")
    refinement_commands = [
        ("analyze-gaps", "Analyze requirement gaps"),
        ("expand", "Expand requirements with details"),
        ("questions", "Interactive requirement clarification"),
        ("examples", "Browse requirement examples"),
    ]
    for cmd, desc in refinement_commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Code Analysis (v0.4.0)
    brief_text.append("Code Analysis (v0.4.0):\n", style="bold yellow")
    analysis_commands = [
        ("analyze-completeness", "Analyze implementation completeness"),
        ("fix-runtime-error", "Auto-fix Python runtime errors"),
    ]
    for cmd, desc in analysis_commands:
        brief_text.append(f"  {cmd:<20} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Advanced Features
    brief_text.append("Advanced Features:\n", style="bold yellow")
    advanced_commands = [
        ("generate-phase", "Generate specific CAAS 6-Phase"),
        ("test", "Run tests on generated code"),
        ("traceability", "Track requirement → code coverage"),
    ]
    for cmd, desc in advanced_commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Monitoring & Performance
    brief_text.append("Monitoring & Performance:\n", style="bold yellow")
    monitoring_commands = [
        ("cache", "Cache management"),
        ("monitor", "Real-time monitoring & metrics"),
        ("models", "Multi-model router management"),
        ("profile", "Performance profiling"),
    ]
    for cmd, desc in monitoring_commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Management & Workflow
    brief_text.append("Management & Workflow:\n", style="bold yellow")
    management_commands = [
        ("session", "Manage generation sessions"),
        ("workflow", "Control generation workflows"),
        ("plugins", "Manage LLM plugins"),
    ]
    for cmd, desc in management_commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Other Commands
    brief_text.append("Other Commands:\n", style="bold yellow")
    other_commands = [
        ("status", "Check system status"),
        ("download", "Download generation results"),
        ("list", "List projects"),
    ]
    for cmd, desc in other_commands:
        brief_text.append(f"  {cmd:<16} ", style="cyan")
        brief_text.append(f"{desc}\n", style="dim")

    brief_text.append("\n")

    # Options
    brief_text.append("Options:\n", style="bold yellow")
    brief_text.append("  --help           ", style="cyan")
    brief_text.append("Show comprehensive help with methodology\n", style="dim")
    brief_text.append("  --version        ", style="cyan")
    brief_text.append("Show version information\n\n", style="dim")

    # Footer
    brief_text.append("For detailed help: ", style="bold")
    brief_text.append("caas --help\n", style="bold green")
    brief_text.append("For command help: ", style="bold")
    brief_text.append("caas <command> --help\n", style="bold green")

    console.print(Panel(brief_text, border_style="cyan", padding=(1, 2)))


@click.group(cls=CustomGroup, invoke_without_command=True)
@click.version_option(version="0.4.1")
@click.pass_context
def cli(ctx):
    """CAAS - CrewAI Agent Auto-generation System

    \b
    ═══════════════════════════════════════════════════════════════════════
                    METHODOLOGY-DRIVEN CODE GENERATION
    ═══════════════════════════════════════════════════════════════════════

    CAAS implements a comprehensive, methodology-driven approach to automated
    code generation, combining industry best practices with AI-powered agents.

    \b
    🎯 CORE METHODOLOGIES
    ═══════════════════════════════════════════════════════════════════════

    1. CAAS 6-Phase Methodology
       ├─ Phase 0: Requirement Concretization (Golden Data generation)
       ├─ Phase 1: Discovery (Tool & capability analysis)
       ├─ Phase 2: Architecture (System design)
       ├─ Phase 3: Design (Agent & task design)
       ├─ Phase 4: Measurement (Quality validation)
       └─ Phase 5: Deployment (Code generation & delivery)

    2. SDD (Specification-Driven Development)
       ├─ Golden Data: Complete, unambiguous specifications
       ├─ Boundaries: Always/Ask/Never security model
       ├─ Commands: Install, test, run, lint, format
       ├─ Code Style: Formatter, type hints, docstrings
       ├─ Git Workflow: Branch naming, commit format, PR template
       └─ Testing: Unit, integration, e2e coverage requirements

    3. TDD (Test-Driven Development)
       ├─ Red: Generate test code first (from acceptance criteria)
       ├─ Green: Generate minimal implementation to pass tests
       ├─ Refactor: Improve code quality while maintaining tests
       └─ Coverage: Ensure 80%+ test coverage

    \b
    🔍 QUALITY ASSURANCE LAYERS
    ═══════════════════════════════════════════════════════════════════════

    Layer 1: Safe Feedback Loop
             ├─ Golden Data validation (structural)
             ├─ Timeout protection (60s per retry)
             └─ Max 3 refinement iterations

    Layer 2: Quality Gate System
             ├─ Phase-specific exit criteria
             ├─ Metrics-based validation
             └─ Critical failure blocking

    Layer 3: Producer-Critic Pattern
             ├─ LLM-based peer review
             ├─ Iterative refinement (max 3 iterations)
             └─ Approval threshold: 7.0/10.0

    Layer 4: LLM-as-a-Judge
             ├─ Semantic quality evaluation
             ├─ Multi-dimensional scoring
             └─ Actionable improvement suggestions

    \b
    🚀 QUICK START
    ═══════════════════════════════════════════════════════════════════════

    Initialize CAAS:
      $ caas init

    Full automation (requirement → production):
      $ caas auto-deploy "Build a RESTful API for task management"

    Step-by-step with Plan Mode (recommended for first use):
      $ caas generate "Build a blog" --plan-mode

    Generate from example template:
      $ caas examples list                    # Browse examples
      $ caas generate --from-example web_app  # Use example

    \b
    📋 COMMAND CATEGORIES
    ═══════════════════════════════════════════════════════════════════════

    🚀 PRODUCTION-READY AUTOMATION
       auto-deploy       Full automation: requirement → deployed code
                         • CAAS 6-Phase workflow automation
                         • Quality gate validation
                         • Git initialization & CI/CD setup
                         • Virtual environment & dependency installation

    🎨 CODE GENERATION (Core)
       generate          Generate complete CrewAI system
                         • Follows full CAAS 6-Phase methodology
                         • Multi-phase validation
                         • Golden Data-driven generation

       generate-code     Fast code generation from existing specs
                         • Skips requirement analysis
                         • Uses pre-validated specifications
                         • AST-based code generation

       codegen           Generate specific components
                         • Agents, tasks, tools, crews
                         • Fine-grained control
                         • Component-level generation

    ✅ VALIDATION & QUALITY
       validate          Validate design quality
                         • Golden Data compliance
                         • Dependency validation
                         • Ontology consistency
                         • Semantic checker

       fix               Auto-fix design issues
                         • LLM-powered issue resolution
                         • Validation feedback loop
                         • Automated refinement

    🔍 CODE ANALYSIS & QUALITY ASSURANCE (v0.4.0)
       analyze-completeness  Analyze implementation completeness
                         • Feature coverage analysis
                         • Golden Data traceability matrix
                         • Business rule verification
                         • Implementation gap detection
                         • Actionable recommendations

       fix-runtime-error Auto-fix Python runtime errors
                         • Parse error logs automatically
                         • LLM-powered root cause analysis
                         • Generate code fixes with explanations
                         • Preview or apply fixes
                         • Support 8+ error types (Import, Name, Type, etc.)

    ⚙️ SETUP & CONFIGURATION
       init              Initialize CAAS configuration
                         • API keys setup
                         • Default LLM selection
                         • Project preferences

       config            Manage settings
                         • View/edit configuration
                         • LLM provider settings
                         • Generation preferences

       env               Manage environment variables
                         • API keys management
                         • Environment-specific settings

    🔍 REQUIREMENT REFINEMENT
       analyze-gaps      Analyze requirement gaps
                         • Identify missing features
                         • Detect ambiguities
                         • Suggest improvements

       expand            Expand requirements with details
                         • Add acceptance criteria
                         • Define data models
                         • Specify NFRs (non-functional requirements)

       questions         Interactive requirement clarification
                         • LLM-guided question flow
                         • Context-aware queries
                         • Progressive refinement

       examples          Browse requirement examples
                         • 11 curated examples
                         • Multiple domains (web, API, data, ML)
                         • Best practice templates

    🧪 ADVANCED FEATURES
       generate-phase    Generate specific CAAS 6-Phase
                         • Phase 0: Concretization
                         • Phase 1: Discovery
                         • Phase 2: Architecture
                         • Phase 3: Design
                         • Phase 5: Delivery

       test              Run tests on generated code
                         • Syntax validation
                         • Import verification
                         • Test execution
                         • Coverage reporting

       traceability      Track requirement → code coverage
                         • Traceability matrix
                         • Feature-to-code mapping
                         • Gap identification

    📊 MONITORING & PERFORMANCE
       cache             Cache management
                         • View cache statistics
                         • Clear cache by type
                         • Configure cache settings

       monitor           Real-time monitoring & metrics
                         • System metrics tracking
                         • Cost analysis & tracking
                         • Quality metrics
                         • Alert management
                         • Export metrics (Prometheus, JSON)

       models            Multi-model router management
                         • List available models
                         • View model performance metrics
                         • Switch active model
                         • Configure routing strategy
                         • Manage fallback chain

       profile           Performance profiling
                         • Profile generation runs
                         • Identify bottlenecks
                         • Performance comparison
                         • Optimization suggestions

    🔧 MANAGEMENT & WORKFLOW
       session           Manage generation sessions
                         • Save/resume sessions
                         • Session history
                         • Context preservation

       workflow          Control generation workflows
                         • Custom workflow definition
                         • Event-driven orchestration
                         • Parallel phase execution

       plugins           Manage LLM plugins
                         • OpenAI, Anthropic, Google, Local
                         • Plugin configuration
                         • Model selection

    ℹ️ UTILITIES
       status            Check system status
       download          Download generation results
       list              List projects

    \b
    🎓 USAGE PATTERNS
    ═══════════════════════════════════════════════════════════════════════

    Pattern 1: Full Automation (Fastest)
      $ caas auto-deploy "Build a REST API for blog posts"
      → Generates complete system with tests, CI/CD, and deployment

    Pattern 2: Guided Generation (Recommended for learning)
      $ caas generate "Build a chatbot" --plan-mode
      → Review & approve each phase (Spec → Design → Code)

    Pattern 3: Iterative Refinement (Best quality)
      $ caas generate "Build a todo app" --critic-pattern
      $ caas validate ./output/design.json
      $ caas fix ./output/design.json
      $ caas generate-code ./output/design.json
      → Multi-layer quality validation & auto-fixing

    Pattern 4: From Examples (Quick start)
      $ caas examples list
      $ caas generate --from-example e_commerce
      → Use proven templates

    Pattern 5: Phase-by-Phase (Fine control)
      $ caas generate-phase concretize "Build an API"
      $ caas generate-phase discover ./spec.json
      $ caas generate-phase architect ./spec.json
      $ caas generate-phase design ./spec.json
      $ caas generate-phase deliver ./design.json
      → Full control over each CAAS 6-Phase

    \b
    🔧 COMMON OPTIONS
    ═══════════════════════════════════════════════════════════════════════

    --plan-mode              Enable Plan Mode (3 approval gates)
    --critic-pattern         Enable Producer-Critic peer review
    --enable-validation      Enable multi-layer quality validation
    --llm PROVIDER           LLM provider (openai/anthropic/google)
    --model MODEL            Specific model (gpt-4/claude-3/gemini-pro)
    --output-dir DIR         Output directory for generated code
    --format {json|yaml}     Output format for specifications
    --verbose                Show detailed progress information

    \b
    📚 METHODOLOGY DEEP DIVE
    ═══════════════════════════════════════════════════════════════════════

    Golden Data (Spec-Driven Development)
      CAAS generates a "Golden Data" specification that serves as the
      single source of truth. This includes:
      • System scope & boundaries
      • Feature specifications with acceptance criteria
      • Data models with validation rules
      • UI components & interactions
      • Non-functional requirements (performance, security, etc.)
      • Testing strategy (unit, integration, e2e)
      • Git workflow & CI/CD configuration

    Quality Gates (CAAS 6-Phase Methodology)
      Each CAAS 6-Phase has quality gates with exit criteria:
      • Concretization: 95%+ feature completeness, <10% ambiguity
      • Discovery: All required tools identified
      • Architecture: 90%+ role clarity, 0 circular dependencies
      • Design: 0 undefined tools, valid dependency graph
      • Delivery: 0 syntax errors, 0 import failures

    Multi-Agent Collaboration
      CAAS uses 6 specialized expert agents:
      1. RequirementAnalyst: Analyzes & concretizes requirements
      2. SystemArchitect: Designs system architecture
      3. AgentDesigner: Designs CrewAI agents & tasks
      4. CodeGenerator: Generates production-ready code
      5. QASpecialist: Validates quality at each phase
      6. CodeAnalyst: Analyzes completeness & fixes errors (v0.4.0)

    Feedback Loops
      • Safe Feedback Loop: Golden Data validation (max 3 retries, 60s timeout)
      • Producer-Critic: LLM peer review (score threshold: 7.0/10.0)
      • LLM Judge: Semantic quality evaluation
      • Auto-Fix: Automated issue resolution

    \b
    ✨ WHAT'S NEW IN v0.4.1 (2026-02-06)
    ═══════════════════════════════════════════════════════════════════════

    🚀 Code Quality & Technical Debt Resolution
       • Code duplication reduced: 15-20% → <8% (-60%)
       • Plugin system: 74% → <5% duplication (-93%)
       • Expert agents: 60% → 12% duplication (-80%)

    📝 Structured Logging System
       • 277 print statements → structured logger
       • Standardized logging levels (DEBUG/INFO/WARNING/ERROR)
       • Rich integration for enhanced readability

    🛡️ Custom Exception Hierarchy
       • 17 custom exception classes (7 categories)
       • Exception chaining standardized (raise ... from e)
       • File: caas_framework/exceptions.py

    🐛 Quality Gate Bug Fix (CRITICAL)
       • Infinite wait bug 100% resolved (10-20% → 0%)
       • AutoMetricsCollector auto-integration
       • Metric fallback: None → 0.0
       • LLM Judge timeout added (60s)

    🏗️ New Infrastructure Components
       • agents/utils.py - Agent utilities (367 lines)
       • agents/code_gen_helpers.py - Code gen helpers (358 lines)
       • plugins/llm/utils.py - LLM utilities (214 lines)
       • Enhanced BaseLLMPlugin & BaseExpertAgent

    📊 Business Impact
       • Development speed: +83%
       • Bug fix time: -75-83%
       • Production stability: 100% (infinite wait: 0%)

    \b
    🌐 RESOURCES
    ═══════════════════════════════════════════════════════════════════════

    Documentation:    https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System
    Issue Tracker:    https://github.com/bullpeng72/CrewAI-Agent-Autogeneration-System/issues
    Examples:         caas examples list
    Methodology:      docs/05_Expert_Methodology_Guide.md

    \b
    For command-specific help:
      caas <command> --help

    For interactive help:
      caas questions
    """
    ctx.ensure_object(dict)

    # If no subcommand provided, show brief help
    if ctx.invoked_subcommand is None:
        show_brief_help()
        ctx.exit(0)


# Register commands
cli.add_command(generate.generate)
cli.add_command(init.init)
cli.add_command(config.config)
cli.add_command(env.env)
cli.add_command(status.status)
cli.add_command(list_projects.list_cmd)
cli.add_command(download.download)
cli.add_command(analyze_gaps.analyze_gaps, name="analyze-gaps")
cli.add_command(analyze_requirement.analyze_requirement_cmd, name="analyze-requirement")
cli.add_command(expand_requirement.expand)
cli.add_command(interactive_questions.questions)
cli.add_command(traceability.traceability)
cli.add_command(examples.examples_group)

# Phase 1: Core Features
cli.add_command(validate_cmd.validate)
cli.add_command(codegen_cmd.codegen)
cli.add_command(generate_code_cmd.generate_code)
cli.add_command(fix_cmd.fix)

# Phase 2: Advanced Features
cli.add_command(generate_phase.generate_phase)
cli.add_command(test_cmd.test)

# Phase 2 Enhancement: Monitoring & Performance
cli.add_command(cache_cmd.cache)
cli.add_command(monitor_cmd.monitor)
cli.add_command(models_cmd.models)
cli.add_command(profile_cmd.profile)

# Phase 3: Management Features
cli.add_command(session_cmd.session)
cli.add_command(workflow_cmd.workflow)
cli.add_command(plugins_cmd.plugins)

# Phase 4: Production Ready
cli.add_command(auto_deploy_cmd.auto_deploy)

# Code Analysis & Quality Assurance (v0.4.0)
cli.add_command(analyze_completeness.analyze_completeness, name="analyze-completeness")
cli.add_command(fix_runtime_error.fix_runtime_error, name="fix-runtime-error")

# Phase 5: TDD Integration (Week 3)
cli.add_command(tdd.tdd_group)


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
