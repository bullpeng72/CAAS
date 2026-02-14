# CAAS-E (CAAS Enterprise) Methodology
## Unified Development Framework v1.0

**Integration of**: CAAS 6-Phase + BMAD + SDD + TDD

**Author**: Claude Sonnet 4.5
**Date**: 2026-02-14
**Target**: Enterprise teams building complex AI agent systems
**Status**: Production-Ready Design

---

## Executive Summary

CAAS-E is an enterprise-grade development methodology that integrates four proven approaches into a unified framework for building complex AI agent systems:

- **CAAS 6-Phase Methodology**: Structured workflow from requirements to production code
- **BMAD (Breakthrough Method of Agile AI Driven Development)**: Story-based iteration with 21-agent collaboration and Party Mode multi-agent review
- **SDD (Spec-Driven Development)**: Contract-first approach with explicit specifications before code
- **TDD (Test-Driven Development)**: RED-GREEN-REFACTOR cycle ensuring code quality

**Key Innovations**:
✅ Story-based iteration (1 epic = 5-10 stories, 1 story = 3-5 features)
✅ Spec-driven contracts (API, data models, business rules defined before coding)
✅ Test-first development (Phase 4.5: RED, Phase 5: GREEN, Phase 5.5: REFACTOR)
✅ 7 human checkpoints ensuring quality and alignment
✅ Multi-agent peer review (Party Mode with 3/5 approval threshold)
✅ Traceability matrix (features → tasks → tests → code)

---

## 1. OVERVIEW DIAGRAM: Visual Flow of Integrated Methodology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAAS-E METHODOLOGY OVERVIEW                          │
│                                                                             │
│  Epic (15-30 features)                                                      │
│       │                                                                     │
│       ├─ Story 1 (3-5 features) ─┐                                         │
│       ├─ Story 2 (3-5 features) ─┼─ Iterative Development                 │
│       └─ Story N (3-5 features) ─┘                                         │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 0: CONCRETIZATION (Golden Data Generation)                    │  │
│  │ - BMAD: Story Decomposition + Human Review                          │  │
│  │ - SDD: Feature Specifications + API Contracts                       │  │
│  │ - TDD: Test Scenario Planning                                       │  │
│  │ ✓ CHECKPOINT 1: Golden Data Approval (Human-in-the-Loop)           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 1-2: DISCOVERY + ARCHITECTURE (Parallel)                      │  │
│  │ - BMAD: Multi-Agent Review (Party Mode)                             │  │
│  │ - SDD: System Architecture Specs                                    │  │
│  │ - TDD: Integration Test Scenarios                                   │  │
│  │ ✓ CHECKPOINT 2: Architecture Approval + Traceability Matrix         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 3: DESIGN (Agent/Task Design)                                 │  │
│  │ - BMAD: Agent Designer + QA Specialist Collaboration                │  │
│  │ - SDD: Agent/Task Interface Contracts                               │  │
│  │ - TDD: Agent Behavior Test Planning                                 │  │
│  │ ✓ CHECKPOINT 3: Design Completeness Validation                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 4: SPECIFICATION GENERATION (SDD Core)                        │  │
│  │ - Generate agent_specs.yaml, tool_specs.yaml, task_specs.yaml      │  │
│  │ - Define API contracts, data models, business rules                 │  │
│  │ ✓ CHECKPOINT 4: Specification Review (Human + LLM Judge)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 4.5: TEST-FIRST GENERATION (TDD Core - RED)                  │  │
│  │ - RED: Generate failing tests (unit, integration, e2e)              │  │
│  │ - Test stubs from specifications                                    │  │
│  │ ✓ CHECKPOINT 5: Test Coverage Review (>80% required)                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 5: DELIVERY (Code Generation - GREEN)                         │  │
│  │ - GREEN: Generate implementation to pass tests                      │  │
│  │ - BMAD: Code Generator + QA Specialist Collaboration                │  │
│  │ - Run tests → If fail: iterate                                      │  │
│  │ ✓ CHECKPOINT 6: All Tests Green (Quality Gate)                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 5.5: REFACTOR (TDD Refactor Step)                             │  │
│  │ - REFACTOR: Improve code while keeping tests green                  │  │
│  │ - BMAD: Multi-Perspective Code Review (Party Mode)                  │  │
│  │ ✓ CHECKPOINT 7: Code Quality Score >8.0/10                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 6: QUALITY ASSURANCE + CODE ANALYSIS (Parallel)               │  │
│  │ - QA: Security scan, compliance check, performance test             │  │
│  │ - Code Analysis: Runtime error fix, traceability validation         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                          │
│                    🚀 PRODUCTION DEPLOYMENT 🚀                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PHASE-BY-PHASE GUIDE

### **PHASE 0: CONCRETIZATION (Golden Data + Story Decomposition)**

#### **Objective**
Transform natural language requirements into structured Golden Data with story-based decomposition for iterative development.

#### **Inputs**
- Natural language requirement (user story, epic, or PRD)
- Optional: Domain hint, existing Golden Data

#### **Process**

**Step 0.1: Story Decomposition (BMAD Integration)**

```bash
# If requirement is large (15+ features expected), decompose first
caas analyze-requirement "Build e-commerce platform with AI recommendations" \
    --output-format story-breakdown
```

**Output**: Story breakdown
```json
{
  "epic": {
    "name": "E-Commerce AI Platform",
    "estimated_features": 28,
    "recommended_stories": 6
  },
  "stories": [
    {
      "id": "story_1",
      "name": "Product Catalog Management",
      "features": ["product_listing", "search", "filters", "sorting", "categories"],
      "dependencies": [],
      "estimated_complexity": "medium"
    },
    {
      "id": "story_2",
      "name": "User Authentication & Profile",
      "features": ["login", "signup", "profile", "preferences"],
      "dependencies": [],
      "estimated_complexity": "low"
    },
    {
      "id": "story_3",
      "name": "Shopping Cart & Checkout",
      "features": ["add_to_cart", "cart_management", "checkout", "payment"],
      "dependencies": ["story_2"],
      "estimated_complexity": "high"
    },
    {
      "id": "story_4",
      "name": "AI Recommendation Engine",
      "features": ["collaborative_filtering", "content_based", "trending", "personalized"],
      "dependencies": ["story_1", "story_2"],
      "estimated_complexity": "high"
    }
  ]
}
```

**Story Decomposition Rules**:
- **1 Story = 3-5 features** (ideal)
- **Max 7 features per story** (upper limit)
- **Dependencies**: Stories can depend on other stories
- **Complexity**: low (<3 features), medium (3-5), high (6-7)

**Step 0.2: Generate Golden Data (CAAS Core + SDD Integration)**

For **each story** OR for **full epic** (choose based on strategy):

