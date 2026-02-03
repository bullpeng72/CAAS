"""
Requirement Examples

A collection of example requirements to guide users in writing better project specifications.
Organized by domain, complexity, and use case.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class Domain(str, Enum):
    """Domain categories"""

    WEB_APP = "web_app"
    API = "api"
    DATA_ANALYSIS = "data_analysis"
    AUTOMATION = "automation"
    CHATBOT = "chatbot"
    CONTENT_MANAGEMENT = "content_management"
    E_COMMERCE = "e_commerce"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    GENERAL = "general"


class Complexity(str, Enum):
    """Complexity levels"""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class RequirementExample:
    """Example requirement specification"""

    title: str
    domain: Domain
    complexity: Complexity
    description: str
    requirement_text: str
    key_features: List[str]
    tags: List[str]

    def format_for_display(self) -> str:
        """Format example for display"""
        return f"""
# {self.title}

**Domain**: {self.domain.value}
**Complexity**: {self.complexity.value}

## Description
{self.description}

## Example Requirement
```
{self.requirement_text}
```

## Key Features
{chr(10).join(f"- {feature}" for feature in self.key_features)}

## Tags
{', '.join(self.tags)}
"""


# ============================================================================
# Example Requirements Database
# ============================================================================

REQUIREMENT_EXAMPLES = [
    # ========== Simple Examples ==========
    RequirementExample(
        title="Simple To-Do List Application",
        domain=Domain.WEB_APP,
        complexity=Complexity.SIMPLE,
        description="A basic task management application for personal use",
        requirement_text="""Build a simple to-do list web application where users can:
- Create new tasks with a title and description
- Mark tasks as complete or incomplete
- Delete tasks
- View all tasks in a list
- Filter tasks by status (all, active, completed)

The app should have a clean, minimal interface and persist data locally in the browser.""",
        key_features=[
            "Task CRUD operations",
            "Status filtering",
            "Local storage persistence",
            "Minimal UI",
        ],
        tags=["todo", "task-management", "simple", "beginner"],
    ),
    RequirementExample(
        title="Weather Information Bot",
        domain=Domain.CHATBOT,
        complexity=Complexity.SIMPLE,
        description="A chatbot that provides weather information",
        requirement_text="""Create a chatbot that can:
- Accept a city name as input
- Fetch current weather data from a weather API
- Display temperature, humidity, and weather conditions
- Provide a 3-day forecast
- Handle common variations in city names
- Give friendly error messages for invalid inputs

The bot should respond conversationally and be easy to use.""",
        key_features=[
            "Weather API integration",
            "Current conditions",
            "3-day forecast",
            "Error handling",
        ],
        tags=["chatbot", "weather", "api-integration", "simple"],
    ),
    RequirementExample(
        title="Basic REST API for Blog",
        domain=Domain.API,
        complexity=Complexity.SIMPLE,
        description="A REST API for managing blog posts",
        requirement_text="""Develop a REST API for a blog with these endpoints:

Posts:
- GET /posts - List all posts
- GET /posts/:id - Get a specific post
- POST /posts - Create a new post (title, content, author)
- PUT /posts/:id - Update a post
- DELETE /posts/:id - Delete a post

Comments:
- GET /posts/:id/comments - Get comments for a post
- POST /posts/:id/comments - Add a comment

Include basic validation and return appropriate HTTP status codes.""",
        key_features=[
            "CRUD operations for posts",
            "Comments functionality",
            "RESTful design",
            "Input validation",
        ],
        tags=["api", "rest", "blog", "crud"],
    ),
    # ========== Moderate Examples ==========
    RequirementExample(
        title="Customer Support Ticket System",
        domain=Domain.WEB_APP,
        complexity=Complexity.MODERATE,
        description="A multi-user ticket management system",
        requirement_text="""Build a customer support ticket system with the following features:

