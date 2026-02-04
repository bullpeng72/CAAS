"""
CLI Commands
"""

from caas_cli.commands import (  # Phase 1: Core Features; Phase 2: Advanced Features; Phase 2 Enhancement: Monitoring & Performance; Phase 3: Management Features; Phase 4: Production Ready
    analyze_completeness,
    analyze_gaps,
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
    "fix_runtime_error",
]