```bash
# Option A: Story-by-story (recommended for large projects)
caas generate-phase --phase 0 \
    --requirement "$(cat story_1_requirement.txt)" \
    --domain e_commerce \
    --output ./artifacts/story_1/golden_data.json \
    --enable-sdd-specs  # NEW: Generate SDD specifications

# Option B: Full epic (recommended for small projects <15 features)
caas generate-phase --phase 0 \
    --requirement "$(cat epic_requirement.txt)" \
    --domain e_commerce \
    --output ./artifacts/epic/golden_data.json \
    --enable-sdd-specs
```

**SDD Enhancement** (`--enable-sdd-specs`): Adds specification fields to Golden Data
```json
{
  "features": [
    {
      "id": "product_listing",
      "name": "Product Listing",
      "description": "Display products with pagination",

      "api_contract": {
        "endpoint": "GET /api/products",
        "inputs": {
          "page": "int (default: 1)",
          "limit": "int (default: 20, max: 100)",
          "category": "str (optional)",
          "sort_by": "enum[price, rating, date] (default: date)"
        },
        "outputs": {
          "products": "List[Product]",
          "total": "int",
          "page": "int",
          "has_more": "bool"
        },
        "error_cases": [
          "400: Invalid pagination parameters",
          "404: Category not found",
          "500: Database connection error"
        ]
      },

      "data_model": {
        "entity": "Product",
        "schema": {
          "id": "UUID (primary key)",
          "name": "str (required, max: 200)",
          "price": "Decimal (required, min: 0.01)",
          "category_id": "UUID (foreign key → Category)",
          "rating": "float (0.0-5.0, default: 0.0)",
          "created_at": "datetime (auto)"
        },
        "validation_rules": [
          "price > 0",
          "name cannot be empty",
          "category_id must exist in categories table"
        ]
      },

      "business_rules": [
        "Free shipping for orders >$50",
        "Products with rating <2.0 hidden from search",
        "Max 100 items per page to prevent overload"
      ],

      "test_scenarios": [
        {
          "type": "unit",
          "description": "Test product listing with valid pagination",
          "given": "Database has 50 products",
          "when": "Request GET /api/products?page=2&limit=20",
          "then": "Return products 21-40, total=50, has_more=true"
        },
        {
          "type": "edge_case",
          "description": "Test with invalid page number",
          "given": "Database has 50 products",
          "when": "Request GET /api/products?page=-1",
          "then": "Return 400 error with message 'Invalid page number'"
        }
      ]
    }
  ]
}
```

**Step 0.3: Human Checkpoint - Golden Data Approval (BMAD Integration)**

```bash
# Review Golden Data with BMAD-style guidance
caas review-golden-data ./artifacts/story_1/golden_data.json \
    --checklist bmad \
    --show-recommendations
```

**✓ CHECKPOINT 1 - Review Checklist**:
- [ ] All features have clear descriptions and acceptance criteria
- [ ] API contracts are complete (inputs, outputs, error cases)
- [ ] Data models include validation rules
- [ ] Business rules are explicit and measurable
- [ ] Test scenarios cover happy path + edge cases
- [ ] Story dependencies are correctly identified
- [ ] Feature count is 3-7 per story (decompose if >7)

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 1-2
- 🔄 **REVISE**: Refine specifications and re-submit
- ❌ **REJECT**: Re-decompose stories or clarify requirements

---

### **PHASE 1-2: DISCOVERY + ARCHITECTURE (Parallel Execution)**

#### **Objective**
Analyze requirements deeply and design system architecture with multi-agent review.

#### **Inputs**
- Approved Golden Data from Phase 0
- Domain knowledge base
- Architecture patterns library

#### **Process**

**Step 1.1: Parallel Execution (BMAD Party Mode)**

```bash
# Execute Discovery + Architecture in parallel with multi-agent review
caas generate-phase --phase 1-2 \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-party-mode \  # BMAD: 3-5 agents review in parallel
    --party-size 5 \
    --approval-threshold 0.6  # 3/5 agents must approve
```

**Discovery (Phase 1)**:
- Domain classification (17 domains)
- Feature complexity analysis
- Tool requirements identification
- Agent role suggestions

**Architecture (Phase 2)**:
- System component design
- Agent communication patterns
- Data flow architecture
- Integration points

**Party Mode Review**:
- 5 agents review in parallel: Requirement Analyst, System Architect, Agent Designer, QA Specialist, Security Specialist
- Each scores 0-10 on 5 dimensions: Completeness, Feasibility, Scalability, Maintainability, Security
- Approval threshold: 3/5 agents score ≥6.0

**Step 1.2: Generate Traceability Matrix**

```bash
# Generate feature → task mapping for full traceability
caas generate-traceability \
    --golden-data ./artifacts/story_1/golden_data.json \
    --architecture ./artifacts/story_1/architecture.json \
    --output ./artifacts/story_1/traceability_matrix.json
```

**Output**: Traceability Matrix
```json
{
  "features": [
    {
      "feature_id": "product_listing",
      "mapped_tasks": ["fetch_products_task", "paginate_results_task"],
      "mapped_agents": ["data_retrieval_agent", "formatting_agent"],
      "test_coverage": ["test_product_listing_pagination", "test_empty_results"]
    }
  ]
}
```

**Step 1.3: Human Checkpoint - Architecture Approval**

**✓ CHECKPOINT 2 - Review Checklist**:
- [ ] All features mapped to tasks (100% coverage)
- [ ] Agent responsibilities clearly defined
- [ ] No circular dependencies
- [ ] Scalability patterns identified
- [ ] Security considerations addressed
- [ ] Party Mode approval ≥60% (3/5 agents)

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 3
- 🔄 **REVISE**: Address specific concerns from Party Mode feedback
- ❌ **REJECT**: Redesign architecture

---

### **PHASE 3: DESIGN (Agent/Task Design)**

#### **Objective**
Design detailed agent roles, tasks, and collaboration patterns with SDD contracts.

#### **Inputs**
- Approved architecture from Phase 1-2
- Traceability matrix
- Golden Data specifications

#### **Process**

**Step 3.1: Agent/Task Design with SDD Contracts**

```bash
# Generate agent and task designs with interface contracts
caas generate-phase --phase 3 \
    --architecture ./artifacts/story_1/architecture.json \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-sdd-contracts \  # Generate interface contracts
    --output ./artifacts/story_1/design.json
```

**SDD Agent Contract Example**:
```yaml
# agent_specs.yaml
agents:
  - id: product_retrieval_agent
    role: "Product Data Retrieval Specialist"
    goal: "Fetch and filter product data from database"

    interface_contract:
      inputs:
        - name: "category_filter"
          type: "Optional[str]"
          description: "Product category to filter by"
        - name: "page"
          type: "int"
          default: 1
        - name: "limit"
          type: "int"
          default: 20
          constraints: "1 <= limit <= 100"

      outputs:
        - name: "products"
          type: "List[ProductModel]"
          description: "List of product objects"
        - name: "total_count"
          type: "int"

      errors:
        - code: "DB_CONNECTION_ERROR"
          condition: "Database unreachable"
        - code: "INVALID_CATEGORY"
          condition: "Category ID not found"

    tools: ["database_query", "cache_lookup"]
    delegation: false
```

