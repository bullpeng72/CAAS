"""
Web Application Domain Ontology

Provides domain knowledge for web applications including
common concepts like User, Post, Comment, etc.
"""

from caas_framework.ontology.domain_ontology import (
    Concept,
    DesignPattern,
    DomainOntology,
    register_ontology,
)

# Define concepts
USER_CONCEPT = Concept(
    name="User",
    properties=["id", "email", "password", "username", "created_at", "updated_at"],
    relationships={
        "creates": ["Post", "Comment"],
        "has_many": ["Post", "Comment", "Like"],
        "belongs_to": ["Group", "Organization"],
    },
    typical_operations=[
        "register",
        "login",
        "logout",
        "update_profile",
        "delete_account",
    ],
    description="Represents a user in the system",
)

POST_CONCEPT = Concept(
    name="Post",
    properties=[
        "id",
        "title",
        "content",
        "created_at",
        "updated_at",
        "author_id",
        "published",
    ],
    relationships={"belongs_to": ["User"], "has_many": ["Comment", "Like", "Tag"]},
    typical_operations=["create", "read", "update", "delete", "publish", "unpublish"],
    description="Represents a blog post or article",
)

COMMENT_CONCEPT = Concept(
    name="Comment",
    properties=["id", "content", "created_at", "updated_at", "author_id", "post_id"],
    relationships={"belongs_to": ["User", "Post"]},
    typical_operations=["create", "read", "update", "delete", "approve", "flag"],
    description="Represents a comment on a post",
)

TAG_CONCEPT = Concept(
    name="Tag",
    properties=["id", "name", "slug", "created_at"],
    relationships={"belongs_to": ["Post"], "has_many": ["Post"]},
    typical_operations=["create", "read", "update", "delete", "search"],
    description="Represents a tag or category",
)

LIKE_CONCEPT = Concept(
    name="Like",
    properties=["id", "user_id", "post_id", "created_at"],
    relationships={"belongs_to": ["User", "Post"]},
    typical_operations=["create", "delete", "count"],
    description="Represents a like or favorite",
)

GROUP_CONCEPT = Concept(
    name="Group",
    properties=["id", "name", "description", "created_at", "owner_id"],
    relationships={"has_many": ["User", "Post"], "belongs_to": ["User"]},
    typical_operations=[
        "create",
        "read",
        "update",
        "delete",
        "add_member",
        "remove_member",
    ],
    description="Represents a user group or community",
)

ORGANIZATION_CONCEPT = Concept(
    name="Organization",
    properties=["id", "name", "description", "website", "created_at"],
    relationships={"has_many": ["User", "Group"]},
    typical_operations=["create", "read", "update", "delete", "add_member"],
    description="Represents an organization or company",
)

NOTIFICATION_CONCEPT = Concept(
    name="Notification",
    properties=["id", "user_id", "message", "read", "created_at", "type"],
    relationships={"belongs_to": ["User"]},
    typical_operations=["create", "read", "mark_as_read", "delete"],
    description="Represents a notification to a user",
)

# Define patterns
CRUD_WITH_AUTH_PATTERN = DesignPattern(
    name="CRUD_with_Auth",
    applies_to=["Post", "Comment", "Group"],
    required_components=[
        "authentication_middleware",
        "authorization_check",
        "database_model",
        "api_endpoints",
        "validation",
    ],
    description="Standard CRUD operations with authentication and authorization",
    benefits=["Secure access control", "Consistent API design", "Reusable auth logic"],
)

USER_MANAGEMENT_PATTERN = DesignPattern(
    name="User_Management",
    applies_to=["User"],
    required_components=[
        "password_hashing",
        "session_management",
        "email_verification",
        "password_reset",
        "profile_management",
    ],
    description="Complete user management system",
    benefits=["Secure authentication", "Standard user workflows", "Email integration"],
)

SOCIAL_FEATURES_PATTERN = DesignPattern(
    name="Social_Features",
    applies_to=["Post", "Comment", "Like"],
    required_components=[
        "like_system",
        "comment_system",
        "notification_system",
        "activity_feed",
    ],
    description="Social interaction features",
    benefits=["User engagement", "Community building", "Real-time updates"],
)

CONTENT_MODERATION_PATTERN = DesignPattern(
    name="Content_Moderation",
    applies_to=["Post", "Comment"],
    required_components=[
        "flag_system",
        "approval_workflow",
        "admin_dashboard",
        "content_filtering",
    ],
    description="Content moderation and safety features",
    benefits=["Safe community", "Spam prevention", "Quality control"],
)

# Create ontology
WEB_APP_ONTOLOGY = DomainOntology(
    domain_name="web_application",
    concepts={
        "User": USER_CONCEPT,
        "Post": POST_CONCEPT,
        "Comment": COMMENT_CONCEPT,
        "Tag": TAG_CONCEPT,
        "Like": LIKE_CONCEPT,
        "Group": GROUP_CONCEPT,
        "Organization": ORGANIZATION_CONCEPT,
        "Notification": NOTIFICATION_CONCEPT,
    },
    patterns=[
        CRUD_WITH_AUTH_PATTERN,
        USER_MANAGEMENT_PATTERN,
        SOCIAL_FEATURES_PATTERN,
        CONTENT_MODERATION_PATTERN,
    ],
    description="Domain ontology for web applications with social features",
)

# Register in global registry
register_ontology(WEB_APP_ONTOLOGY)
