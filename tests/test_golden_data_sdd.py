"""
Tests for Golden Data SDD (Spec-Driven Development) Enhancement (CAAS-E Week 2)

Tests the enhanced FeatureSpec model with SDD fields:
- api_contract: API endpoint specifications
- data_model: Entity schema with validation
- business_rules: Explicit business rules
- test_scenarios: Given-When-Then test cases
"""

import pytest
from unittest.mock import AsyncMock, Mock
from caas_framework.methodology.golden_data import (
    RequirementConcretizer,
    GoldenDataPipeline
)
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec
)


class TestFeatureSpecSDDFields:
    """Test FeatureSpec model with SDD fields"""

    def test_feature_spec_with_all_sdd_fields(self):
        """Test creating FeatureSpec with all SDD fields populated"""
        feature = FeatureSpec(
            id="F1",
            name="User Registration",
            description="User can register with email and password",
            priority="high",
            acceptance_criteria=["Email validation", "Password strength check"],
            api_contract={
                "endpoint": "POST /api/users/register",
                "inputs": {
                    "email": "string (required, valid email format)",
                    "password": "string (required, min: 8 chars)"
                },
                "outputs": {
                    "user_id": "UUID",
                    "status": "string (success|error)"
                },
                "error_cases": [
                    "400: Invalid email format",
                    "409: Email already exists"
                ]
            },
            data_model={
                "entity": "User",
                "schema": {
                    "id": "UUID (primary key)",
                    "email": "string (unique, required, max: 255)",
                    "password_hash": "string (required)",
                    "created_at": "datetime (auto)"
                },
                "validation_rules": [
                    "Email must be unique",
                    "Password must be hashed with bcrypt"
                ]
            },
            business_rules=[
                "Users must verify email within 24 hours",
                "Duplicate emails are not allowed",
                "Passwords must contain uppercase, lowercase, and numbers"
            ],
            test_scenarios=[
                {
                    "type": "unit",
                    "description": "Valid registration",
                    "given": "Valid email and strong password",
                    "when": "User submits registration form",
                    "then": "User account is created and verification email sent"
                },
                {
                    "type": "edge_case",
                    "description": "Duplicate email",
                    "given": "Email already exists in database",
                    "when": "User tries to register with existing email",
                    "then": "Return 409 error with 'Email already exists' message"
                }
            ]
        )

        # Assert all SDD fields are correctly stored
        assert feature.api_contract is not None
        assert feature.api_contract["endpoint"] == "POST /api/users/register"
        assert "email" in feature.api_contract["inputs"]
        assert len(feature.api_contract["error_cases"]) == 2

        assert feature.data_model is not None
        assert feature.data_model["entity"] == "User"
        assert "id" in feature.data_model["schema"]
        assert len(feature.data_model["validation_rules"]) == 2

        assert len(feature.business_rules) == 3
        assert "must verify email" in feature.business_rules[0]

        assert len(feature.test_scenarios) == 2
        assert feature.test_scenarios[0]["type"] == "unit"
        assert "given" in feature.test_scenarios[0]

    def test_feature_spec_without_sdd_fields(self):
        """Test backward compatibility - FeatureSpec without SDD fields"""
        feature = FeatureSpec(
            id="F2",
            name="Simple Feature",
            description="Basic feature without SDD",
            priority="low",
            acceptance_criteria=["Works correctly"]
        )

        # Assert SDD fields default to None or empty
        assert feature.api_contract is None
        assert feature.data_model is None
        assert feature.business_rules == []
        assert feature.test_scenarios == []

    def test_business_rules_string_to_list_conversion(self):
        """Test business_rules validator converts string to list"""
        # This should work due to convert_strings_to_lists validator
        feature = FeatureSpec(
            id="F3",
            name="Test Feature",
            description="Test string conversion",
            business_rules="Single business rule"  # String input
        )

        # Should be converted to list
        assert isinstance(feature.business_rules, list)
        assert len(feature.business_rules) == 1
        assert feature.business_rules[0] == "Single business rule"