**SDD Task Contract Example**:
```yaml
# task_specs.yaml
tasks:
  - id: fetch_products_task
    description: "Retrieve paginated product list with filters"
    agent: product_retrieval_agent

    preconditions:
      - "Database connection established"
      - "Valid pagination parameters"

    postconditions:
      - "Products list returned (may be empty)"
      - "Total count reflects filter criteria"

    input_schema:
      page: "int (1+)"
      limit: "int (1-100)"
      category: "Optional[str]"

    output_schema:
      products: "List[Product]"
      total: "int"
      has_more: "bool"

    error_handling:
      - error: "DB_CONNECTION_ERROR"
        action: "Retry 3x with exponential backoff, then fail"
      - error: "INVALID_CATEGORY"
        action: "Return empty list with warning"
```

**Step 3.2: Design Completeness Validation**

```bash
# Validate design completeness against Golden Data
caas validate-design \
    --design ./artifacts/story_1/design.json \
    --golden-data ./artifacts/story_1/golden_data.json \
    --check-completeness \
    --check-consistency
```

**Validation Checks**:
- ✅ Every feature has at least one task
- ✅ Every task has exactly one agent
- ✅ All API contracts have corresponding task input/output schemas
- ✅ All business rules referenced in task postconditions
- ✅ All test scenarios have traceable task coverage

**Step 3.3: Human Checkpoint - Design Review**

**✓ CHECKPOINT 3 - Review Checklist**:
- [ ] Agent responsibilities non-overlapping
- [ ] Task granularity appropriate (not too fine/coarse)
- [ ] Interface contracts complete (inputs, outputs, errors)
- [ ] Preconditions/postconditions testable
- [ ] Error handling strategies defined
- [ ] Delegation patterns clear

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 4
- 🔄 **REVISE**: Adjust agent boundaries or task assignments
- ❌ **REJECT**: Redesign agent/task structure

---

### **PHASE 4: SPECIFICATION GENERATION (SDD Core)**

#### **Objective**
Generate complete, executable specifications before writing any implementation code.

#### **Inputs**
- Approved design from Phase 3
- SDD contracts (agent_specs.yaml, task_specs.yaml)

#### **Process**

**Step 4.1: Generate Comprehensive Specifications**

```bash
# Generate all specification files
caas generate-phase --phase 4 \
    --design ./artifacts/story_1/design.json \
    --output-dir ./artifacts/story_1/specs/ \
    --spec-types agent,task,tool,data_model,business_rule
```

**Generated Files**:
```
./artifacts/story_1/specs/
├── agent_specs.yaml        # Agent interface contracts
├── task_specs.yaml         # Task contracts with pre/post conditions
├── tool_specs.yaml         # Tool function signatures
├── data_models.yaml        # Pydantic models with validation
└── business_rules.yaml     # Business logic specifications
```

**Example: data_models.yaml**
```yaml
models:
  - name: ProductModel
    description: "Product entity with validation rules"

    fields:
      id:
        type: UUID
        required: true
        primary_key: true

      name:
        type: str
        required: true
        max_length: 200
        validation: "non-empty string"

      price:
        type: Decimal
        required: true
        validation: "price > 0.01"

      category_id:
        type: UUID
        required: true
        foreign_key: "Category.id"

      rating:
        type: float
        default: 0.0
        validation: "0.0 <= rating <= 5.0"

    indexes:
      - fields: ["category_id", "rating"]
        unique: false
```

**Example: business_rules.yaml**
```yaml
rules:
  - id: free_shipping_threshold
    name: "Free Shipping Above $50"
    description: "Orders over $50 get free shipping"

    trigger: "Order.calculate_total() called"

    condition: "order.total > 50.00"

    action: "order.shipping_cost = 0.00"

    priority: 1  # Applied before tax calculation

    test_cases:
      - input: {total: 49.99}
        expected: {shipping_cost: 5.99}
      - input: {total: 50.01}
        expected: {shipping_cost: 0.00}
```

**Step 4.2: Specification Review (Human + LLM Judge)**

```bash
# Dual review: Human + LLM Judge
caas review-specifications \
    --spec-dir ./artifacts/story_1/specs/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-llm-judge \
    --review-dimensions completeness,consistency,testability
```

**LLM Judge Evaluation**:
- **Completeness**: All API contracts fully specified (inputs, outputs, errors)
- **Consistency**: Data models match API contracts, business rules align with specs
- **Testability**: All specs have clear acceptance criteria

**✓ CHECKPOINT 4 - Review Checklist**:
- [ ] All specifications complete (no TBD fields)
- [ ] Data models have validation rules
- [ ] Business rules have test cases
- [ ] Tool signatures match task requirements
- [ ] LLM Judge score ≥7.0/10.0

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 4.5 (Test Generation)
- 🔄 **REVISE**: Fill in missing specifications
- ❌ **REJECT**: Re-design contracts

---

### **PHASE 4.5: TEST-FIRST GENERATION (TDD Core - RED)**

#### **Objective**
Generate comprehensive failing tests before implementation (TDD RED phase).

#### **Inputs**
- Approved specifications from Phase 4
- Test scenarios from Golden Data

#### **Process**

**Step 4.5.1: Generate Test Stubs**

```bash
# Generate failing tests from specifications
caas generate-phase --phase 4.5 \
    --spec-dir ./artifacts/story_1/specs/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --test-types unit,integration,e2e \
    --coverage-target 80 \
    --output-dir ./artifacts/story_1/tests/
```

**Generated Test Files**:
```
./artifacts/story_1/tests/
├── test_product_retrieval_agent.py   # Unit tests for agents
├── test_fetch_products_task.py       # Unit tests for tasks
├── test_product_listing_integration.py  # Integration tests
└── test_e2e_product_catalog.py       # End-to-end tests
```

