"""
E-Commerce Domain Ontology

Provides domain knowledge for e-commerce applications including
concepts like Product, Order, Cart, Payment, etc.
"""

from caas_framework.ontology.domain_ontology import (
    Concept,
    DesignPattern,
    DomainOntology,
    register_ontology,
)

# Define concepts
CUSTOMER_CONCEPT = Concept(
    name="Customer",
    properties=["id", "email", "password", "name", "phone", "address", "created_at"],
    relationships={
        "creates": ["Order", "Review"],
        "has_many": ["Order", "Review", "WishlistItem"],
        "has_one": ["Cart"],
    },
    typical_operations=[
        "register",
        "login",
        "update_profile",
        "view_orders",
        "add_to_wishlist",
    ],
    description="Represents a customer in the e-commerce system",
)

PRODUCT_CONCEPT = Concept(
    name="Product",
    properties=[
        "id",
        "name",
        "description",
        "price",
        "stock",
        "sku",
        "category_id",
        "created_at",
    ],
    relationships={
        "belongs_to": ["Category", "Vendor"],
        "has_many": ["Review", "CartItem", "OrderItem", "Image"],
    },
    typical_operations=[
        "create",
        "read",
        "update",
        "delete",
        "search",
        "filter",
        "update_stock",
    ],
    description="Represents a product for sale",
)

CATEGORY_CONCEPT = Concept(
    name="Category",
    properties=["id", "name", "description", "parent_id", "slug"],
    relationships={"has_many": ["Product", "Category"], "belongs_to": ["Category"]},
    typical_operations=["create", "read", "update", "delete", "list_products"],
    description="Represents a product category",
)

CART_CONCEPT = Concept(
    name="Cart",
    properties=["id", "customer_id", "created_at", "updated_at"],
    relationships={"belongs_to": ["Customer"], "has_many": ["CartItem"]},
    typical_operations=[
        "add_item",
        "remove_item",
        "update_quantity",
        "clear",
        "calculate_total",
        "checkout",
    ],
    description="Represents a shopping cart",
)

CART_ITEM_CONCEPT = Concept(
    name="CartItem",
    properties=["id", "cart_id", "product_id", "quantity", "price"],
    relationships={"belongs_to": ["Cart", "Product"]},
    typical_operations=["create", "update", "delete"],
    description="Represents an item in a shopping cart",
)

ORDER_CONCEPT = Concept(
    name="Order",
    properties=[
        "id",
        "customer_id",
        "total",
        "status",
        "shipping_address",
        "created_at",
        "updated_at",
    ],
    relationships={
        "belongs_to": ["Customer"],
        "has_many": ["OrderItem", "Payment"],
        "has_one": ["Shipment"],
    },
    typical_operations=["create", "read", "update", "cancel", "track", "refund"],
    description="Represents a customer order",
)

ORDER_ITEM_CONCEPT = Concept(
    name="OrderItem",
    properties=["id", "order_id", "product_id", "quantity", "price", "subtotal"],
    relationships={"belongs_to": ["Order", "Product"]},
    typical_operations=["create", "read"],
    description="Represents an item in an order",
)

PAYMENT_CONCEPT = Concept(
    name="Payment",
    properties=[
        "id",
        "order_id",
        "amount",
        "method",
        "status",
        "transaction_id",
        "created_at",
    ],
    relationships={"belongs_to": ["Order"]},
    typical_operations=["create", "process", "refund", "verify"],
    description="Represents a payment transaction",
)

SHIPMENT_CONCEPT = Concept(
    name="Shipment",
    properties=[
        "id",
        "order_id",
        "tracking_number",
        "carrier",
        "status",
        "shipped_at",
        "delivered_at",
    ],
    relationships={"belongs_to": ["Order"]},
    typical_operations=["create", "update_status", "track"],
    description="Represents a shipment",
)

REVIEW_CONCEPT = Concept(
    name="Review",
    properties=["id", "product_id", "customer_id", "rating", "comment", "created_at"],
    relationships={"belongs_to": ["Product", "Customer"]},
    typical_operations=["create", "read", "update", "delete", "approve"],
    description="Represents a product review",
)

VENDOR_CONCEPT = Concept(
    name="Vendor",
    properties=["id", "name", "email", "phone", "commission_rate", "created_at"],
    relationships={"has_many": ["Product"]},
    typical_operations=["create", "read", "update", "delete", "view_sales"],
    description="Represents a vendor or seller",
)

# Define patterns
CHECKOUT_FLOW_PATTERN = DesignPattern(
    name="Checkout_Flow",
    applies_to=["Cart", "Order", "Payment"],
    required_components=[
        "cart_validation",
        "address_collection",
        "payment_processing",
        "order_confirmation",
        "inventory_reservation",
    ],
    description="Complete checkout workflow from cart to order",
    benefits=["Smooth customer experience", "Payment security", "Inventory management"],
)

PRODUCT_CATALOG_PATTERN = DesignPattern(
    name="Product_Catalog",
    applies_to=["Product", "Category"],
    required_components=[
        "search_functionality",
        "filtering_system",
        "category_navigation",
        "product_details_page",
        "image_gallery",
    ],
    description="Product browsing and discovery features",
    benefits=["Easy product discovery", "Rich product information", "SEO friendly"],
)

ORDER_MANAGEMENT_PATTERN = DesignPattern(
    name="Order_Management",
    applies_to=["Order", "OrderItem", "Shipment"],
    required_components=[
        "order_tracking",
        "status_updates",
        "email_notifications",
        "admin_dashboard",
        "fulfillment_integration",
    ],
    description="Order lifecycle management",
    benefits=["Order visibility", "Customer updates", "Efficient fulfillment"],
)

PAYMENT_PROCESSING_PATTERN = DesignPattern(
    name="Payment_Processing",
    applies_to=["Payment"],
    required_components=[
        "payment_gateway_integration",
        "pci_compliance",
        "fraud_detection",
        "refund_system",
        "payment_verification",
    ],
    description="Secure payment processing",
    benefits=["Payment security", "Multiple payment methods", "Fraud prevention"],
)

MARKETPLACE_PATTERN = DesignPattern(
    name="Marketplace",
    applies_to=["Vendor", "Product", "Order"],
    required_components=[
        "vendor_dashboard",
        "commission_calculation",
        "payout_system",
        "vendor_reviews",
        "multi_vendor_search",
    ],
    description="Multi-vendor marketplace features",
    benefits=["Vendor management", "Commission tracking", "Marketplace scalability"],
)

# Create ontology
ECOMMERCE_ONTOLOGY = DomainOntology(
    domain_name="ecommerce",
    concepts={
        "Customer": CUSTOMER_CONCEPT,
        "Product": PRODUCT_CONCEPT,
        "Category": CATEGORY_CONCEPT,
        "Cart": CART_CONCEPT,
        "CartItem": CART_ITEM_CONCEPT,
        "Order": ORDER_CONCEPT,
        "OrderItem": ORDER_ITEM_CONCEPT,
        "Payment": PAYMENT_CONCEPT,
        "Shipment": SHIPMENT_CONCEPT,
        "Review": REVIEW_CONCEPT,
        "Vendor": VENDOR_CONCEPT,
    },
    patterns=[
        CHECKOUT_FLOW_PATTERN,
        PRODUCT_CATALOG_PATTERN,
        ORDER_MANAGEMENT_PATTERN,
        PAYMENT_PROCESSING_PATTERN,
        MARKETPLACE_PATTERN,
    ],
    description="Domain ontology for e-commerce applications",
)

# Register in global registry
register_ontology(ECOMMERCE_ONTOLOGY)
