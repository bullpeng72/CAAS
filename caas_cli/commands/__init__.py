"""
CLI Commands
"""

from caas_cli.commands import (  # Phase 1: Core Features; Phase 2: Advanced Features; Phase 2 Enhancement: Monitoring & Performance; Phase 3: Management Features; Phase 4: Production Ready; Phase 5: TDD Integration; Phase 6: SDD YAML Export
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
    export_specs,
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

__all__ = [
    "generate",
    "init",
    "config",
    "env",
    "status",
    "list_projects",
    "download",
    "analyze_gaps",
    "analyze_requirement",
    "expand_requirement",
    "interactive_questions",
    "traceability",
    "examples",
    # Phase 1
    "validate_cmd",
    "codegen_cmd",
    "generate_code_cmd",
    "fix_cmd",
    # Phase 2
    "generate_phase",
    "test_cmd",
    # Phase 2 Enhancement
    "cache_cmd",
    "monitor_cmd",
    "models_cmd",
    "profile_cmd",
    # Phase 3
    "session_cmd",
    "workflow_cmd",
    "plugins_cmd",
    # Phase 4
    "auto_deploy_cmd",
    "analyze_completeness",
    "analyze_requirement",
    "fix_runtime_error",
    # Phase 5: TDD Integration
    "tdd",
    # Phase 6: SDD YAML Export (Week 4)
    "export_specs",
]