**Example: test_product_retrieval_agent.py**
```python
import pytest
from unittest.mock import Mock, patch
from agents import ProductRetrievalAgent
from models import ProductModel

class TestProductRetrievalAgent:
    """Unit tests for Product Retrieval Agent (TDD RED - should fail initially)"""

    @pytest.fixture
    def agent(self):
        return ProductRetrievalAgent(
            role="Product Data Retrieval Specialist",
            goal="Fetch and filter product data from database",
            tools=[Mock()],  # Mock tools
        )

    def test_fetch_products_valid_pagination(self, agent):
        """Test: Fetch products with valid pagination parameters"""
        # Given: Database has 50 products
        with patch('tools.database_query') as mock_db:
            mock_db.return_value = [
                ProductModel(id=21, name="Product 21", price=29.99),
                # ... 19 more products
            ]

            # When: Request page 2 with limit 20
            result = agent.fetch_products(page=2, limit=20)

            # Then: Return products 21-40
            assert len(result['products']) == 20
            assert result['total'] == 50
            assert result['has_more'] is True
            assert result['products'][0].id == 21

    def test_fetch_products_invalid_page(self, agent):
        """Test: Handle invalid page number (edge case)"""
        # When: Request with invalid page
        with pytest.raises(ValidationError) as exc_info:
            agent.fetch_products(page=-1, limit=20)

        # Then: Raise validation error
        assert "Invalid page number" in str(exc_info.value)
```

**Step 4.5.2: Run Tests (Expect Failures)**

```bash
# Run tests - all should fail (RED phase)
cd ./artifacts/story_1/tests/
pytest -v --tb=short

# Expected output:
# test_fetch_products_valid_pagination ... FAILED
# test_fetch_products_invalid_page ... FAILED
# ====================== 15 failed in 2.34s ======================
```

**Step 4.5.3: Test Coverage Analysis**

```bash
# Analyze test coverage against specifications
caas analyze-test-coverage \
    --tests ./artifacts/story_1/tests/ \
    --specs ./artifacts/story_1/specs/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --report-format html
```

**✓ CHECKPOINT 5 - Review Checklist**:
- [ ] Test coverage ≥80% (all specs have tests)
- [ ] Unit tests for all agents and tasks
- [ ] Integration tests for feature workflows
- [ ] E2E tests for user scenarios
- [ ] Edge cases and error conditions tested
- [ ] All tests currently FAILING (RED phase confirmed)

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 5 (Implementation)
- 🔄 **REVISE**: Add missing tests or edge cases
- ❌ **REJECT**: Test scenarios insufficient

---

### **PHASE 5: DELIVERY (Code Generation - GREEN)**

#### **Objective**
Generate implementation code that makes all tests pass (TDD GREEN phase).

#### **Inputs**
- Approved specifications from Phase 4
- Failing tests from Phase 4.5
- Golden Data with business rules

#### **Process**

**Step 5.1: Generate Implementation Code**

```bash
# Generate code to pass all tests
caas generate-phase --phase 5 \
    --spec-dir ./artifacts/story_1/specs/ \
    --tests ./artifacts/story_1/tests/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-test-driven \  # Use tests to guide code generation
    --output-dir ./generated/story_1/
```

**Generated Files**:
```
./generated/story_1/
├── main.py              # CrewAI Crew orchestration
├── agents.py            # Agent implementations
├── tasks.py             # Task definitions
├── tools.py             # Custom tools
├── models.py            # Pydantic data models
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
└── README.md            # Usage instructions
```

**Step 5.2: Run Tests (Expect Success)**

```bash
# Run tests - should all pass (GREEN phase)
cd ./generated/story_1/
pip install -r requirements.txt
pytest tests/ -v --cov=. --cov-report=html

# Expected output:
# test_fetch_products_valid_pagination ... PASSED
# test_fetch_products_invalid_page ... PASSED
# ====================== 15 passed in 3.12s ======================
# Coverage: 87%
```

**Step 5.3: Iterative Fixing (If Tests Fail)**

```bash
# If tests fail, analyze and fix
caas fix-implementation \
    --code-dir ./generated/story_1/ \
    --tests ./artifacts/story_1/tests/ \
    --test-results ./test-results.xml \
    --max-iterations 3
```

**Fixing Strategy**:
1. Parse test failure messages
2. Identify failing code section
3. Apply LLM-based auto-fix
4. Re-run tests
5. Repeat until all tests pass (max 3 iterations)

**✓ CHECKPOINT 6 - Quality Gate**:
- [ ] All tests PASSING (100% success rate)
- [ ] Test coverage ≥80%
- [ ] No critical linting errors (flake8, pylint)
- [ ] All business rules implemented
- [ ] No hardcoded secrets or credentials

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 5.5 (Refactoring)
- 🔄 **RETRY**: Re-run auto-fix (up to 3 iterations)
- ❌ **REJECT**: Manual intervention required

---

### **PHASE 5.5: REFACTOR (TDD Refactor Step)**

#### **Objective**
Improve code quality, readability, and maintainability while keeping all tests green.

#### **Inputs**
- Working implementation from Phase 5
- Passing tests from Phase 4.5
- Code quality metrics

#### **Process**

**Step 5.5.1: Code Quality Analysis**

```bash
# Analyze code quality metrics
caas analyze-code-quality \
    --code-dir ./generated/story_1/ \
    --metrics complexity,duplication,style,security \
    --output ./quality_report.json
```

**Quality Metrics**:
- **Complexity**: Cyclomatic complexity score (target: <10 per function)
- **Duplication**: Code duplication percentage (target: <5%)
- **Style**: PEP 8 compliance (target: 95%+)
- **Security**: Bandit security issues (target: 0 high/critical)

**Step 5.5.2: Multi-Perspective Code Review (BMAD Party Mode)**

```bash
# Party Mode review with 5 perspectives
caas review-code \
    --code-dir ./generated/story_1/ \
    --enable-party-mode \
    --party-size 5 \
    --perspectives "security,performance,maintainability,readability,testability"
```

**Party Mode Reviewers**:
1. **Security Specialist**: SQL injection, XSS, secrets exposure
2. **Performance Engineer**: O(n) complexity, caching opportunities
3. **Maintainability Expert**: Code smells, SOLID principles
4. **Readability Advocate**: Naming, comments, documentation
5. **Test Engineer**: Test coverage gaps, brittleness

**Step 5.5.3: Apply Refactoring**

```bash
# Apply refactoring recommendations
caas refactor-code \
    --code-dir ./generated/story_1/ \
    --review-results ./party_mode_review.json \
    --apply-safe-refactorings \  # Only apply if tests stay green
    --backup
```

**Safe Refactorings** (tests must stay green):
- Extract method (reduce complexity)
- Rename variable/function (improve readability)
- Remove duplication (DRY principle)
- Add type hints (improve type safety)
- Extract constant (magic numbers)

**Step 5.5.4: Re-run Tests After Refactoring**

```bash
# Ensure tests still pass after refactoring
cd ./generated/story_1/
pytest tests/ -v --cov=. --cov-report=html

# All tests must PASS - if any fail, revert refactoring
```

**✓ CHECKPOINT 7 - Code Quality Gate**:
- [ ] All tests still PASSING (100% green)
- [ ] Code quality score ≥8.0/10.0
- [ ] Cyclomatic complexity <10 per function
- [ ] Code duplication <5%
- [ ] Security scan: 0 high/critical issues
- [ ] Party Mode approval ≥80% (4/5 reviewers)

