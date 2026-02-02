"""
Domain Ontology for CaaS Framework

Provides domain knowledge representation and reasoning capabilities
for intelligent concept inference and pattern application.
"""

from caas_framework.ontology.api_ontology import API_ONTOLOGY
from caas_framework.ontology.domain_ontology import (
    Concept,
    DesignPattern,
    DomainOntology,
    OntologyReasoner,
)
from caas_framework.ontology.ecommerce_ontology import ECOMMERCE_ONTOLOGY
from caas_framework.ontology.web_app_ontology import WEB_APP_ONTOLOGY

__all__ = [
    "Concept",
    "DesignPattern",
    "DomainOntology",
    "OntologyReasoner",
    "WEB_APP_ONTOLOGY",
    "ECOMMERCE_ONTOLOGY",
    "API_ONTOLOGY",
]
