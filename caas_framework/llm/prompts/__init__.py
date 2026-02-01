"""
CAAS Framework LLM Prompts

Prompt templates for various LLM operations.
"""

from caas_framework.llm.prompts.analysis import (
    REQUIREMENT_ANALYSIS_SYSTEM,
    REQUIREMENT_ANALYSIS_USER,
    AGENT_DESIGN_SYSTEM,
    AGENT_DESIGN_USER,
    TASK_DESIGN_SYSTEM,
    TASK_DESIGN_USER,
    ONTOLOGY_CONTEXT_TEMPLATE,
    PATTERN_CONTEXT_TEMPLATE,
)

from caas_framework.llm.prompts.domain_classification import (
    DOMAIN_CLASSIFICATION_SYSTEM,
    DOMAIN_CLASSIFICATION_USER,
    DOMAIN_CLASSIFICATION_USER_KO,
)

from caas_framework.llm.prompts.spec_generation import (
    SPEC_GENERATION_SYSTEM,
    SPEC_GENERATION_USER,
    SPEC_VALIDATION_SYSTEM,
    SPEC_VALIDATION_USER,
)

from caas_framework.llm.prompts.concretization import (
    CONCRETIZATION_SYSTEM,
    CONCRETIZATION_USER_TEMPLATE,
)

__all__ = [
    # Analysis prompts
    "REQUIREMENT_ANALYSIS_SYSTEM",
    "REQUIREMENT_ANALYSIS_USER",
    "AGENT_DESIGN_SYSTEM",
    "AGENT_DESIGN_USER",
    "TASK_DESIGN_SYSTEM",
    "TASK_DESIGN_USER",
    "ONTOLOGY_CONTEXT_TEMPLATE",
    "PATTERN_CONTEXT_TEMPLATE",
    # Domain classification prompts
    "DOMAIN_CLASSIFICATION_SYSTEM",
    "DOMAIN_CLASSIFICATION_USER",
    "DOMAIN_CLASSIFICATION_USER_KO",
    # Spec generation prompts
    "SPEC_GENERATION_SYSTEM",
    "SPEC_GENERATION_USER",
    "SPEC_VALIDATION_SYSTEM",
    "SPEC_VALIDATION_USER",
    # Concretization prompts
    "CONCRETIZATION_SYSTEM",
    "CONCRETIZATION_USER_TEMPLATE",
]