**Approval Decision**:
- ✅ **APPROVE**: Proceed to Phase 6 (Final QA)
- 🔄 **REVISE**: Address specific code review feedback
- ❌ **REJECT**: Revert refactoring, keep Phase 5 code

---

### **PHASE 6: QUALITY ASSURANCE + CODE ANALYSIS (Parallel)**

#### **Objective**
Final quality assurance, security scanning, and traceability validation before production deployment.

#### **Inputs**
- Refactored code from Phase 5.5
- All test results
- Golden Data for traceability

#### **Process**

**Step 6.1: Parallel Execution (QA + Code Analysis)**

```bash
# Execute QA and Code Analysis in parallel
caas generate-phase --phase 6 \
    --code-dir ./generated/story_1/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-parallel \
    --qa-checks security,compliance,performance \
    --analysis-checks traceability,completeness,runtime_errors
```

**QA Specialist Tasks**:
- Security scan (OWASP Top 10, dependency vulnerabilities)
- Compliance check (license compatibility, data privacy)
- Performance test (load testing, memory profiling)

**Code Analysis Agent Tasks**:
- Traceability validation (all features implemented)
- Completeness check (Golden Data vs actual code)
- Runtime error detection (static analysis + dry-run)

**Step 6.2: Security & Compliance Report**

```bash
# Generate comprehensive security report
caas qa-report \
    --code-dir ./generated/story_1/ \
    --report-type security \
    --output ./security_report.html
```

**Security Checks**:
- Dependency vulnerabilities (safety, pip-audit)
- Code security issues (Bandit)
- Secrets detection (detect-secrets)
- License compliance (pip-licenses)

**Step 6.3: Traceability Validation**

```bash
# Validate all features are implemented
caas validate-traceability \
    --code-dir ./generated/story_1/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --traceability-matrix ./artifacts/story_1/traceability_matrix.json \
    --detailed-report
```

**Traceability Matrix Validation**:
```json
{
  "summary": {
    "total_features": 5,
    "implemented_features": 5,
    "implementation_rate": "100%",
    "total_tasks": 8,
    "implemented_tasks": 8,
    "task_completion": "100%"
  },
  "feature_traceability": [
    {
      "feature_id": "product_listing",
      "status": "IMPLEMENTED",
      "mapped_tasks": ["fetch_products_task", "paginate_results_task"],
      "mapped_code": ["agents.py:ProductRetrievalAgent", "tasks.py:fetch_products_task"],
      "test_coverage": ["test_product_retrieval_agent.py", "test_fetch_products_task.py"]
    }
  ]
}
```

**Step 6.4: Production-Ready Gate**

**Final Checklist**:
- [ ] All tests passing (100%)
- [ ] Security scan: 0 critical, <3 medium issues
- [ ] Test coverage ≥80%
- [ ] Code quality ≥8.0/10.0
- [ ] Traceability: 100% features implemented
- [ ] Performance: <500ms p95 latency
- [ ] Documentation complete (README, API docs)
- [ ] Deployment artifacts ready (Docker, requirements.txt)

**Approval Decision**:
- ✅ **APPROVE**: Deploy to production
- 🔄 **REVISE**: Address specific QA issues
- ❌ **REJECT**: Major issues found, go back to Phase 5

---

## 3. ITERATION STRATEGIES

### **Macro Iteration: Epic-Level (BMAD Story Approach)**

```
Epic (28 features) → 6 Stories
  ↓
Story 1 (5 features) → Phase 0-6 → Production ✅
  ↓
Story 2 (4 features) → Phase 0-6 → Production ✅
  ↓
...
  ↓
Story 6 (3 features) → Phase 0-6 → Production ✅
```

**When to Use**:
- Large projects (15+ features)
- Multiple teams working in parallel
- Need incremental delivery every 1-2 weeks

**Benefits**:
- Incremental value delivery
- Reduced integration risk
- Faster feedback loops

---

### **Micro Iteration: Story-Level (Phase Refinement)**

```
Story 1 → Phase 0 → ❌ Reject → Refine requirements → Phase 0 again
                 → ✅ Approve → Phase 1-2 → ❌ Revise architecture
                                         → ✅ Approve → Phase 3 → ...
```

**When to Use**:
- Complex requirements needing clarification
- Architectural experiments (try multiple approaches)
- Stakeholder alignment needed

**Benefits**:
- Higher quality through iteration
- Risk mitigation early in the process
- Stakeholder confidence

---

### **Nano Iteration: TDD Cycle (RED-GREEN-REFACTOR)**

```
Phase 4.5 (RED) → Write failing test
                ↓
Phase 5 (GREEN) → Implement minimum code to pass test
                ↓
                Tests fail? → Fix code → Re-run tests
                ↓
                Tests pass? ✅
                ↓
Phase 5.5 (REFACTOR) → Improve code while keeping tests green
                      ↓
                      Re-run tests → All pass? → Done ✅
```

**When to Use**:
- Complex business logic
- Critical features requiring high reliability
- Performance-sensitive code

**Benefits**:
- Bug prevention through tests-first
- Design improvement through refactoring
- Documentation via tests

---

## 4. HUMAN-IN-THE-LOOP CHECKPOINTS

### **7 Checkpoints Summary**

| Phase | Checkpoint | Decision | Avg Time | Critical Focus |
|-------|-----------|----------|----------|----------------|
| **Phase 0** | Golden Data Approval | Approve/Revise/Reject | 15-30 min | Feature completeness, API contracts |
| **Phase 1-2** | Architecture Approval | Approve/Revise/Reject | 20-40 min | System design, dependencies, Party Mode consensus |
| **Phase 3** | Design Completeness | Approve/Revise/Reject | 15-25 min | Agent boundaries, task granularity |
| **Phase 4** | Specification Review | Approve/Revise/Reject | 10-20 min | Contract completeness, LLM Judge score |
| **Phase 4.5** | Test Coverage Review | Approve/Revise/Reject | 5-15 min | >80% coverage, edge cases |
| **Phase 5** | Quality Gate (All Tests Green) | Approve/Retry/Reject | 5-10 min | 100% test pass rate |
| **Phase 5.5** | Code Quality Score | Approve/Revise/Reject | 10-20 min | Quality ≥8.0, Party Mode review |

**Total Human Review Time**: ~80-180 minutes per story (1.5-3 hours)

---

### **Best Practices for Human Review**

**1. Golden Data Review (Checkpoint 1)**
- Focus on API contracts: Are inputs/outputs clear?
- Validate business rules: Are they measurable and testable?
- Check test scenarios: Do they cover edge cases?

**2. Architecture Review (Checkpoint 2)**
- Trace features to tasks: Is every feature covered?
- Check dependencies: Are there circular references?
- Review Party Mode feedback: What are recurring concerns?

