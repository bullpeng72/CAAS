"""
Concretization Prompts

Prompt templates for concretizing requirements into detailed specifications.
"""

# TODO: Implement actual prompt templates
# These are placeholders until proper prompts are defined

CONCRETIZATION_SYSTEM = """You are an expert requirement concretization specialist.
Transform high-level requirements into detailed, concrete specifications.

Respond with a JSON object following the ConcretizedRequirement schema."""

CONCRETIZATION_USER_TEMPLATE = """Concretize the following requirement:

{requirement}

Analysis context:
{analysis}

Provide detailed specifications including:
- System scope and boundaries
- Feature breakdowns
- Data models
- UI components (if applicable)
- Non-functional requirements
- Constraints and assumptions
- Success criteria"""
