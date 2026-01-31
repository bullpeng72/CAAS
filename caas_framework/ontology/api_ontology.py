"""
API Domain Ontology

Provides domain knowledge for REST API applications including
concepts like Endpoint, Resource, Authentication, etc.
"""

from caas_framework.ontology.domain_ontology import (
    Concept,
    DesignPattern,
    DomainOntology,
    register_ontology
)


# Define concepts
RESOURCE_CONCEPT = Concept(
    name="Resource",
    properties=["id", "type", "attributes", "created_at", "updated_at"],
    relationships={
        "has_many": ["Endpoint"],
        "requires": ["Schema", "Validation"]
    },
    typical_operations=["create", "read", "update", "delete", "list", "search"],
    description="Represents a REST API resource"
)

ENDPOINT_CONCEPT = Concept(
    name="Endpoint",
    properties=["path", "method", "parameters", "response_schema", "status_codes"],
    relationships={
        "belongs_to": ["Resource"],
        "requires": ["Authentication", "Validation"],
        "has_one": ["RateLimit"]
    },
    typical_operations=["define", "implement", "test", "document"],
    description="Represents an API endpoint"
)

AUTHENTICATION_CONCEPT = Concept(
    name="Authentication",
    properties=["type", "token", "expiry", "refresh_token"],
    relationships={
        "required_by": ["Endpoint"],
        "has_one": ["User"]
    },
    typical_operations=["login", "logout", "refresh", "validate"],
    description="Represents authentication mechanism"
)

AUTHORIZATION_CONCEPT = Concept(
    name="Authorization",
    properties=["permissions", "roles", "policies"],
    relationships={
        "required_by": ["Endpoint"],
        "belongs_to": ["User"]
    },
    typical_operations=["check_permission", "grant", "revoke"],
    description="Represents authorization and access control"
)

SCHEMA_CONCEPT = Concept(
    name="Schema",
    properties=["fields", "validation_rules", "format"],
    relationships={
        "belongs_to": ["Resource", "Endpoint"],
        "requires": ["Validation"]
    },
    typical_operations=["define", "validate", "serialize", "deserialize"],
    description="Represents data schema for validation"
)

VALIDATION_CONCEPT = Concept(
    name="Validation",
    properties=["rules", "error_messages", "sanitization"],
    relationships={
        "belongs_to": ["Schema", "Endpoint"]
    },
    typical_operations=["validate", "sanitize", "format_errors"],
    description="Represents input validation"
)

RATE_LIMIT_CONCEPT = Concept(
    name="RateLimit",
    properties=["max_requests", "window", "strategy"],
    relationships={
        "belongs_to": ["Endpoint", "User"]
    },
    typical_operations=["check", "increment", "reset"],
    description="Represents API rate limiting"
)

ERROR_HANDLING_CONCEPT = Concept(
    name="ErrorHandling",
    properties=["error_codes", "messages", "status_codes"],
    relationships={
        "belongs_to": ["Endpoint"]
    },
    typical_operations=["handle", "log", "format", "respond"],
    description="Represents error handling mechanism"
)

DOCUMENTATION_CONCEPT = Concept(
    name="Documentation",
    properties=["description", "examples", "schema", "format"],
    relationships={
        "belongs_to": ["Endpoint", "Resource"],
        "requires": ["Schema"]
    },
    typical_operations=["generate", "update", "publish"],
    description="Represents API documentation"
)

VERSIONING_CONCEPT = Concept(
    name="Versioning",
    properties=["version", "strategy", "deprecated_endpoints"],
    relationships={
        "belongs_to": ["Endpoint", "Resource"]
    },
    typical_operations=["version", "deprecate", "migrate"],
    description="Represents API versioning"
)

# Define patterns
REST_CRUD_PATTERN = DesignPattern(
    name="REST_CRUD",
    applies_to=["Resource", "Endpoint"],
    required_components=[
        "get_endpoint",
        "post_endpoint",
        "put_endpoint",
        "delete_endpoint",
        "list_endpoint",
        "validation"
    ],
    description="Standard REST CRUD operations",
    benefits=[
        "Standard HTTP methods",
        "RESTful design",
        "Predictable API structure"
    ]
)

JWT_AUTH_PATTERN = DesignPattern(
    name="JWT_Authentication",
    applies_to=["Authentication", "Endpoint"],
    required_components=[
        "jwt_generation",
        "jwt_validation",
        "refresh_token_flow",
        "blacklist_mechanism",
        "middleware"
    ],
    description="JWT-based authentication",
    benefits=[
        "Stateless authentication",
        "Secure token exchange",
        "Easy to scale"
    ]
)

API_SECURITY_PATTERN = DesignPattern(
    name="API_Security",
    applies_to=["Endpoint", "Authentication", "Authorization"],
    required_components=[
        "authentication",
        "authorization",
        "rate_limiting",
        "input_validation",
        "cors_configuration",
        "https_enforcement"
    ],
    description="Comprehensive API security",
    benefits=[
        "Protected endpoints",
        "Rate limit abuse",
        "Data validation"
    ]
)

API_DOCUMENTATION_PATTERN = DesignPattern(
    name="API_Documentation",
    applies_to=["Documentation", "Endpoint", "Schema"],
    required_components=[
        "openapi_spec",
        "swagger_ui",
        "example_requests",
        "example_responses",
        "error_documentation"
    ],
    description="Complete API documentation",
    benefits=[
        "Self-documenting API",
        "Interactive testing",
        "Developer friendly"
    ]
)

PAGINATION_PATTERN = DesignPattern(
    name="Pagination",
    applies_to=["Endpoint", "Resource"],
    required_components=[
        "page_parameter",
        "limit_parameter",
        "total_count",
        "next_page_link",
        "previous_page_link"
    ],
    description="API response pagination",
    benefits=[
        "Efficient data transfer",
        "Better performance",
        "Scalable responses"
    ]
)

ERROR_RESPONSE_PATTERN = DesignPattern(
    name="Error_Response",
    applies_to=["ErrorHandling", "Endpoint"],
    required_components=[
        "error_code",
        "error_message",
        "error_details",
        "timestamp",
        "request_id"
    ],
    description="Standardized error responses",
    benefits=[
        "Consistent error format",
        "Easy debugging",
        "Client-friendly errors"
    ]
)

# Create ontology
API_ONTOLOGY = DomainOntology(
    domain_name="api",
    concepts={
        "Resource": RESOURCE_CONCEPT,
        "Endpoint": ENDPOINT_CONCEPT,
        "Authentication": AUTHENTICATION_CONCEPT,
        "Authorization": AUTHORIZATION_CONCEPT,
        "Schema": SCHEMA_CONCEPT,
        "Validation": VALIDATION_CONCEPT,
        "RateLimit": RATE_LIMIT_CONCEPT,
        "ErrorHandling": ERROR_HANDLING_CONCEPT,
        "Documentation": DOCUMENTATION_CONCEPT,
        "Versioning": VERSIONING_CONCEPT
    },
    patterns=[
        REST_CRUD_PATTERN,
        JWT_AUTH_PATTERN,
        API_SECURITY_PATTERN,
        API_DOCUMENTATION_PATTERN,
        PAGINATION_PATTERN,
        ERROR_RESPONSE_PATTERN
    ],
    description="Domain ontology for REST API applications"
)

# Register in global registry
register_ontology(API_ONTOLOGY)