**3. Design Review (Checkpoint 3)**
- Agent boundaries: Is there overlap or gaps?
- Task granularity: Too fine (10+ tasks per feature) or too coarse (1 task for everything)?
- Interface contracts: Are preconditions/postconditions testable?

**4. Specification Review (Checkpoint 4)**
- Completeness: Any "TBD" or placeholder fields?
- Consistency: Do data models match API contracts?
- LLM Judge score: If <7.0, what dimensions failed?

**5. Test Coverage Review (Checkpoint 5)**
- Percentage: Is coverage ≥80%?
- Quality: Are tests meaningful or just chasing coverage?
- Edge cases: Error handling, boundary conditions?

**6. Quality Gate (Checkpoint 6)**
- Tests: Are they truly passing or flaky?
- Quick scan: Any obvious bugs in implementation?
- Business rules: Spot-check 1-2 critical rules

**7. Code Quality Review (Checkpoint 7)**
- Party Mode: What did 5 reviewers flag?
- Complexity: Any functions >50 lines or complexity >10?
- Security: Any hardcoded secrets or SQL injection risks?

---

## 5. ENTERPRISE PATTERNS

### **Pattern 1: Multi-Team Parallel Development**

```
Epic: E-Commerce Platform (28 features, 6 stories)

Team A (Backend)          Team B (Frontend)        Team C (AI/ML)
  ↓                         ↓                        ↓
Story 1: API Foundation   Story 2: User Auth UI    Story 4: Recommendations
  Phase 0-6 (2 weeks)       Phase 0-6 (2 weeks)      Phase 0-6 (3 weeks)
  ↓                         ↓                        ↓
Story 3: Cart/Checkout    Story 5: Order UI        (continues)
  Phase 0-6 (2 weeks)       Phase 0-6 (2 weeks)

Sprint 1: Stories 1, 2 in parallel
Sprint 2: Stories 3, 5 in parallel (depend on 1, 2)
Sprint 3: Story 4 (depends on 1, 2)
```

**Coordination**:
- Shared Golden Data repository
- Daily sync on API contracts
- Integration tests at story boundaries

---

### **Pattern 2: Risk-Driven Story Prioritization**

```
Epic Risk Assessment:
  Story 1: Product Catalog (Low Risk, High Value) → Priority 1
  Story 2: User Auth (Low Risk, High Value) → Priority 2
  Story 3: Checkout (Medium Risk, High Value) → Priority 3
  Story 4: AI Recommendations (High Risk, Medium Value) → Priority 4
  Story 5: Order Management (Low Risk, Medium Value) → Priority 5
  Story 6: Analytics (Low Risk, Low Value) → Priority 6

Development Order: 1 → 2 → 3 → 4 → 5 → 6
```

**Strategy**:
- Tackle high-value, low-risk first (quick wins)
- De-risk high-risk stories early (learning)
- Defer low-value stories (can be cut if needed)

---

### **Pattern 3: Spike Stories for Exploration**

```
Epic: E-Commerce Platform

Before Story 4 (AI Recommendations):
  ↓
Spike Story: "Evaluate Recommendation Algorithms"
  - Duration: 3 days
  - Goal: Choose between collaborative filtering vs content-based
  - Deliverable: Prototype + decision document
  - No production code
  ↓
Decision: Collaborative filtering
  ↓
Story 4: AI Recommendations (use collaborative filtering)
  Phase 0-6 (3 weeks)
```

**When to Use**:
- Unclear technical approach
- New technology/library evaluation
- Performance benchmarking needed

---

### **Pattern 4: Continuous Integration Pipeline**

```
Story 1 Complete (Phase 6 ✅)
  ↓
Automated CI/CD Pipeline:
  1. Run all tests (unit, integration, e2e)
  2. Security scan (Bandit, safety)
  3. Code quality check (flake8, pylint)
  4. Build Docker image
  5. Deploy to staging
  6. Run smoke tests
  7. If all pass → Auto-deploy to production
  8. If any fail → Alert team, rollback
```

**CAAS Integration**:
```bash
# Add to .github/workflows/caas-deploy.yml
caas validate-traceability --code-dir ./generated/ --golden-data ./artifacts/golden_data.json
caas qa-report --code-dir ./generated/ --report-type security
pytest tests/ --cov=. --cov-report=xml --cov-fail-under=80
```

---

## 6. TROUBLESHOOTING GUIDE

### **Problem: Phase 0 generates too many features (>7 per story)**

**Solution**:
```bash
# Force decomposition
caas analyze-requirement "..." --max-features-per-story 5 --output-format story-breakdown

# Manually split Golden Data
caas split-golden-data ./golden_data.json --split-by feature_count --max-per-split 5
```

---

### **Problem: Party Mode reviewers disagree (approval <60%)**

**Solution**:
1. Review individual agent feedback:
   ```bash
   caas show-party-feedback ./party_mode_review.json --detailed
   ```

2. Identify common concerns (e.g., 3/5 agents flag "scalability")

3. Address specific concerns and re-run Party Mode:
   ```bash
   caas generate-phase --phase 1-2 --golden-data ./refined_golden_data.json --enable-party-mode
   ```

---

### **Problem: Tests fail after Phase 5 code generation**

**Solution**:
1. Analyze test failures:
   ```bash
   pytest tests/ -v --tb=long > test_failures.log
   caas analyze-test-failures --log test_failures.log
   ```

2. Auto-fix (up to 3 iterations):
   ```bash
   caas fix-implementation --code-dir ./generated/ --tests ./tests/ --max-iterations 3
   ```

3. If auto-fix fails, manual intervention:
   - Read test failure message
   - Identify failing function
   - Compare with specification (Phase 4 spec file)
   - Manually fix code

---

### **Problem: Code quality score <8.0 after Phase 5.5**

**Solution**:
1. Identify quality issues:
   ```bash
   caas analyze-code-quality --code-dir ./generated/ --verbose
   ```

2. Apply specific refactorings:
   ```bash
   # Reduce complexity
   caas refactor --type extract_method --threshold complexity>10

   # Remove duplication
   caas refactor --type remove_duplication --threshold similarity>80%

   # Add type hints
   caas refactor --type add_type_hints --coverage 100%
   ```

3. Re-run Party Mode review:
   ```bash
   caas review-code --code-dir ./generated/ --enable-party-mode
   ```

---

### **Problem: Traceability validation fails (features not implemented)**

**Solution**:
1. Generate detailed gap report:
   ```bash
   caas validate-traceability --golden-data ./golden_data.json --code-dir ./generated/ --detailed-report
   ```

2. Identify missing features:
   ```json
   {
     "missing_features": [
       {"feature_id": "advanced_search", "reason": "No matching task found"}
     ]
   }
   ```

