"""
Examples Module

Provides example requirements and templates to help users write better project specifications.
"""

from caas_framework.examples.requirement_examples import (
    RequirementExample,
    Domain,
    Complexity,
    REQUIREMENT_EXAMPLES,
    get_examples_by_domain,
    get_examples_by_complexity,
    get_examples_by_tag,
    search_examples,
    get_example_summary,
    suggest_examples
)

__all__ = [
    "RequirementExample",
    "Domain",
    "Complexity",
    "REQUIREMENT_EXAMPLES",
    "get_examples_by_domain",
    "get_examples_by_complexity",
    "get_examples_by_tag",
    "search_examples",
    "get_example_summary",
    "suggest_examples"
]
