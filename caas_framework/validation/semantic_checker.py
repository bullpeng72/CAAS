"""
Semantic Consistency Checker

Validates that requirement specifications don't contain contradictory or
incompatible requirements, improving design quality.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from caas_framework.models.specifications import ConcretizedRequirement


@dataclass
class Contradiction:
    """Represents a semantic contradiction in requirements."""

    concept_a: str
    concept_b: str
    reason: str
    severity: str = "warning"  # "warning", "error", "critical"
    location: Optional[str] = None


class ContradictionReport(BaseModel):
    """Report of all contradictions found."""

    contradictions: List[Dict[str, str]] = Field(default_factory=list)
    has_contradictions: bool = False
    severity_counts: Dict[str, int] = Field(default_factory=dict)


class SemanticConsistencyChecker:
    """
    Validates semantic consistency of requirement specifications.

    Uses both rule-based and LLM-based checking to detect contradictions
    and incompatible requirements.
    """

    # Known contradiction rules
    CONTRADICTION_RULES = [
        {
            "concept_a": "realtime",
            "concept_b": "rest_only",
            "reason": "Real-time features require WebSocket or similar, not just REST API",
            "severity": "error",
            "keywords_a": ["realtime", "real-time", "websocket", "socket.io", "live"],
            "keywords_b": ["rest only", "restful only", "no websocket"],
        },
        {
            "concept_a": "serverless",
            "concept_b": "stateful_session",
            "reason": "Serverless functions are stateless by design",
            "severity": "error",
            "keywords_a": ["serverless", "lambda", "cloud function"],
            "keywords_b": ["stateful", "session state", "maintain state"],
        },
        {
            "concept_a": "nosql",
            "concept_b": "complex_joins",
            "reason": "NoSQL databases don't support complex SQL joins well",
            "severity": "warning",
            "keywords_a": ["nosql", "mongodb", "dynamodb", "cassandra"],
            "keywords_b": ["complex join", "multi-table join", "sql join"],
        },
        {
            "concept_a": "microservices",
            "concept_b": "shared_database",
            "reason": "Microservices should have independent databases (database per service)",
            "severity": "warning",
            "keywords_a": ["microservice", "micro-service"],
            "keywords_b": ["shared database", "single database", "common database"],
        },
        {
            "concept_a": "synchronous",
            "concept_b": "high_scalability",
            "reason": "Synchronous operations can limit scalability; consider async",
            "severity": "warning",
            "keywords_a": ["synchronous", "blocking", "sync"],
            "keywords_b": ["high scalability", "millions of users", "massive scale"],
        },
        {
            "concept_a": "local_storage",
            "concept_b": "distributed_system",
            "reason": "Local storage doesn't work well in distributed systems",
            "severity": "error",
            "keywords_a": ["local storage", "file system", "local file"],
            "keywords_b": ["distributed", "multi-server", "cluster"],
        },
        {
            "concept_a": "acid_transactions",
            "concept_b": "eventual_consistency",
            "reason": "ACID transactions and eventual consistency are conflicting consistency models",
            "severity": "error",
            "keywords_a": ["acid", "strong consistency", "transaction"],
            "keywords_b": ["eventual consistency", "eventually consistent"],
        },
        {
            "concept_a": "monolithic",
            "concept_b": "independent_deployment",
            "reason": "Monolithic architecture doesn't support independent deployment of components",
            "severity": "warning",
            "keywords_a": ["monolithic", "monolith"],
            "keywords_b": ["independent deploy", "separate deploy", "deploy independently"],
        },
        {
            "concept_a": "client_side_only",
            "concept_b": "server_processing",
            "reason": "Client-side only apps can't do server-side processing",
            "severity": "error",
            "keywords_a": ["client-side only", "frontend only", "no backend"],
            "keywords_b": ["server process", "backend logic", "server-side"],
        },
        {
            "concept_a": "graphql",
            "concept_b": "rest_strict",
            "reason": "GraphQL and strict REST are different API paradigms, choose one",
            "severity": "warning",
            "keywords_a": ["graphql", "graph ql"],
            "keywords_b": ["rest only", "restful strict", "pure rest"],
        },
        {
            "concept_a": "static_site",
            "concept_b": "dynamic_content",
            "reason": "Static sites can't generate truly dynamic content without backend",
            "severity": "warning",
            "keywords_a": ["static site", "static website", "jamstack"],
            "keywords_b": ["dynamic content", "user-generated", "personalized"],
        },
        {
            "concept_a": "sql_database",
            "concept_b": "schema_free",
            "reason": "SQL databases require schemas; use NoSQL for schema-free data",
            "severity": "warning",
            "keywords_a": ["sql", "postgresql", "mysql", "relational"],
            "keywords_b": ["schema-free", "schemaless", "no schema"],
        },
    ]

    def __init__(self, llm_provider: Optional[Any] = None):
        """
        Initialize the semantic consistency checker.

        Args:
            llm_provider: Optional LLM provider for advanced checking
        """
        self.llm_provider = llm_provider

    def check_consistency(self, concretized: ConcretizedRequirement) -> List[Contradiction]:
        """
        Check semantic consistency of concretized requirements.

        Args:
            concretized: The concretized requirement specification

        Returns:
            List of contradictions found
        """
        contradictions = []

        # Extract all requirements as text
        all_requirements = self._extract_requirements(concretized)

        # Rule-based checking
        rule_contradictions = self._rule_based_check(all_requirements)
        contradictions.extend(rule_contradictions)

        # LLM-based checking (if available and contradictions found)
        if self.llm_provider and rule_contradictions:
            llm_contradictions = self._llm_consistency_check(all_requirements)
            contradictions.extend(llm_contradictions)

        return contradictions

    def _extract_requirements(self, concretized: ConcretizedRequirement) -> List[str]:
        """
        Extract all requirements as text strings.

        Args:
            concretized: The concretized requirement

        Returns:
            List of requirement strings
        """
        requirements = []

        # Extract from system scope
        if hasattr(concretized, "system_scope"):
            requirements.append(f"Project: {concretized.system_scope.project_name}")
            requirements.append(f"Purpose: {concretized.system_scope.purpose}")
            requirements.append(f"Type: {concretized.system_scope.system_type}")

        # Extract from features
        for feature in concretized.features:
            requirements.append(f"Feature: {feature.name} - {feature.description}")
            if hasattr(feature, "acceptance_criteria"):
                for criteria in feature.acceptance_criteria:
                    requirements.append(f"Criteria: {criteria}")

        # Extract from non-functional requirements
        if hasattr(concretized, "non_functional_requirements"):
            for key, value in concretized.non_functional_requirements.items():
                requirements.append(f"NFR {key}: {value}")

        # Extract from constraints
        if hasattr(concretized, "constraints"):
            for constraint in concretized.constraints:
                requirements.append(f"Constraint: {constraint}")

        return requirements

    def _rule_based_check(self, requirements: List[str]) -> List[Contradiction]:
        """
        Check for contradictions using predefined rules.

        Args:
            requirements: List of requirement strings

        Returns:
            List of contradictions found
        """
        contradictions = []

        # Convert all requirements to lowercase for matching
        req_text = " ".join(requirements).lower()

        for rule in self.CONTRADICTION_RULES:
            # Check if concept A is present
            concept_a_present = any(keyword in req_text for keyword in rule["keywords_a"])

            # Check if concept B is present
            concept_b_present = any(keyword in req_text for keyword in rule["keywords_b"])

            # If both present, we have a contradiction
            if concept_a_present and concept_b_present:
                # Find which specific requirements contain these concepts
                location = self._find_location(requirements, rule)

                contradictions.append(
                    Contradiction(
                        concept_a=rule["concept_a"],
                        concept_b=rule["concept_b"],
                        reason=rule["reason"],
                        severity=rule["severity"],
                        location=location,
                    )
                )

        return contradictions

    def _find_location(self, requirements: List[str], rule: Dict[str, Any]) -> str:
        """
        Find which requirements contain the contradictory concepts.

        Args:
            requirements: List of requirement strings
            rule: The contradiction rule

        Returns:
            Description of where contradiction was found
        """
        locations_a = []
        locations_b = []

        for req in requirements:
            req_lower = req.lower()

            if any(kw in req_lower for kw in rule["keywords_a"]):
                locations_a.append(req[:100])

            if any(kw in req_lower for kw in rule["keywords_b"]):
                locations_b.append(req[:100])

        if locations_a and locations_b:
            return f"'{locations_a[0]}...' conflicts with '{locations_b[0]}...'"

        return "Multiple requirements"

    def _llm_consistency_check(self, requirements: List[str]) -> List[Contradiction]:
        """
        Use LLM to check for semantic contradictions.

        Args:
            requirements: List of requirement strings

        Returns:
            List of contradictions found by LLM
        """
        if not self.llm_provider:
            return []

        prompt = f"""Analyze these requirements for semantic contradictions or incompatibilities:

{chr(10).join(f"{i+1}. {req}" for i, req in enumerate(requirements))}

Find any contradictory, conflicting, or incompatible requirements.
Consider technical limitations, architectural incompatibilities, and logical conflicts.

Respond in JSON format:
{{
    "contradictions": [
        {{
            "concept_a": "brief name of first concept",
            "concept_b": "brief name of second concept",
            "reason": "explanation of why these conflict",
            "severity": "warning or error"
        }}
    ]
}}

If no contradictions found, return empty array.
"""

        try:
            # Call LLM (implementation depends on LLM provider interface)
            response = self.llm_provider.generate_structured(prompt, schema=ContradictionReport)

            # Convert to Contradiction objects
            contradictions = []
            for c in response.contradictions:
                contradictions.append(
                    Contradiction(
                        concept_a=c.get("concept_a", ""),
                        concept_b=c.get("concept_b", ""),
                        reason=c.get("reason", ""),
                        severity=c.get("severity", "warning"),
                        location="LLM-detected",
                    )
                )

            return contradictions

        except Exception as e:
            # If LLM check fails, just return empty list
            return []

    def generate_report(self, contradictions: List[Contradiction]) -> ContradictionReport:
        """
        Generate a formatted report of contradictions.

        Args:
            contradictions: List of contradictions

        Returns:
            Contradiction report
        """
        report_contradictions = []
        severity_counts = {"warning": 0, "error": 0, "critical": 0}

        for c in contradictions:
            report_contradictions.append(
                {
                    "concept_a": c.concept_a,
                    "concept_b": c.concept_b,
                    "reason": c.reason,
                    "severity": c.severity,
                    "location": c.location or "Unknown",
                }
            )

            severity_counts[c.severity] = severity_counts.get(c.severity, 0) + 1

        return ContradictionReport(
            contradictions=report_contradictions,
            has_contradictions=len(contradictions) > 0,
            severity_counts=severity_counts,
        )

    def print_report(self, contradictions: List[Contradiction], verbose: bool = True):
        """
        Print a human-readable report of contradictions.

        Args:
            contradictions: List of contradictions
            verbose: Whether to print detailed information
        """
        if not contradictions:
            print("\n✅ No semantic contradictions found!")
            return

        print("\n" + "=" * 70)
        print("⚠️  SEMANTIC CONSISTENCY REPORT")
        print("=" * 70)
        print(f"\nFound {len(contradictions)} contradiction(s):\n")

        for i, c in enumerate(contradictions, 1):
            severity_icon = {"warning": "⚠️ ", "error": "❌", "critical": "🔴"}.get(c.severity, "•")

            print(f"{i}. {severity_icon} {c.severity.upper()}")
            print(f"   Conflict: '{c.concept_a}' ↔ '{c.concept_b}'")
            print(f"   Reason: {c.reason}")

            if verbose and c.location:
                print(f"   Location: {c.location}")

            print()

        # Summary
        error_count = sum(1 for c in contradictions if c.severity == "error")
        warning_count = sum(1 for c in contradictions if c.severity == "warning")

        print("=" * 70)
        print(f"Summary: {error_count} errors, {warning_count} warnings")
        print("=" * 70 + "\n")


def validate_semantic_consistency(
    concretized: ConcretizedRequirement, llm_provider: Optional[Any] = None, verbose: bool = False
) -> tuple[bool, List[Contradiction]]:
    """
    Convenience function to validate semantic consistency.

    Args:
        concretized: The concretized requirement
        llm_provider: Optional LLM provider
        verbose: Whether to print report

    Returns:
        Tuple of (is_valid, contradictions)
    """
    checker = SemanticConsistencyChecker(llm_provider)
    contradictions = checker.check_consistency(concretized)

    if verbose:
        checker.print_report(contradictions)

    # Consider valid if no errors (warnings are OK)
    has_errors = any(c.severity == "error" for c in contradictions)
    is_valid = not has_errors

    return is_valid, contradictions