3. Add missing features:
   - Option A: Go back to Phase 3, add tasks for missing features, re-generate Phase 4-6
   - Option B: Manually implement missing features and tests

---

## 7. EXAMPLE WALKTHROUGH: E-Commerce Platform

### **Epic**: E-Commerce AI Platform (28 features)

**Step 1: Story Decomposition (Phase 0)**

```bash
caas analyze-requirement "Build an e-commerce platform with product catalog, user authentication, shopping cart, checkout, AI recommendations, and order management" \
    --output-format story-breakdown \
    --max-features-per-story 5

# Output: 6 stories (Product Catalog, User Auth, Cart/Checkout, AI Recommendations, Order Management, Analytics)
```

**Step 2: Generate Golden Data for Story 1 (Phase 0)**

```bash
caas generate-phase --phase 0 \
    --requirement "Product catalog with listing, search, filters, sorting, and categories" \
    --domain e_commerce \
    --enable-sdd-specs \
    --output ./artifacts/story_1/golden_data.json

# Human Review (Checkpoint 1): Approve ✅
```

**Step 3: Discovery + Architecture (Phase 1-2)**

```bash
caas generate-phase --phase 1-2 \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-party-mode \
    --party-size 5 \
    --approval-threshold 0.6

# Party Mode Result: 4/5 agents approve (80%) ✅
# Human Review (Checkpoint 2): Approve ✅
```

**Step 4: Agent/Task Design (Phase 3)**

```bash
caas generate-phase --phase 3 \
    --architecture ./artifacts/story_1/architecture.json \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-sdd-contracts \
    --output ./artifacts/story_1/design.json

# Design Output:
# - 3 Agents: ProductRetrievalAgent, SearchAgent, CategoryAgent
# - 5 Tasks: fetch_products, search_products, filter_by_category, sort_results, paginate

# Human Review (Checkpoint 3): Approve ✅
```

**Step 5: Specification Generation (Phase 4)**

```bash
caas generate-phase --phase 4 \
    --design ./artifacts/story_1/design.json \
    --output-dir ./artifacts/story_1/specs/

# Generated: agent_specs.yaml, task_specs.yaml, tool_specs.yaml, data_models.yaml, business_rules.yaml

# LLM Judge Review: 8.5/10.0 ✅
# Human Review (Checkpoint 4): Approve ✅
```

**Step 6: Test Generation (Phase 4.5 - RED)**

```bash
caas generate-phase --phase 4.5 \
    --spec-dir ./artifacts/story_1/specs/ \
    --test-types unit,integration,e2e \
    --coverage-target 85 \
    --output-dir ./artifacts/story_1/tests/

# Generated: 25 tests (15 unit, 7 integration, 3 e2e)
# Run tests: 25 failed (expected - RED phase) ✅

# Human Review (Checkpoint 5): Coverage 87% ✅, Approve ✅
```

**Step 7: Code Generation (Phase 5 - GREEN)**

```bash
caas generate-phase --phase 5 \
    --spec-dir ./artifacts/story_1/specs/ \
    --tests ./artifacts/story_1/tests/ \
    --enable-test-driven \
    --output-dir ./generated/story_1/

# Generated: main.py, agents.py, tasks.py, tools.py, models.py, requirements.txt
# Run tests: 25 passed ✅

# Human Review (Checkpoint 6): All tests green ✅, Approve ✅
```

**Step 8: Refactoring (Phase 5.5 - REFACTOR)**

```bash
caas analyze-code-quality --code-dir ./generated/story_1/
# Quality: 7.8/10.0 (needs improvement)

caas review-code --code-dir ./generated/story_1/ --enable-party-mode --party-size 5
# Party Mode: 3/5 agents flag complexity issues

caas refactor-code --code-dir ./generated/story_1/ --apply-safe-refactorings

# Re-run tests: 25 passed ✅
# Quality: 8.6/10.0 ✅

# Human Review (Checkpoint 7): Quality ≥8.0 ✅, Approve ✅
```

**Step 9: Final QA + Analysis (Phase 6)**

```bash
caas generate-phase --phase 6 \
    --code-dir ./generated/story_1/ \
    --golden-data ./artifacts/story_1/golden_data.json \
    --enable-parallel

# QA Report:
# - Security: 0 critical, 1 medium (outdated dependency) ✅
# - Performance: p95 latency 320ms ✅
# - Traceability: 100% features implemented ✅

# Deploy to production ✅
```

---

## 8. CLI COMMAND REFERENCE

### **Phase 0: Concretization**

```bash
# Analyze requirement and decompose into stories
caas analyze-requirement "REQUIREMENT_TEXT" \
    --output-format story-breakdown \
    --max-features-per-story 5

# Generate Golden Data
caas generate-phase --phase 0 \
    --requirement "REQUIREMENT_TEXT" \
    --domain DOMAIN_NAME \
    --enable-sdd-specs \
    --output ./artifacts/golden_data.json

# Review Golden Data
caas review-golden-data ./artifacts/golden_data.json \
    --checklist bmad \
    --show-recommendations
```

---

### **Phase 1-2: Discovery + Architecture**

```bash
# Generate architecture with Party Mode
caas generate-phase --phase 1-2 \
    --golden-data ./artifacts/golden_data.json \
    --enable-party-mode \
    --party-size 5 \
    --approval-threshold 0.6

# Generate traceability matrix
caas generate-traceability \
    --golden-data ./artifacts/golden_data.json \
    --architecture ./artifacts/architecture.json \
    --output ./artifacts/traceability_matrix.json
```

---

### **Phase 3: Design**

```bash
# Generate agent/task design with SDD contracts
caas generate-phase --phase 3 \
    --architecture ./artifacts/architecture.json \
    --golden-data ./artifacts/golden_data.json \
    --enable-sdd-contracts \
    --output ./artifacts/design.json

# Validate design completeness
caas validate-design \
    --design ./artifacts/design.json \
    --golden-data ./artifacts/golden_data.json \
    --check-completeness \
    --check-consistency
```

---

### **Phase 4: Specification Generation**

```bash
# Generate specifications
caas generate-phase --phase 4 \
    --design ./artifacts/design.json \
    --output-dir ./artifacts/specs/ \
    --spec-types agent,task,tool,data_model,business_rule

# Review specifications
caas review-specifications \
    --spec-dir ./artifacts/specs/ \
    --golden-data ./artifacts/golden_data.json \
    --enable-llm-judge \
    --review-dimensions completeness,consistency,testability
```

---

### **Phase 4.5: Test Generation (TDD RED)**

```bash
# Generate failing tests
caas generate-phase --phase 4.5 \
    --spec-dir ./artifacts/specs/ \
    --test-types unit,integration,e2e \
    --coverage-target 80 \
    --output-dir ./artifacts/tests/

# Analyze test coverage
caas analyze-test-coverage \
    --tests ./artifacts/tests/ \
    --specs ./artifacts/specs/ \
    --report-format html
```

