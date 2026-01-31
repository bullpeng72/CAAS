"""
Tests for Domain Ontology

Tests the domain knowledge representation and reasoning capabilities.
"""

import pytest

from caas_framework.ontology.domain_ontology import (
    Concept,
    DesignPattern,
    DomainOntology,
    OntologyReasoner,
    OntologyRegistry,
    register_ontology,
    get_ontology,
    get_reasoner,
    list_available_domains
)

from caas_framework.ontology.web_app_ontology import WEB_APP_ONTOLOGY
from caas_framework.ontology.ecommerce_ontology import ECOMMERCE_ONTOLOGY
from caas_framework.ontology.api_ontology import API_ONTOLOGY


class TestConcept:
    """Test Concept class."""

    def test_concept_creation(self):
        """Test creating a concept."""
        concept = Concept(
            name="User",
            properties=["id", "email", "username"],
            relationships={"has_many": ["Post"]},
            typical_operations=["create", "read", "update", "delete"],
            description="User entity"
        )

        assert concept.name == "User"
        assert len(concept.properties) == 3
        assert "has_many" in concept.relationships
        assert len(concept.typical_operations) == 4

    def test_concept_has_relationship(self):
        """Test checking relationship."""
        concept = Concept(
            name="Post",
            relationships={"belongs_to": ["User"], "has_many": ["Comment"]}
        )

        assert concept.has_relationship("belongs_to", "User")
        assert not concept.has_relationship("belongs_to", "Comment")

    def test_concept_get_related_concepts(self):
        """Test getting related concepts."""
        concept = Concept(
            name="Post",
            relationships={"belongs_to": ["User"], "has_many": ["Comment", "Like"]}
        )

        # All relationships
        all_related = concept.get_related_concepts()
        assert set(all_related) == {"User", "Comment", "Like"}

        # Specific relationship
        belongs_to = concept.get_related_concepts("belongs_to")
        assert belongs_to == ["User"]


class TestDesignPattern:
    """Test DesignPattern class."""

    def test_pattern_creation(self):
        """Test creating a design pattern."""
        pattern = DesignPattern(
            name="CRUD",
            applies_to=["Post", "Comment"],
            required_components=["database", "api"],
            description="CRUD operations",
            benefits=["Standard interface"]
        )

        assert pattern.name == "CRUD"
        assert len(pattern.applies_to) == 2
        assert len(pattern.required_components) == 2

    def test_pattern_is_applicable_to(self):
        """Test checking pattern applicability."""
        pattern = DesignPattern(
            name="CRUD",
            applies_to=["Post", "Comment"]
        )

        assert pattern.is_applicable_to(["Post"])
        assert pattern.is_applicable_to(["Comment"])
        assert pattern.is_applicable_to(["Post", "User"])
        assert not pattern.is_applicable_to(["User", "Group"])


class TestDomainOntology:
    """Test DomainOntology class."""

    def test_ontology_creation(self):
        """Test creating an ontology."""
        user = Concept(name="User")
        post = Concept(name="Post")

        ontology = DomainOntology(
            domain_name="test",
            concepts={"User": user, "Post": post},
            description="Test ontology"
        )

        assert ontology.domain_name == "test"
        assert len(ontology.concepts) == 2

    def test_get_concept(self):
        """Test getting concept from ontology."""
        user = Concept(name="User")

        ontology = DomainOntology(
            domain_name="test",
            concepts={"User": user}
        )

        assert ontology.get_concept("User") == user
        assert ontology.get_concept("Nonexistent") is None

    def test_has_concept(self):
        """Test checking if concept exists."""
        ontology = DomainOntology(
            domain_name="test",
            concepts={"User": Concept(name="User")}
        )

        assert ontology.has_concept("User")
        assert not ontology.has_concept("Post")

    def test_get_all_concept_names(self):
        """Test getting all concept names."""
        ontology = DomainOntology(
            domain_name="test",
            concepts={
                "User": Concept(name="User"),
                "Post": Concept(name="Post")
            }
        )

        names = ontology.get_all_concept_names()
        assert set(names) == {"User", "Post"}

    def test_get_patterns_for_concepts(self):
        """Test getting applicable patterns."""
        pattern1 = DesignPattern(name="P1", applies_to=["Post"])
        pattern2 = DesignPattern(name="P2", applies_to=["User"])

        ontology = DomainOntology(
            domain_name="test",
            patterns=[pattern1, pattern2]
        )

        patterns = ontology.get_patterns_for_concepts(["Post"])
        assert len(patterns) == 1
        assert patterns[0].name == "P1"


