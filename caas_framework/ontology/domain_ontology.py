"""
Domain Ontology Core Classes

Provides structured domain knowledge representation and reasoning
for intelligent concept inference and pattern application.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Concept:
    """
    Represents a domain concept with properties and relationships.

    Examples: User, Post, Comment, Product, Order, etc.
    """
    name: str
    properties: List[str] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    typical_operations: List[str] = field(default_factory=list)
    description: Optional[str] = None

    def has_relationship(self, relation_type: str, target: str) -> bool:
        """Check if concept has specific relationship to target."""
        return target in self.relationships.get(relation_type, [])

    def get_related_concepts(self, relation_type: Optional[str] = None) -> List[str]:
        """Get all related concepts, optionally filtered by relationship type."""
        if relation_type:
            return self.relationships.get(relation_type, [])

        # Return all related concepts
        all_related = []
        for concepts in self.relationships.values():
            all_related.extend(concepts)
        return list(set(all_related))


@dataclass
class DesignPattern:
    """
    Represents a design pattern applicable to certain concepts.

    Examples: CRUD_with_Auth, Shopping_Cart, Payment_Flow, etc.
    """
    name: str
    applies_to: List[str]  # Concept names this pattern applies to
    required_components: List[str] = field(default_factory=list)
    description: Optional[str] = None
    benefits: List[str] = field(default_factory=list)

    def is_applicable_to(self, concepts: List[str]) -> bool:
        """Check if pattern is applicable to given concepts."""
        return any(concept in self.applies_to for concept in concepts)


@dataclass
class DomainOntology:
    """
    Represents a domain ontology with concepts and patterns.

    Provides structured domain knowledge for a specific domain
    (e.g., web apps, e-commerce, APIs).
    """
    domain_name: str
    concepts: Dict[str, Concept] = field(default_factory=dict)
    patterns: List[DesignPattern] = field(default_factory=list)
    description: Optional[str] = None

    def get_concept(self, name: str) -> Optional[Concept]:
        """Get concept by name."""
        return self.concepts.get(name)

    def has_concept(self, name: str) -> bool:
        """Check if ontology contains concept."""
        return name in self.concepts

    def get_all_concept_names(self) -> List[str]:
        """Get all concept names in ontology."""
        return list(self.concepts.keys())

    def get_patterns_for_concepts(self, concepts: List[str]) -> List[DesignPattern]:
        """Get applicable patterns for given concepts."""
        return [p for p in self.patterns if p.is_applicable_to(concepts)]


class OntologyReasoner:
    """
    Performs reasoning over domain ontology to infer missing concepts,
    suggest operations, and apply patterns.
    """

    def __init__(self, ontology: DomainOntology):
        """
        Initialize ontology reasoner.

        Args:
            ontology: The domain ontology to reason over
        """
        self.ontology = ontology

    def infer_missing_concepts(
        self,
        mentioned_concepts: List[str],
        max_depth: int = 2
    ) -> List[str]:
        """
        Infer concepts that are likely needed based on mentioned concepts.

        Uses relationship traversal to find related concepts that should
        probably be included.

        Args:
            mentioned_concepts: Concepts explicitly mentioned by user
            max_depth: Maximum relationship traversal depth

        Returns:
            List of inferred concept names (excluding already mentioned)
        """
        inferred = set()
        visited = set(mentioned_concepts)

        # Queue for BFS traversal: (concept_name, depth)
        queue = [(name, 0) for name in mentioned_concepts]

        while queue:
            concept_name, depth = queue.pop(0)

            if depth >= max_depth:
                continue

            concept = self.ontology.get_concept(concept_name)
            if not concept:
                continue

            # Traverse important relationships
            for relation, targets in concept.relationships.items():
                # belongs_to and requires relationships are most important
                if relation in ["belongs_to", "requires", "depends_on"]:
                    for target in targets:
                        if target not in visited:
                            inferred.add(target)
                            visited.add(target)
                            queue.append((target, depth + 1))

                # has_many relationships at depth 0 are also important
                elif relation == "has_many" and depth == 0:
                    for target in targets:
                        if target not in visited:
                            # Don't add to inferred automatically, but mark as visited
                            visited.add(target)

        # Return inferred concepts (excluding originally mentioned)
        return list(inferred - set(mentioned_concepts))

    def suggest_operations(
        self,
        concept_name: str
    ) -> List[str]:
        """
        Suggest typical operations for a concept.

        Args:
            concept_name: Name of the concept

        Returns:
            List of typical operation names
        """
        concept = self.ontology.get_concept(concept_name)
        if not concept:
            return []

        return concept.typical_operations.copy()

    def suggest_properties(
        self,
        concept_name: str
    ) -> List[str]:
        """
        Suggest typical properties for a concept.

        Args:
            concept_name: Name of the concept

        Returns:
            List of typical property names
        """
        concept = self.ontology.get_concept(concept_name)
        if not concept:
            return []

        return concept.properties.copy()

    def apply_patterns(
        self,
        concepts: List[str]
    ) -> List[DesignPattern]:
        """
        Find design patterns applicable to given concepts.

        Args:
            concepts: List of concept names

        Returns:
            List of applicable design patterns
        """
        return self.ontology.get_patterns_for_concepts(concepts)

    def get_related_concepts(
        self,
        concept_name: str,
        relation_type: Optional[str] = None
    ) -> List[str]:
        """
        Get concepts related to given concept.

        Args:
            concept_name: Name of the concept
            relation_type: Optional relationship type filter

        Returns:
            List of related concept names
        """
        concept = self.ontology.get_concept(concept_name)
        if not concept:
            return []

        return concept.get_related_concepts(relation_type)

    def analyze_completeness(
        self,
        mentioned_concepts: List[str]
    ) -> Dict[str, any]:
        """
        Analyze completeness of concept set.

        Args:
            mentioned_concepts: Concepts mentioned by user

        Returns:
            Dictionary with completeness analysis
        """
        missing = self.infer_missing_concepts(mentioned_concepts)
        applicable_patterns = self.apply_patterns(mentioned_concepts)

        # Check if key concepts are present
        all_concepts = set(mentioned_concepts + missing)
        coverage = len(mentioned_concepts) / len(all_concepts) if all_concepts else 1.0

        return {
            'mentioned_concepts': mentioned_concepts,
            'missing_concepts': missing,
            'all_required_concepts': list(all_concepts),
            'coverage': coverage,
            'coverage_percent': coverage * 100,
            'applicable_patterns': [p.name for p in applicable_patterns],
            'is_complete': len(missing) == 0
        }

    def suggest_enhancements(
        self,
        mentioned_concepts: List[str]
    ) -> Dict[str, List[str]]:
        """
        Suggest enhancements for concept set.

        Args:
            mentioned_concepts: Concepts mentioned by user

        Returns:
            Dictionary with suggested enhancements
        """
        suggestions = {
            'missing_concepts': [],
            'recommended_operations': {},
            'applicable_patterns': [],
            'related_concepts': {}
        }

        # Find missing concepts
        suggestions['missing_concepts'] = self.infer_missing_concepts(mentioned_concepts)

        # Suggest operations for each concept
        for concept_name in mentioned_concepts:
            operations = self.suggest_operations(concept_name)
            if operations:
                suggestions['recommended_operations'][concept_name] = operations

        # Find applicable patterns
        patterns = self.apply_patterns(mentioned_concepts)
        suggestions['applicable_patterns'] = [p.name for p in patterns]

        # Find related concepts
        for concept_name in mentioned_concepts:
            related = self.get_related_concepts(concept_name)
            if related:
                suggestions['related_concepts'][concept_name] = related

        return suggestions


class OntologyRegistry:
    """
    Registry for managing multiple domain ontologies.
    """

    def __init__(self):
        self._ontologies: Dict[str, DomainOntology] = {}

    def register(self, ontology: DomainOntology):
        """Register an ontology."""
        self._ontologies[ontology.domain_name] = ontology

    def get(self, domain_name: str) -> Optional[DomainOntology]:
        """Get ontology by domain name."""
        return self._ontologies.get(domain_name)

    def list_domains(self) -> List[str]:
        """List all registered domain names."""
        return list(self._ontologies.keys())

    def has_domain(self, domain_name: str) -> bool:
        """Check if domain is registered."""
        return domain_name in self._ontologies

    def get_reasoner(self, domain_name: str) -> Optional[OntologyReasoner]:
        """Get reasoner for domain."""
        ontology = self.get(domain_name)
        if ontology:
            return OntologyReasoner(ontology)
        return None


# Global registry
_global_registry = OntologyRegistry()


def register_ontology(ontology: DomainOntology):
    """Register ontology in global registry."""
    _global_registry.register(ontology)


def get_ontology(domain_name: str) -> Optional[DomainOntology]:
    """Get ontology from global registry."""
    return _global_registry.get(domain_name)


def get_reasoner(domain_name: str) -> Optional[OntologyReasoner]:
    """Get reasoner from global registry."""
    return _global_registry.get_reasoner(domain_name)


def list_available_domains() -> List[str]:
    """List all available domains."""
    return _global_registry.list_domains()
