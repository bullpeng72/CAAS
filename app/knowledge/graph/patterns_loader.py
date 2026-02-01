"""
Pattern Loader - Phase 1 Task P1.2

Replaces 379-line _load_builtin_patterns() with simple YAML loader.
"""

import yaml
from pathlib import Path
from typing import List
from app.knowledge.graph.patterns import AgentPattern, PatternType


def load_builtin_patterns() -> List[AgentPattern]:
    """
    Load built-in patterns from YAML file.

    Replaces the 379-line hardcoded _load_builtin_patterns() method.

    Returns:
        List[AgentPattern]: List of built-in agent patterns

    Raises:
        FileNotFoundError: If patterns.yaml not found
        yaml.YAMLError: If YAML parsing fails
    """
    # Find patterns.yaml
    patterns_file = Path(__file__).parent.parent.parent.parent / "caas_framework" / "data" / "patterns.yaml"

    if not patterns_file.exists():
        raise FileNotFoundError(
            f"Patterns file not found: {patterns_file}\n"
            f"Expected at: caas_framework/data/patterns.yaml"
        )

    # Load YAML
    with open(patterns_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data or 'patterns' not in data:
        raise ValueError("Invalid patterns.yaml: missing 'patterns' key")

    # Convert to AgentPattern objects
    patterns = []
    for pattern_data in data['patterns']:
        pattern = AgentPattern(
            id=pattern_data['id'],
            name=pattern_data['name'],
            description=pattern_data['description'],
            pattern_type=PatternType(pattern_data['pattern_type']),
            agent_roles=pattern_data['agent_roles'],
            task_types=pattern_data['task_types'],
            recommended_tools=pattern_data['recommended_tools'],
            workflow_type=pattern_data['workflow_type'],
            use_case=pattern_data['use_case'],
            usage_count=pattern_data['usage_count'],
            success_rate=pattern_data['success_rate'],
            domain=pattern_data['domain'],
            version=pattern_data['version'],
            is_builtin=pattern_data['is_builtin'],
            agents=pattern_data.get('agents', []),
            tasks=pattern_data.get('tasks', [])
        )
        patterns.append(pattern)

    return patterns