class TestGoldenDataSDDGeneration:
    """Test Golden Data generation with SDD fields"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM plugin"""
        llm = Mock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def concretizer(self, mock_llm):
        """Create RequirementConcretizer instance"""
        return RequirementConcretizer(llm_plugin=mock_llm)

    @pytest.mark.asyncio
    async def test_concretize_with_sdd_fields(self, concretizer, mock_llm):
        """Test concretization extracts SDD fields from LLM response"""
        # Mock LLM response with SDD fields
        mock_response = Mock(content='''
{
  "domain": "E_COMMERCE",
  "project_name": "온라인 쇼핑몰",
  "description": "사용자가 상품을 검색하고 구매할 수 있는 시스템",
  "features": [
    {
      "id": "F1",
      "name": "상품 검색",
      "description": "키워드로 상품 검색",
      "priority": "high",
      "acceptance_criteria": ["검색 결과가 1초 이내에 표시됨", "관련도 순으로 정렬"],
      "api_contract": {
        "endpoint": "GET /api/products/search",
        "inputs": {
          "keyword": "string (required, min: 2 chars)",
          "page": "int (optional, default: 1)",
          "limit": "int (optional, default: 20, max: 100)"
        },
        "outputs": {
          "products": "array of Product objects",
          "total_count": "int",
          "page": "int"
        },
        "error_cases": [
          "400: Keyword too short",
          "500: Search service unavailable"
        ]
      },
      "data_model": {
        "entity": "Product",
        "schema": {
          "id": "UUID (primary key)",
          "name": "string (required, max: 200)",
          "description": "text",
          "price": "decimal (required, min: 0)",
          "stock": "int (required, min: 0)",
          "created_at": "datetime (auto)"
        },
        "validation_rules": [
          "Price must be positive",
          "Stock cannot be negative"
        ]
      },
      "business_rules": [
        "Search results are cached for 5 minutes",
        "Out-of-stock products appear last in results",
        "Premium products are boosted in relevance score"
      ],
      "test_scenarios": [
        {
          "type": "unit",
          "description": "검색어로 상품 찾기",
          "given": "데이터베이스에 '노트북' 상품 10개 존재",
          "when": "사용자가 '노트북' 키워드로 검색",
          "then": "10개 상품이 관련도 순으로 반환됨"
        },
        {
          "type": "edge_case",
          "description": "검색어가 너무 짧음",
          "given": "검색어 길이가 1자",
          "when": "검색 API 호출",
          "then": "400 에러와 'Keyword too short' 메시지 반환"
        }
      ]
    }
  ],
  "data_models": [],
  "ui_components": [],
  "non_functional_requirements": {},
  "workflow_type": "sequential",
  "deployment_target": "docker",
  "boundaries": {
    "always_allowed": ["읽기 작업", "검색", "로깅"],
    "ask_first": ["데이터베이스 변경", "외부 API 호출"],
    "never_allowed": ["시스템 명령 실행", "임의 코드 실행"]
  },
  "commands": {
    "install": "pip install -r requirements.txt",
    "test": "pytest tests/",
    "run": "python main.py"
  },
  "code_style": {
    "formatter": "black",
    "line_length": 88,
    "use_type_hints": true,
    "docstring_style": "google"
  },
  "git_workflow": {
    "branch_naming": "feature/{issue-number}-{description}",
    "commit_message_format": "<type>(<scope>): <subject>",
    "requires_pr": true,
    "main_branch": "main"
  }
}
        ''')

        mock_llm.ainvoke.return_value = mock_response

        # Execute concretization
        result = await concretizer.concretize(
            requirement="온라인 쇼핑몰에서 상품을 검색하고 구매할 수 있어야 함",
            domain="E_COMMERCE"
        )

        # Assert ConcretizedRequirement structure
        assert isinstance(result, ConcretizedRequirement)
        assert result.domain == "E_COMMERCE"
        assert len(result.features) == 1

        # Assert FeatureSpec has SDD fields
        feature = result.features[0]
        assert feature.id == "F1"
        assert feature.name == "상품 검색"

        # Assert api_contract
        assert feature.api_contract is not None
        assert feature.api_contract["endpoint"] == "GET /api/products/search"
        assert "keyword" in feature.api_contract["inputs"]
        assert "products" in feature.api_contract["outputs"]
        assert len(feature.api_contract["error_cases"]) == 2

        # Assert data_model
        assert feature.data_model is not None
        assert feature.data_model["entity"] == "Product"
        assert "id" in feature.data_model["schema"]
        assert "price" in feature.data_model["schema"]
        assert len(feature.data_model["validation_rules"]) == 2

        # Assert business_rules
        assert len(feature.business_rules) == 3
        assert "cached for 5 minutes" in feature.business_rules[0]

        # Assert test_scenarios
        assert len(feature.test_scenarios) == 2
        assert feature.test_scenarios[0]["type"] == "unit"
        assert "노트북" in feature.test_scenarios[0]["given"]
        assert feature.test_scenarios[1]["type"] == "edge_case"

    @pytest.mark.asyncio
    async def test_concretize_with_missing_sdd_fields(self, concretizer, mock_llm):
        """Test concretization handles missing SDD fields gracefully"""
        # Mock LLM response WITHOUT SDD fields (backward compatibility)
        mock_response = Mock(content='''
{
  "domain": "GENERAL",
  "project_name": "Simple App",
  "description": "A simple application",
  "features": [
    {
      "id": "F1",
      "name": "Basic Feature",
      "description": "Simple feature without SDD",
      "priority": "medium",
      "acceptance_criteria": ["Works correctly"]
    }
  ],
  "data_models": [],
  "ui_components": [],
  "non_functional_requirements": {},
  "workflow_type": "sequential",
  "deployment_target": "docker"
}
        ''')

        mock_llm.ainvoke.return_value = mock_response

        # Execute concretization
        result = await concretizer.concretize(
            requirement="Create a simple app",
            domain="GENERAL"
        )

        # Assert feature exists but SDD fields are None/empty
        feature = result.features[0]
        assert feature.id == "F1"
        assert feature.api_contract is None
        assert feature.data_model is None
        assert feature.business_rules == []
        assert feature.test_scenarios == []

    @pytest.mark.asyncio
    async def test_golden_data_pipeline_with_sdd(self, mock_llm):
        """Test full GoldenDataPipeline generates SDD fields"""
        # Mock LLM response
        mock_response = Mock(content='''
{
  "domain": "HEALTHCARE",
  "project_name": "환자 관리 시스템",
  "description": "병원에서 환자 정보를 관리하는 시스템",
  "features": [
    {
      "id": "F1",
      "name": "환자 등록",
      "description": "새로운 환자를 시스템에 등록",
      "priority": "critical",
      "acceptance_criteria": ["환자 정보 검증", "중복 방지"],
      "api_contract": {
        "endpoint": "POST /api/patients",
        "inputs": {
          "name": "string (required)",
          "birth_date": "date (required)",
          "ssn": "string (required, unique)"
        },
        "outputs": {
          "patient_id": "UUID",
          "status": "string"
        },
        "error_cases": ["400: Invalid SSN", "409: Patient already exists"]
      },
      "data_model": {
        "entity": "Patient",
        "schema": {
          "id": "UUID (primary key)",
          "name": "string (required)",
          "birth_date": "date (required)",
          "ssn": "string (unique, encrypted)"
        },
        "validation_rules": ["SSN must be valid format", "Birth date cannot be future"]
      },
      "business_rules": [
        "환자 정보는 HIPAA 규정 준수",
        "SSN은 암호화하여 저장",
        "중복 등록 시 기존 환자 ID 반환"
      ],
      "test_scenarios": [
        {
          "type": "integration",
          "description": "정상 환자 등록",
          "given": "유효한 환자 정보",
          "when": "POST /api/patients 호출",
          "then": "환자 ID 반환 및 데이터베이스 저장"
        }
      ]
    }
  ],
  "data_models": [],
  "ui_components": [],
  "non_functional_requirements": {
    "security": "HIPAA compliance required"
  },
  "workflow_type": "sequential",
  "deployment_target": "kubernetes"
}
        ''')

        mock_llm.ainvoke.return_value = mock_response

        # Create pipeline
        pipeline = GoldenDataPipeline(
            llm_plugin=mock_llm,
            use_hierarchical_extraction=False  # Disable for this test
        )

        # Execute pipeline
        result = await pipeline.generate(
            requirement="병원 환자 관리 시스템",
            domain="HEALTHCARE",
            validate=True
        )

        # Assert SDD fields are present
        feature = result.features[0]
        assert feature.api_contract is not None
        assert feature.api_contract["endpoint"] == "POST /api/patients"
        assert feature.data_model is not None
        assert feature.data_model["entity"] == "Patient"
        assert "HIPAA" in feature.business_rules[0]
        assert len(feature.test_scenarios) == 1