User Roles:
- Customers: Can create and view their own tickets
- Support Agents: Can view all tickets, update status, add comments
- Admins: Full access including user management

Ticket Management:
- Create tickets with title, description, priority (low/medium/high)
- Assign tickets to support agents
- Update ticket status (new, in progress, resolved, closed)
- Add comments/replies to tickets
- File attachments for tickets
- Email notifications on status changes

Dashboard:
- Display ticket statistics (total, by status, by priority)
- Filter and search tickets
- Sort by date, priority, or status

The system should have a clean UI and support real-time updates.""",
        key_features=[
            "Multi-user roles and permissions",
            "Ticket lifecycle management",
            "Comments and attachments",
            "Email notifications",
            "Dashboard with analytics",
            "Real-time updates",
        ],
        tags=["support", "tickets", "multi-user", "moderate"],
    ),
    RequirementExample(
        title="E-Commerce Product Catalog",
        domain=Domain.E_COMMERCE,
        complexity=Complexity.MODERATE,
        description="An online product catalog with shopping cart",
        requirement_text="""Create an e-commerce product catalog system with:

Product Management:
- Display products with images, name, price, description
- Categories and subcategories
- Product variants (size, color)
- Inventory tracking
- Product search and filtering
- Sort by price, popularity, newest

Shopping Cart:
- Add/remove products
- Update quantities
- Calculate totals with taxes
- Apply discount codes
- Persist cart across sessions

User Features:
- User registration and login
- Order history
- Wishlist/favorites
- Product reviews and ratings

Checkout:
- Multi-step checkout process
- Shipping address management
- Payment gateway integration (Stripe)
- Order confirmation emails""",
        key_features=[
            "Product catalog with variants",
            "Shopping cart functionality",
            "User accounts",
            "Order management",
            "Payment integration",
            "Reviews and ratings",
        ],
        tags=["e-commerce", "shopping", "payments", "moderate"],
    ),
    RequirementExample(
        title="Data Analysis Dashboard",
        domain=Domain.DATA_ANALYSIS,
        complexity=Complexity.MODERATE,
        description="An interactive data visualization dashboard",
        requirement_text="""Build a data analysis dashboard that:

Data Input:
- Upload CSV files
- Connect to database (PostgreSQL)
- Fetch data from REST APIs
- Support multiple data sources

Analysis Features:
- Automatic data type detection
- Basic statistics (mean, median, mode, etc.)
- Missing value analysis
- Correlation matrix
- Time series analysis

Visualizations:
- Line charts for trends
- Bar charts for comparisons
- Pie charts for distributions
- Scatter plots for relationships
- Heatmaps for correlations
- Interactive filtering and drill-down

Export:
- Download charts as PNG/SVG
- Export analysis results as PDF report
- Export processed data as CSV

The dashboard should be responsive and handle datasets up to 100,000 rows.""",
        key_features=[
            "Multiple data sources",
            "Automated analysis",
            "Interactive visualizations",
            "Export capabilities",
            "Performance optimization",
        ],
        tags=["data-analysis", "dashboard", "visualization", "moderate"],
    ),
    # ========== Complex Examples ==========
    RequirementExample(
        title="Financial Trading Platform",
        domain=Domain.FINANCE,
        complexity=Complexity.COMPLEX,
        description="A comprehensive stock trading platform",
        requirement_text="""Develop a financial trading platform with these capabilities:

Market Data:
- Real-time stock prices via WebSocket
- Historical price data (OHLCV)
- Technical indicators (RSI, MACD, Bollinger Bands)
- Market news feed integration
- Watchlists and alerts

Trading Features:
- Market orders and limit orders
- Stop-loss and take-profit orders
- Portfolio management
- Order history and tracking
- Real-time P&L calculation
- Risk management (position sizing, margin requirements)

Analytics:
- Portfolio performance metrics
- Risk analysis (VaR, Sharpe ratio)
- Backtesting historical strategies
- Custom indicator creation
- Trade analytics and reporting