---

### **Phase 5: Code Generation (TDD GREEN)**

```bash
# Generate implementation
caas generate-phase --phase 5 \
    --spec-dir ./artifacts/specs/ \
    --tests ./artifacts/tests/ \
    --enable-test-driven \
    --output-dir ./generated/

# Fix implementation if tests fail
caas fix-implementation \
    --code-dir ./generated/ \
    --tests ./artifacts/tests/ \
    --max-iterations 3
```

---

### **Phase 5.5: Refactoring (TDD REFACTOR)**

```bash
# Analyze code quality
caas analyze-code-quality \
    --code-dir ./generated/ \
    --metrics complexity,duplication,style,security

# Party Mode code review
caas review-code \
    --code-dir ./generated/ \
    --enable-party-mode \
    --party-size 5

# Apply refactoring
caas refactor-code \
    --code-dir ./generated/ \
    --apply-safe-refactorings \
    --backup
```

---

### **Phase 6: QA + Analysis**

```bash
# Final QA and analysis
caas generate-phase --phase 6 \
    --code-dir ./generated/ \
    --golden-data ./artifacts/golden_data.json \
    --enable-parallel

# Security report
caas qa-report \
    --code-dir ./generated/ \
    --report-type security \
    --output ./security_report.html

# Traceability validation
caas validate-traceability \
    --code-dir ./generated/ \
    --golden-data ./artifacts/golden_data.json \
    --detailed-report
```

---

## 9. TOOLS & INTEGRATIONS

### **Required Tools**

- **CAAS v0.5.1+** (Core framework)
- **Python 3.11+**
- **Git** (Version control)
- **Docker** (Containerization)

### **Optional Integrations**

**CI/CD**:
- GitHub Actions
- GitLab CI
- Jenkins

**Testing**:
- pytest (Required)
- pytest-cov (Coverage)
- pytest-xdist (Parallel tests)

**Code Quality**:
- Black (Formatting)
- Flake8 (Linting)
- Pylint (Static analysis)
- Bandit (Security)

**Monitoring**:
- Sentry (Error tracking)
- Prometheus (Metrics)
- Grafana (Dashboards)

---

## 10. APPENDIX

### **A. Story Decomposition Template**

```json
{
  "epic": {
    "name": "EPIC_NAME",
    "description": "EPIC_DESCRIPTION",
    "estimated_features": 25,
    "business_value": "high"
  },
  "stories": [
    {
      "id": "story_1",
      "name": "STORY_NAME",
      "description": "STORY_DESCRIPTION",
      "features": ["feature_1", "feature_2", "feature_3"],
      "dependencies": [],
      "estimated_complexity": "medium",
      "acceptance_criteria": [
        "CRITERION_1",
        "CRITERION_2"
      ]
    }
  ]
}
```

---

### **B. SDD Specification Template**

```yaml
# agent_specs.yaml
agents:
  - id: agent_id
    role: "Agent Role"
    goal: "Agent Goal"
    backstory: "Agent Backstory"

    interface_contract:
      inputs:
        - name: input_name
          type: input_type
          description: input_description
          constraints: "constraints"

      outputs:
        - name: output_name
          type: output_type
          description: output_description

      errors:
        - code: ERROR_CODE
          condition: "error condition"

    tools: [tool_1, tool_2]
    delegation: false

# task_specs.yaml
tasks:
  - id: task_id
    description: "Task description with {placeholder}"
    agent: agent_id

    preconditions:
      - "Precondition 1"

    postconditions:
      - "Postcondition 1"

    input_schema:
      param1: "type"

    output_schema:
      result: "type"

    error_handling:
      - error: ERROR_CODE
        action: "handling strategy"
```

---

### **C. TDD Test Template**

```python
import pytest
from agents import MyAgent
from models import MyModel

class TestMyAgent:
    """Unit tests for MyAgent (TDD RED - should fail initially)"""

    @pytest.fixture
    def agent(self):
        return MyAgent(
            role="Agent Role",
            goal="Agent Goal",
            tools=[],
        )

    def test_happy_path(self, agent):
        """Test: Agent performs expected action"""
        # Given
        input_data = {"param": "value"}

        # When
        result = agent.execute(input_data)

        # Then
        assert result['status'] == 'success'
        assert result['data'] is not None

    def test_edge_case_invalid_input(self, agent):
        """Test: Agent handles invalid input gracefully"""
        # Given
        invalid_input = {"param": None}

        # When
        with pytest.raises(ValidationError) as exc_info:
            agent.execute(invalid_input)

        # Then
        assert "Invalid input" in str(exc_info.value)
```

---

### **D. Traceability Matrix Example**

```json
{
  "epic": "E-Commerce Platform",
  "story": "Product Catalog Management",
  "traceability": [
    {
      "feature_id": "product_listing",
      "feature_name": "Product Listing",
      "golden_data_ref": "golden_data.json:features[0]",

      "mapped_tasks": [
        {
          "task_id": "fetch_products_task",
          "task_file": "tasks.py:25-40"
        }
      ],

      "mapped_agents": [
        {
          "agent_id": "product_retrieval_agent",
          "agent_file": "agents.py:10-30"
        }
      ],

      "test_coverage": [
        {
          "test_file": "test_product_retrieval.py",
          "test_cases": [
            "test_fetch_products_valid_pagination",
            "test_fetch_products_empty_results",
            "test_fetch_products_invalid_page"
          ]
        }
      ],

      "implementation_status": "COMPLETE",
      "coverage_percentage": 92.5
    }
  ],

  "summary": {
    "total_features": 5,
    "implemented_features": 5,
    "implementation_rate": "100%",
    "average_coverage": 87.3
  }
}
```

---

## 11. GLOSSARY

- **BMAD**: Breakthrough Method of Agile AI Driven Development
- **CAAS**: CrewAI Agent Auto-generation System
- **Epic**: Large requirement (15-30 features)
- **Golden Data**: Structured, validated requirements
- **LLM Judge**: AI-powered quality evaluator
- **Party Mode**: Multi-agent collaborative review
- **SDD**: Spec-Driven Development
- **Story**: Medium requirement (3-7 features)
- **TDD**: Test-Driven Development
- **Traceability Matrix**: Feature → Task → Code mapping

---

## 12. CHANGE LOG

- **v1.0 (2026-02-14)**: Initial CAAS-E methodology release
  - Integrated CAAS 6-Phase + BMAD + SDD + TDD
  - Defined 7 human checkpoints
  - Established 3 iteration strategies
  - Created 4 enterprise patterns

---

**Document Status**: Production-Ready ✅
**Next Review**: 2026-05-01
**Feedback**: Submit issues to CAAS GitHub repository
