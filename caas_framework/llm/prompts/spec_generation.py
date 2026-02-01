"""
Specification Generation Prompts

Prompt templates for generating and validating specifications.
"""

# TODO: Implement actual prompt templates
# These are placeholders until proper prompts are defined

SPEC_GENERATION_SYSTEM = """You are an expert specification writer.
Generate detailed technical specifications based on requirements.

Respond with a JSON object containing agent and task specifications."""

SPEC_GENERATION_USER = """Generate specifications for the following requirement:

{requirement}

Include:
- Agent specifications (roles, goals, tools)
- Task specifications (descriptions, outputs, dependencies)
- Workflow configuration"""

SPEC_VALIDATION_SYSTEM = """You are an expert specification validator.
Validate that specifications meet quality standards and are complete.

Respond with a JSON object containing validation results."""

SPEC_VALIDATION_USER = """Validate the following specification:

{specification}

Check for:
- Completeness (all required fields present)
- Consistency (no contradictions)
- Feasibility (can be implemented)
- Quality (meets best practices)"""