class TestOntologyReasoner:
    """Test OntologyReasoner class."""

    @pytest.fixture
    def simple_ontology(self):
        """Create simple ontology for testing."""
        user = Concept(
            name="User",
            relationships={"creates": ["Post"]}
        )
        post = Concept(
            name="Post",
            relationships={"belongs_to": ["User"], "has_many": ["Comment"]}
        )
        comment = Concept(
            name="Comment",
            relationships={"belongs_to": ["User", "Post"]}
        )

        return DomainOntology(
            domain_name="test",
            concepts={"User": user, "Post": post, "Comment": comment}
        )

    def test_reasoner_creation(self, simple_ontology):
        """Test creating a reasoner."""
        reasoner = OntologyReasoner(simple_ontology)
        assert reasoner.ontology == simple_ontology

    def test_infer_missing_concepts(self, simple_ontology):
        """Test inferring missing concepts."""
        reasoner = OntologyReasoner(simple_ontology)

        # Mention only Post
        inferred = reasoner.infer_missing_concepts(["Post"])

        # Should infer User (Post belongs_to User)
        assert "User" in inferred

    def test_infer_missing_concepts_multiple(self, simple_ontology):
        """Test inferring from multiple concepts."""
        reasoner = OntologyReasoner(simple_ontology)

        # Mention Post and Comment
        inferred = reasoner.infer_missing_concepts(["Post", "Comment"])

        # Should infer User (both belong_to User)
        assert "User" in inferred

    def test_infer_no_missing(self, simple_ontology):
        """Test when no concepts are missing."""
        reasoner = OntologyReasoner(simple_ontology)

        # Mention all concepts
        inferred = reasoner.infer_missing_concepts(["User", "Post", "Comment"])

        # Should not infer anything new
        assert len(inferred) == 0

    def test_suggest_operations(self, simple_ontology):
        """Test suggesting operations."""
        # Add operations to User
        simple_ontology.concepts["User"].typical_operations = ["create", "read", "update", "delete"]

        reasoner = OntologyReasoner(simple_ontology)
        operations = reasoner.suggest_operations("User")

        assert len(operations) == 4
        assert "create" in operations

    def test_suggest_properties(self, simple_ontology):
        """Test suggesting properties."""
        # Add properties to User
        simple_ontology.concepts["User"].properties = ["id", "email", "username"]

        reasoner = OntologyReasoner(simple_ontology)
        properties = reasoner.suggest_properties("User")

        assert len(properties) == 3
        assert "email" in properties

    def test_apply_patterns(self, simple_ontology):
        """Test applying patterns."""
        pattern = DesignPattern(name="CRUD", applies_to=["Post"])
        simple_ontology.patterns.append(pattern)

        reasoner = OntologyReasoner(simple_ontology)
        patterns = reasoner.apply_patterns(["Post"])

        assert len(patterns) == 1
        assert patterns[0].name == "CRUD"

    def test_get_related_concepts(self, simple_ontology):
        """Test getting related concepts."""
        reasoner = OntologyReasoner(simple_ontology)

        related = reasoner.get_related_concepts("Post")
        assert "User" in related
        assert "Comment" in related

        # Specific relationship type
        belongs_to = reasoner.get_related_concepts("Post", "belongs_to")
        assert belongs_to == ["User"]

    def test_analyze_completeness(self, simple_ontology):
        """Test completeness analysis."""
        reasoner = OntologyReasoner(simple_ontology)

        analysis = reasoner.analyze_completeness(["Post"])

        assert "User" in analysis['missing_concepts']
        assert analysis['coverage'] < 1.0
        assert not analysis['is_complete']

    def test_suggest_enhancements(self, simple_ontology):
        """Test suggesting enhancements."""
        simple_ontology.concepts["Post"].typical_operations = ["create", "read"]

        reasoner = OntologyReasoner(simple_ontology)
        suggestions = reasoner.suggest_enhancements(["Post"])

        assert "User" in suggestions['missing_concepts']
        assert "Post" in suggestions['recommended_operations']