Security & Compliance:
- Two-factor authentication
- Encrypted data transmission
- Audit logging
- Regulatory compliance (KYC/AML)
- Transaction verification

System Requirements:
- High availability (99.9% uptime)
- Low latency (<100ms for orders)
- Scalable to 10,000+ concurrent users
- Data backup and disaster recovery""",
        key_features=[
            "Real-time market data",
            "Order management system",
            "Risk management",
            "Portfolio analytics",
            "Backtesting engine",
            "Security and compliance",
            "High performance and scalability",
        ],
        tags=["finance", "trading", "real-time", "complex", "high-performance"],
    ),
    RequirementExample(
        title="Healthcare Patient Management System",
        domain=Domain.HEALTHCARE,
        complexity=Complexity.COMPLEX,
        description="A comprehensive electronic health records system",
        requirement_text="""Build a healthcare patient management system with:

Patient Records:
- Patient demographics and contact info
- Medical history and allergies
- Current medications
- Lab results and imaging
- Immunization records
- Insurance information
- HIPAA-compliant data encryption

Appointments:
- Schedule appointments with doctors
- Calendar view for providers
- Automated reminders (email/SMS)
- Waitlist management
- Telemedicine integration

Clinical Features:
- Electronic prescriptions (e-prescribing)
- Clinical notes and documentation
- ICD-10 diagnosis coding
- Treatment plans
- Progress notes
- Referral management

Billing:
- Insurance verification
- Claim submission
- Payment processing
- Billing history
- Revenue cycle management

Analytics & Reporting:
- Patient demographics
- Appointment analytics
- Revenue reports
- Clinical quality metrics
- Regulatory compliance reports

Security & Compliance:
- HIPAA compliance
- Role-based access control
- Audit trails
- Data encryption at rest and in transit
- Secure messaging between providers""",
        key_features=[
            "Electronic health records",
            "Appointment scheduling",
            "E-prescribing",
            "Billing and insurance",
            "Clinical analytics",
            "HIPAA compliance",
            "Secure communication",
        ],
        tags=["healthcare", "ehr", "hipaa", "complex", "compliance"],
    ),
    RequirementExample(
        title="Learning Management System",
        domain=Domain.EDUCATION,
        complexity=Complexity.COMPLEX,
        description="A comprehensive online learning platform",
        requirement_text="""Create a learning management system (LMS) with:

Course Management:
- Create courses with modules and lessons
- Multiple content types (video, text, PDF, quizzes)
- Course prerequisites and sequences
- Drip content scheduling
- Course certification

Student Features:
- Course enrollment
- Progress tracking
- Bookmarks and notes
- Discussion forums
- Live chat with instructors
- Assignment submission
- Quiz taking with auto-grading

Instructor Tools:
- Content creation interface
- Student progress monitoring
- Grade management
- Feedback and comments
- Analytics dashboard
- Virtual classroom integration

Assessment:
- Various question types (MCQ, essay, coding)
- Automated grading
- Peer review
- Rubric-based grading
- Grade export

Gamification:
- Points and badges
- Leaderboards
- Achievement system
- Streaks and rewards

Administration:
- User management (students, instructors, admins)
- Course catalog
- Enrollment management
- Payment integration
- Reporting and analytics
- Integration with other tools (Zoom, Google Meet)

Mobile Support:
- Responsive design
- Offline content access
- Mobile app (iOS/Android)""",
        key_features=[
            "Course creation and management",
            "Multi-media content support",
            "Assessment and grading",
            "Student engagement tools",
            "Analytics and reporting",
            "Gamification",
            "Mobile support",
        ],
        tags=["education", "lms", "e-learning", "complex", "multi-user"],
    ),
    # ========== Automation Examples ==========
    RequirementExample(
        title="Email Newsletter Automation",
        domain=Domain.AUTOMATION,
        complexity=Complexity.SIMPLE,
        description="Automated email newsletter system",
        requirement_text="""Create an email newsletter automation system that:
- Fetches articles from RSS feeds daily
- Curates top 5 articles based on engagement metrics
- Generates a formatted HTML newsletter
- Sends email to subscriber list via SendGrid API
- Tracks open rates and click-through rates
- Allows subscribers to manage preferences
- Handles unsubscribe requests automatically

Run the automation daily at 8 AM EST.""",
        key_features=[
            "RSS feed integration",
            "Content curation",
            "Email template generation",
            "Scheduled sending",
            "Analytics tracking",
        ],
        tags=["automation", "email", "newsletter", "scheduling"],
    ),
    RequirementExample(
        title="Social Media Content Scheduler",
        domain=Domain.AUTOMATION,
        complexity=Complexity.MODERATE,
        description="Multi-platform social media scheduler",
        requirement_text="""Build a social media content scheduler with:

Content Management:
- Create posts with text, images, and hashtags
- Schedule posts for specific date/time
- Support multiple platforms (Twitter, LinkedIn, Instagram)
- Content calendar view
- Draft posts
- Post templates

Automation:
- Queue-based posting
- Optimal time suggestions based on engagement
- Automatic hashtag suggestions
- Image resizing per platform
- URL shortening
- Recurring posts

Analytics:
- Post performance metrics
- Engagement rates
- Best performing content
- Audience growth
- Platform-specific insights

Team Features:
- Multi-user access
- Approval workflow
- Comment/feedback on drafts
- Role-based permissions""",
        key_features=[
            "Multi-platform support",
            "Content scheduling",
            "Analytics dashboard",
            "Team collaboration",
            "Automation features",
        ],
        tags=["automation", "social-media", "scheduling", "moderate"],
    ),
]


# ============================================================================
# Helper Functions
# ============================================================================


def get_examples_by_domain(domain: Domain) -> List[RequirementExample]:
    """Get all examples for a specific domain"""
    return [ex for ex in REQUIREMENT_EXAMPLES if ex.domain == domain]


def get_examples_by_complexity(complexity: Complexity) -> List[RequirementExample]:
    """Get all examples for a specific complexity level"""
    return [ex for ex in REQUIREMENT_EXAMPLES if ex.complexity == complexity]


def get_examples_by_tag(tag: str) -> List[RequirementExample]:
    """Get all examples with a specific tag"""
    tag_lower = tag.lower()
    return [
        ex for ex in REQUIREMENT_EXAMPLES if tag_lower in [t.lower() for t in ex.tags]
    ]


def search_examples(query: str) -> List[RequirementExample]:
    """
    Search examples by keyword in title, description, or tags

    Args:
        query: Search query

    Returns:
        List of matching examples
    """
    query_lower = query.lower()
    results = []

    for ex in REQUIREMENT_EXAMPLES:
        # Search in title, description, and tags
        if (
            query_lower in ex.title.lower()
            or query_lower in ex.description.lower()
            or any(query_lower in tag.lower() for tag in ex.tags)
        ):
            results.append(ex)

    return results


def get_example_summary() -> Dict[str, int]:
    """Get summary statistics of examples"""
    return {
        "total": len(REQUIREMENT_EXAMPLES),
        "by_domain": {
            domain.value: len(get_examples_by_domain(domain)) for domain in Domain
        },
        "by_complexity": {
            complexity.value: len(get_examples_by_complexity(complexity))
            for complexity in Complexity
        },
    }


def suggest_examples(user_input: str, limit: int = 3) -> List[RequirementExample]:
    """
    Suggest relevant examples based on user input

    Args:
        user_input: User's partial requirement or keywords
        limit: Maximum number of suggestions

    Returns:
        List of suggested examples
    """
    # Search for matching examples
    matches = search_examples(user_input)

    # Return top matches
    return matches[:limit]
