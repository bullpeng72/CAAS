"""
Test Golden Data Pipeline with Complete Spec-Driven Development Areas

Tests that all 6 core spec areas are properly populated:
1. Commands
2. Testing (existing)
3. Project Structure (existing)
4. Code Style
5. Git Workflow
6. Boundaries (CRITICAL for security)
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from caas_framework.bmad.golden_data import (
    RequirementConcretizer,
    GoldenDataPipeline
)
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    BoundariesSpec,
    CommandsSpec,
    CodeStyleSpec,
    GitWorkflowSpec
)
from caas_framework.plugins.llm.base import LLMPlugin, LLMResponse


class MockLLM(LLMPlugin):
    """Mock LLM for testing"""

    def __init__(self, mock_json_response: dict):
        super().__init__(name="mock", config={})
        self.mock_json_response = mock_json_response
        self._initialized = True

    async def initialize(self) -> None:
        self._initialized = True

    async def ainvoke(self, messages, **kwargs):
        """Return mock JSON response"""
        return LLMResponse(
            content=json.dumps(self.mock_json_response, ensure_ascii=False),
            model="mock",
            usage={"total_tokens": 100}
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        """Return mock JSON response as string"""
        return json.dumps(self.mock_json_response, ensure_ascii=False)

    async def stream(self, messages, **kwargs):
        """Return mock response as stream"""
        yield json.dumps(self.mock_json_response, ensure_ascii=False)

    async def close(self) -> None:
        pass


@pytest.fixture
def complete_golden_data_response():
    """Complete Golden Data response with all 6 spec areas"""
    return {
        "domain": "E-COMMERCE",
        "project_name": "온라인 쇼핑몰",
        "description": "사용자가 상품을 검색하고 구매할 수 있는 온라인 쇼핑몰",
        "features": [
            {
                "id": "F1",
                "name": "상품 검색",
                "description": "키워드로 상품을 검색할 수 있다",
                "priority": "high",
                "acceptance_criteria": [
                    "키워드 입력 시 관련 상품이 표시된다",
                    "검색 결과가 0.5초 이내에 표시된다"
                ]
            },
            {
                "id": "F2",
                "name": "장바구니",
                "description": "상품을 장바구니에 담을 수 있다",
                "priority": "critical",
                "acceptance_criteria": [
                    "상품을 장바구니에 추가할 수 있다",
                    "장바구니 수량을 변경할 수 있다"
                ]
            }
        ],
        "data_models": [
            {
                "entity_name": "Product",
                "attributes": ["name", "price", "stock"],
                "relationships": ["belongs to Category"]
            },
            {
                "entity_name": "Cart",
                "attributes": ["user_id", "items", "total_price"],
                "relationships": ["has many CartItem"]
            }
        ],
        "ui_components": [
            {
                "page_name": "상품 목록 페이지",
                "component_type": "table",
                "description": "상품 목록을 보여주는 테이블"
            },
            {
                "page_name": "장바구니 페이지",
                "component_type": "form",
                "description": "장바구니 내용을 보여주고 수정할 수 있는 폼"
            }
        ],
        "non_functional_requirements": {
            "security": "사용자 인증 및 결제 정보 암호화",
            "scalability": "동시 사용자 1000명 처리 가능",
            "performance": "페이지 로딩 시간 2초 이내",
            "reliability": "99.9% 가동률"
        },
        "workflow_type": "sequential",
        "deployment_target": "kubernetes",
        # ========== 6 Core Spec-Driven Development Areas ==========
        # 6. Boundaries (CRITICAL for security)
        "boundaries": {
            "always_allowed": [
                "데이터베이스 읽기",
                "상품 정보 조회",
                "사용자 정보 조회",
                "로깅 및 모니터링"
            ],
            "ask_first": [
                "데이터베이스 쓰기",
                "결제 API 호출",
                "이메일 발송",
                "외부 API 호출"
            ],
            "never_allowed": [
                "시스템 명령 실행",
                "파일 시스템 전체 삭제",
                "SQL 인젝션",
                "XSS 공격"
            ]
        },
        # 1. Commands
        "commands": {
            "install": "pip install -r requirements.txt",
            "test": "pytest tests/ -v --cov=src",
            "run": "uvicorn app.main:app --reload",
            "lint": "pylint src/ --rcfile=.pylintrc",
            "format": "black src/ && isort src/",
            "build": "docker build -t ecommerce:latest .",
            "deploy": "kubectl apply -f k8s/"
        },
        # 4. Code Style
        "code_style": {
            "formatter": "black",
            "line_length": 100,
            "use_type_hints": True,
            "docstring_style": "google",
            "import_order": "isort"
        },
        # 5. Git Workflow
        "git_workflow": {
            "branch_naming": "feature/{issue-number}-{description}",
            "commit_message_format": "feat(scope): subject",
            "requires_pr": True,
            "main_branch": "main"
        }
    }


@pytest.mark.asyncio
async def test_requirement_concretizer_with_all_specs(complete_golden_data_response):
    """Test that RequirementConcretizer populates all 6 spec areas"""

    # Arrange
    mock_llm = MockLLM(complete_golden_data_response)
    concretizer = RequirementConcretizer(llm_plugin=mock_llm)

    # Act
    golden_data = await concretizer.concretize(
        requirement="온라인 쇼핑몰을 만들어주세요",
        domain="E-COMMERCE"
    )

    # Assert - Basic fields
    assert golden_data.domain == "E-COMMERCE"
    assert golden_data.project_name == "온라인 쇼핑몰"
    assert "쇼핑몰" in golden_data.description

    # Assert - Features
    assert len(golden_data.features) == 2
    assert golden_data.features[0].name == "상품 검색"
    assert golden_data.features[1].name == "장바구니"

    # Assert - Data Models
    assert len(golden_data.data_models) == 2

    # Assert - UI Components
    assert len(golden_data.ui_components) == 2

    # Assert - Non-functional requirements
    assert "security" in golden_data.non_functional_requirements

    # ========== Assert 6 Core Spec Areas ==========

    # 6. BOUNDARIES (MOST CRITICAL)
    assert golden_data.boundaries is not None
    assert isinstance(golden_data.boundaries, BoundariesSpec)
    assert len(golden_data.boundaries.always_allowed) > 0
    assert "데이터베이스 읽기" in golden_data.boundaries.always_allowed
    assert len(golden_data.boundaries.ask_first) > 0
    assert "결제 API 호출" in golden_data.boundaries.ask_first
    assert len(golden_data.boundaries.never_allowed) > 0
    assert "시스템 명령 실행" in golden_data.boundaries.never_allowed

    # 1. COMMANDS
    assert golden_data.commands is not None
    assert isinstance(golden_data.commands, CommandsSpec)
    assert golden_data.commands.install == "pip install -r requirements.txt"
    assert golden_data.commands.test == "pytest tests/ -v --cov=src"
    assert golden_data.commands.run == "uvicorn app.main:app --reload"
    assert golden_data.commands.build == "docker build -t ecommerce:latest ."
    assert golden_data.commands.deploy == "kubectl apply -f k8s/"

    # 4. CODE STYLE
    assert golden_data.code_style is not None
    assert isinstance(golden_data.code_style, CodeStyleSpec)
    assert golden_data.code_style.formatter == "black"
    assert golden_data.code_style.line_length == 100
    assert golden_data.code_style.use_type_hints is True
    assert golden_data.code_style.docstring_style == "google"
    assert golden_data.code_style.import_order == "isort"

    # 5. GIT WORKFLOW
    assert golden_data.git_workflow is not None
    assert isinstance(golden_data.git_workflow, GitWorkflowSpec)
    assert golden_data.git_workflow.branch_naming == "feature/{issue-number}-{description}"
    assert golden_data.git_workflow.commit_message_format == "feat(scope): subject"
    assert golden_data.git_workflow.requires_pr is True
    assert golden_data.git_workflow.main_branch == "main"


@pytest.mark.asyncio
async def test_golden_data_pipeline_with_all_specs(complete_golden_data_response):
    """Test that GoldenDataPipeline generates complete Golden Data"""

    # Arrange
    mock_llm = MockLLM(complete_golden_data_response)
    pipeline = GoldenDataPipeline(
        llm_plugin=mock_llm,
        use_hierarchical_extraction=False  # Disable to avoid extra LLM calls
    )

    # Act
    golden_data = await pipeline.generate(
        requirement="온라인 쇼핑몰을 만들어주세요",
        domain="E-COMMERCE",
        validate=True
    )

    # Assert all 6 spec areas are populated
    assert golden_data.boundaries is not None
    assert golden_data.commands is not None
    assert golden_data.code_style is not None
    assert golden_data.git_workflow is not None

    # Verify boundaries has default values even if LLM doesn't provide them
    assert len(golden_data.boundaries.always_allowed) > 0
    assert len(golden_data.boundaries.ask_first) > 0
    assert len(golden_data.boundaries.never_allowed) > 0


@pytest.mark.asyncio
async def test_default_boundaries_when_llm_omits_them():
    """Test that default boundaries are set even when LLM doesn't provide them"""

    # Arrange - Response WITHOUT boundaries
    minimal_response = {
        "domain": "GENERAL",
        "project_name": "Simple App",
        "description": "A simple application",
        "features": [
            {
                "id": "F1",
                "name": "Basic Feature",
                "description": "A basic feature",
                "priority": "medium",
                "acceptance_criteria": ["It works"]
            }
        ],
        "data_models": [],
        "ui_components": [],
        "non_functional_requirements": {},
        "workflow_type": "sequential",
        "deployment_target": "docker"
        # NOTE: No boundaries, commands, code_style, git_workflow
    }

    mock_llm = MockLLM(minimal_response)
    concretizer = RequirementConcretizer(llm_plugin=mock_llm)

    # Act
    golden_data = await concretizer.concretize(
        requirement="Simple app",
        domain="GENERAL"
    )

    # Assert - Default boundaries should be set
    assert golden_data.boundaries is not None
    assert len(golden_data.boundaries.always_allowed) == 3  # Default values
    assert "읽기 작업" in golden_data.boundaries.always_allowed
    assert len(golden_data.boundaries.ask_first) == 4  # Default values
    assert "파일 작업" in golden_data.boundaries.ask_first
    assert len(golden_data.boundaries.never_allowed) == 4  # Default values
    assert "시스템 명령 실행" in golden_data.boundaries.never_allowed

    # Assert - Default commands should be set
    assert golden_data.commands is not None
    assert golden_data.commands.install == "pip install -r requirements.txt"
    assert golden_data.commands.test == "pytest tests/"

    # Assert - Default code style should be set
    assert golden_data.code_style is not None
    assert golden_data.code_style.formatter == "black"
    assert golden_data.code_style.line_length == 88

    # Assert - Default git workflow should be set
    assert golden_data.git_workflow is not None
    assert golden_data.git_workflow.main_branch == "main"


@pytest.mark.asyncio
async def test_security_boundaries_are_enforced():
    """Test that security boundaries are ALWAYS set (never None)"""

    # Arrange - Even with empty response
    empty_response = {
        "domain": "GENERAL",
        "project_name": "Test",
        "description": "Test",
        "features": []
    }

    mock_llm = MockLLM(empty_response)
    concretizer = RequirementConcretizer(llm_plugin=mock_llm)

    # Act
    golden_data = await concretizer.concretize("test", "GENERAL")

    # Assert - Boundaries MUST be set (security critical)
    assert golden_data.boundaries is not None, "Boundaries must NEVER be None (security critical)"
    assert len(golden_data.boundaries.never_allowed) > 0, "Must have forbidden operations"
    assert any("rm -rf" in op or "삭제" in op for op in golden_data.boundaries.never_allowed), \
        "Must forbid dangerous file operations"
    assert any("명령 실행" in op or "코드 실행" in op for op in golden_data.boundaries.never_allowed), \
        "Must forbid arbitrary code execution"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