class TestSDDFieldsIntegration:
    """Test SDD fields integration with other components"""

    def test_sdd_fields_serialization(self):
        """Test SDD fields can be serialized to dict/JSON"""
        feature = FeatureSpec(
            id="F1",
            name="Test",
            description="Test feature",
            api_contract={"endpoint": "GET /test"},
            data_model={"entity": "Test", "schema": {"id": "UUID"}},
            business_rules=["Rule 1", "Rule 2"],
            test_scenarios=[{"type": "unit", "description": "Test"}]
        )

        # Serialize to dict
        feature_dict = feature.model_dump()

        # Assert SDD fields are in dict
        assert "api_contract" in feature_dict
        assert "data_model" in feature_dict
        assert "business_rules" in feature_dict
        assert "test_scenarios" in feature_dict

        # Assert can be deserialized back
        feature_restored = FeatureSpec(**feature_dict)
        assert feature_restored.api_contract == feature.api_contract
        assert feature_restored.data_model == feature.data_model

    def test_concretized_requirement_with_sdd_features(self):
        """Test ConcretizedRequirement with SDD-enhanced features"""
        from caas_framework.models.specifications import SystemScope

        feature_with_sdd = FeatureSpec(
            id="F1",
            name="User Login",
            description="Authenticate user",
            api_contract={
                "endpoint": "POST /api/auth/login",
                "inputs": {"username": "string", "password": "string"},
                "outputs": {"token": "JWT"}
            },
            business_rules=["Max 3 failed attempts"],
            test_scenarios=[{"type": "unit", "description": "Valid login"}]
        )

        golden_data = ConcretizedRequirement(
            system_scope=SystemScope(
                project_name="Auth System",
                purpose="User authentication"
            ),
            features=[feature_with_sdd],
            domain="SECURITY"
        )

        # Assert features are accessible
        assert len(golden_data.features) == 1
        assert golden_data.features[0].api_contract is not None
        assert len(golden_data.features[0].business_rules) == 1
