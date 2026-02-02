"""
CLI Commands
"""

from caas_cli.commands import (
    generate,
    init,
    config,
    env,
    status,
    list_projects,
    download,
    analyze_gaps,
    expand_requirement,
    interactive_questions,
    traceability,
    examples,
    # Phase 1: Core Features
    validate_cmd,
    codegen_cmd,
    generate_code_cmd,
    fix_cmd,
    # Phase 2: Advanced Features
    generate_phase,
    test_cmd,
    # Phase 2 Enhancement: Monitoring & Performance
    cache_cmd,
    monitor_cmd,
    models_cmd,
    profile_cmd,
    # Phase 3: Management Features
    session_cmd,
    workflow_cmd,
    plugins_cmd,
    # Phase 4: Production Ready
    auto_deploy_cmd
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
    "auto_deploy_cmd"
]