class TestOntologyRegistry:
    """Test OntologyRegistry class."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = OntologyRegistry()
        assert len(registry.list_domains()) == 0

    def test_register_ontology(self):
        """Test registering an ontology."""
        registry = OntologyRegistry()

        ontology = DomainOntology(domain_name="test")
        registry.register(ontology)

        assert registry.has_domain("test")
        assert len(registry.list_domains()) == 1

    def test_get_ontology(self):
        """Test getting ontology from registry."""
        registry = OntologyRegistry()

        ontology = DomainOntology(domain_name="test")
        registry.register(ontology)

        retrieved = registry.get("test")
        assert retrieved == ontology

    def test_get_reasoner(self):
        """Test getting reasoner from registry."""
        registry = OntologyRegistry()

        ontology = DomainOntology(domain_name="test")
        registry.register(ontology)

        reasoner = registry.get_reasoner("test")
        assert reasoner is not None
        assert reasoner.ontology == ontology

    def test_global_registry_functions(self):
        """Test global registry functions."""
        # These should work with the global registry
        domains = list_available_domains()
        assert isinstance(domains, list)

        # Web app ontology should be registered
        assert "web_application" in domains

        # Get web app ontology
        web_app = get_ontology("web_application")
        assert web_app is not None
        assert web_app.domain_name == "web_application"

        # Get reasoner
        reasoner = get_reasoner("web_application")
        assert reasoner is not None


class TestWebAppOntology:
    """Test Web Application ontology."""

    def test_web_app_ontology_exists(self):
        """Test that web app ontology is defined."""
        assert WEB_APP_ONTOLOGY is not None
        assert WEB_APP_ONTOLOGY.domain_name == "web_application"

    def test_web_app_concepts(self):
        """Test web app concepts."""
        assert WEB_APP_ONTOLOGY.has_concept("User")
        assert WEB_APP_ONTOLOGY.has_concept("Post")
        assert WEB_APP_ONTOLOGY.has_concept("Comment")

    def test_web_app_user_concept(self):
        """Test User concept details."""
        user = WEB_APP_ONTOLOGY.get_concept("User")

        assert "email" in user.properties
        assert "password" in user.properties
        assert "login" in user.typical_operations
        assert "Post" in user.relationships.get("creates", [])

    def test_web_app_patterns(self):
        """Test web app patterns."""
        assert len(WEB_APP_ONTOLOGY.patterns) > 0

        pattern_names = [p.name for p in WEB_APP_ONTOLOGY.patterns]
        assert "CRUD_with_Auth" in pattern_names

    def test_web_app_inference(self):
        """Test inference with web app ontology."""
        reasoner = OntologyReasoner(WEB_APP_ONTOLOGY)

        # Mention only Post and Comment
        inferred = reasoner.infer_missing_concepts(["Post", "Comment"])

        # Should infer User
        assert "User" in inferred


class TestEcommerceOntology:
    """Test E-commerce ontology."""

    def test_ecommerce_ontology_exists(self):
        """Test that e-commerce ontology is defined."""
        assert ECOMMERCE_ONTOLOGY is not None
        assert ECOMMERCE_ONTOLOGY.domain_name == "ecommerce"

    def test_ecommerce_concepts(self):
        """Test e-commerce concepts."""
        assert ECOMMERCE_ONTOLOGY.has_concept("Customer")
        assert ECOMMERCE_ONTOLOGY.has_concept("Product")
        assert ECOMMERCE_ONTOLOGY.has_concept("Order")
        assert ECOMMERCE_ONTOLOGY.has_concept("Cart")

    def test_ecommerce_product_concept(self):
        """Test Product concept details."""
        product = ECOMMERCE_ONTOLOGY.get_concept("Product")

        assert "price" in product.properties
        assert "stock" in product.properties
        assert "update_stock" in product.typical_operations

    def test_ecommerce_patterns(self):
        """Test e-commerce patterns."""
        pattern_names = [p.name for p in ECOMMERCE_ONTOLOGY.patterns]
        assert "Checkout_Flow" in pattern_names
        assert "Product_Catalog" in pattern_names

    def test_ecommerce_inference(self):
        """Test inference with e-commerce ontology."""
        reasoner = OntologyReasoner(ECOMMERCE_ONTOLOGY)

        # Mention only Order
        inferred = reasoner.infer_missing_concepts(["Order"])

        # Should infer Customer
        assert "Customer" in inferred


class TestAPIOntology:
    """Test API ontology."""

    def test_api_ontology_exists(self):
        """Test that API ontology is defined."""
        assert API_ONTOLOGY is not None
        assert API_ONTOLOGY.domain_name == "api"

    def test_api_concepts(self):
        """Test API concepts."""
        assert API_ONTOLOGY.has_concept("Resource")
        assert API_ONTOLOGY.has_concept("Endpoint")
        assert API_ONTOLOGY.has_concept("Authentication")

    def test_api_endpoint_concept(self):
        """Test Endpoint concept details."""
        endpoint = API_ONTOLOGY.get_concept("Endpoint")

        assert "path" in endpoint.properties
        assert "method" in endpoint.properties
        assert "Authentication" in endpoint.relationships.get("requires", [])

    def test_api_patterns(self):
        """Test API patterns."""
        pattern_names = [p.name for p in API_ONTOLOGY.patterns]
        assert "REST_CRUD" in pattern_names
        assert "JWT_Authentication" in pattern_names

    def test_api_inference(self):
        """Test inference with API ontology."""
        reasoner = OntologyReasoner(API_ONTOLOGY)

        # Mention only Endpoint
        inferred = reasoner.infer_missing_concepts(["Endpoint"])

        # Should infer required concepts
        assert "Authentication" in inferred or "Validation" in inferred


class TestIntegration:
    """Integration tests."""

    def test_full_workflow_web_app(self):
        """Test complete workflow with web app ontology."""
        reasoner = OntologyReasoner(WEB_APP_ONTOLOGY)

        # User mentions they need Post and Comment
        mentioned = ["Post", "Comment"]

        # Infer missing concepts
        missing = reasoner.infer_missing_concepts(mentioned)
        assert "User" in missing

        # Get operations for Post
        operations = reasoner.suggest_operations("Post")
        assert "create" in operations
        assert "publish" in operations

        # Find applicable patterns
        patterns = reasoner.apply_patterns(mentioned)
        assert len(patterns) > 0

    def test_full_workflow_ecommerce(self):
        """Test complete workflow with e-commerce ontology."""
        reasoner = OntologyReasoner(ECOMMERCE_ONTOLOGY)

        # User building shopping cart
        mentioned = ["Cart", "Product"]

        # Infer missing concepts
        missing = reasoner.infer_missing_concepts(mentioned)

        # Analyze completeness
        analysis = reasoner.analyze_completeness(mentioned)
        assert len(analysis['missing_concepts']) > 0
        assert 'Customer' in analysis['all_required_concepts']

        # Get suggestions
        suggestions = reasoner.suggest_enhancements(mentioned)
        assert len(suggestions['missing_concepts']) > 0

    def test_cross_domain_comparison(self):
        """Test that different domains have different concepts."""
        web_app_concepts = set(WEB_APP_ONTOLOGY.get_all_concept_names())
        ecommerce_concepts = set(ECOMMERCE_ONTOLOGY.get_all_concept_names())
        api_concepts = set(API_ONTOLOGY.get_all_concept_names())

        # Should be different domains
        assert "Post" in web_app_concepts
        assert "Post" not in ecommerce_concepts

        assert "Product" in ecommerce_concepts
        assert "Product" not in api_concepts

        assert "Endpoint" in api_concepts
        assert "Endpoint" not in web_app_concepts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
