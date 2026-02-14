"""
CAAS-E Integration Test (Week 2 Part 3)

Tests integration of all CAAS-E components:
- Story Decomposition (Week 1)
- Golden Data SDD (Week 2 Part 2)
- Party Mode Review (Week 2 Part 1)

This test uses mocked LLM responses for fast, deterministic testing.
"""

import pytest
import json
import os
from unittest.mock import AsyncMock, Mock
from caas_framework.methodology.story_decomposer import StoryDecomposer, Epic, Story
from caas_framework.methodology.golden_data import GoldenDataPipeline
from caas_framework.agents.party_mode_coordinator import (
    PartyModeCoordinator,
    PartyModeResult,
    ReviewPerspective
)
from caas_framework.models.specifications import ConcretizedRequirement, FeatureSpec, SystemScope
from caas_framework.plugins.llm.openai import OpenAIPlugin


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin"""
    llm = Mock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.mark.asyncio
async def test_story_decomposition_to_sdd_golden_data(mock_llm):
    """
    Test Step 1-2: Story Decomposition → Golden Data with SDD

    Workflow:
    1. Decompose requirement into stories (mocked)
    2. Generate Golden Data with SDD fields for first story
    """
    print("\n=== Test: Story → Golden Data with SDD ===\n")

    # Create a mock epic (simulates story decomposition result)
    mock_story = Story(
        id="S1",
        name="User Authentication System",
        description="Complete user authentication with registration, login, and password reset",
        features=["feature_1", "feature_2", "feature_3"],
        dependencies=[],
        estimated_complexity="medium",
        acceptance_criteria=[
            "Users can register with email verification",
            "Users can login securely",
            "Password reset works via email"
        ],
        business_value="high"
    )

    mock_epic = Epic(
        name="E-Commerce Platform",
        description="Full e-commerce platform with auth, products, and checkout",
        estimated_features=12,
        recommended_stories=3,
        stories=[mock_story],
        business_value="high"
    )

    print(f"✅ Story: {mock_story.name}")
    print(f"   Features: {len(mock_story.features)}")

    # Phase 2: Generate Golden Data with SDD from story
    mock_llm.ainvoke.return_value = Mock(content=json.dumps({
        "domain": "E_COMMERCE",
        "project_name": "Authentication System",
        "description": "User authentication module",
        "features": [
            {
                "id": "F1",
                "name": "사용자 회원가입",
                "description": "이메일과 비밀번호로 회원가입",
                "priority": "high",
                "acceptance_criteria": ["이메일 검증", "비밀번호 강도 체크"],
                "api_contract": {
                    "endpoint": "POST /api/auth/register",
                    "inputs": {"email": "string", "password": "string"},
                    "outputs": {"user_id": "UUID", "status": "string"},
                    "error_cases": ["400: Invalid email", "409: Email exists"]
                },
                "data_model": {
                    "entity": "User",
                    "schema": {"id": "UUID", "email": "string", "password_hash": "string"},
                    "validation_rules": ["Email must be unique"]
                },
                "business_rules": ["비밀번호는 bcrypt로 해싱"],
                "test_scenarios": [
                    {
                        "type": "unit",
                        "description": "정상 회원가입",
                        "given": "유효한 이메일과 비밀번호",
                        "when": "회원가입 API 호출",
                        "then": "사용자 계정 생성"
                    }
                ]
            }
        ],
        "data_models": [],
        "ui_components": [],
        "non_functional_requirements": {},
        "workflow_type": "sequential",
        "deployment_target": "docker"
    }))

    pipeline = GoldenDataPipeline(llm_plugin=mock_llm, use_hierarchical_extraction=False)
    golden_data = await pipeline.generate(
        requirement=mock_story.description,
        domain="E_COMMERCE",
        validate=True
    )

    # Verify Golden Data with SDD fields
    assert len(golden_data.features) == 1
    feature = golden_data.features[0]

    print(f"✅ Golden Data: {golden_data.project_name}")
    print(f"   Feature: {feature.name}")
    print(f"   SDD Fields:")
    print(f"     - API Contract: {'✓' if feature.api_contract else '✗'}")
    print(f"     - Data Model: {'✓' if feature.data_model else '✗'}")
    print(f"     - Business Rules: {len(feature.business_rules)}")
    print(f"     - Test Scenarios: {len(feature.test_scenarios)}")

    assert feature.api_contract is not None
    assert feature.data_model is not None
    assert len(feature.business_rules) > 0
    assert len(feature.test_scenarios) > 0

    print("\n✅ Step 1-2 Integration: Story → SDD Golden Data PASSED\n")
    return golden_data


@pytest.mark.asyncio
async def test_sdd_golden_data_to_party_mode_review(mock_llm):
    """
    Test Step 2-3: Golden Data with SDD → Party Mode Review

    Workflow:
    1. Create Golden Data with SDD fields (mocked)
    2. Review using Party Mode (5 agents)
    """
    print("\n=== Test: SDD Golden Data → Party Mode Review ===\n")

    # Create mock Golden Data with SDD fields
    feature_with_sdd = FeatureSpec(
        id="F1",
        name="사용자 회원가입",
        description="이메일과 비밀번호로 회원가입",
        priority="high",
        acceptance_criteria=["이메일 검증", "비밀번호 강도 체크"],
        api_contract={
            "endpoint": "POST /api/auth/register",
            "inputs": {"email": "string", "password": "string"},
            "outputs": {"user_id": "UUID"},
            "error_cases": ["400: Invalid email"]
        },
        data_model={
            "entity": "User",
            "schema": {"id": "UUID", "email": "string"},
            "validation_rules": ["Email must be unique"]
        },
        business_rules=["비밀번호는 bcrypt로 해싱"],
        test_scenarios=[
            {
                "type": "unit",
                "description": "정상 회원가입",
                "given": "유효한 이메일",
                "when": "회원가입 호출",
                "then": "계정 생성"
            }
        ]
    )

    golden_data = ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="Authentication System",
            purpose="User authentication"
        ),
        features=[feature_with_sdd],
        domain="E_COMMERCE"
    )

    print(f"✅ Golden Data: {golden_data.project_name}")
    print(f"   Features: {len(golden_data.features)}")
    print(f"   SDD Coverage: 4/4 (api_contract, data_model, business_rules, test_scenarios)")

    # Phase 3: Party Mode Review (5 agents approve)
    mock_reviews = [
        # Agent 1-5: All approve with high scores
        Mock(content=json.dumps({
            "dimension_scores": [
                {"dimension": "completeness", "score": 8.0 + i * 0.2, "reasoning": "Good"},
                {"dimension": "feasibility", "score": 8.0 + i * 0.2, "reasoning": "Good"},
                {"dimension": "scalability", "score": 8.0 + i * 0.2, "reasoning": "Good"},
                {"dimension": "maintainability", "score": 8.0 + i * 0.2, "reasoning": "Good"},
                {"dimension": "security", "score": 8.0 + i * 0.2, "reasoning": "Good"}
            ],
            "feedback": f"Agent {i+1} approves",
            "critical_issues": [],
            "warnings": []
        }))
        for i in range(5)
    ]

    mock_llm.ainvoke.side_effect = mock_reviews

    coordinator = PartyModeCoordinator(
        llm_plugin=mock_llm,
        party_size=5,
        approval_threshold=6.0,
        consensus_threshold=0.6
    )

    artifact = {
        "type": "golden_data",
        "project_name": golden_data.project_name,
        "features": [feature_with_sdd.model_dump()]
    }

    review_result = await coordinator.review_artifact(
        artifact=artifact,
        artifact_type="golden_data",
        phase="concretization",
        perspectives=[ReviewPerspective.REQUIREMENTS, ReviewPerspective.ARCHITECTURE,
                     ReviewPerspective.SECURITY, ReviewPerspective.QUALITY, ReviewPerspective.DESIGN]
    )

    # Verify Party Mode results
    approved_count = sum(1 for r in review_result.reviews if r.approved)

    print(f"✅ Party Mode Review:")
    print(f"   Agents: {len(review_result.reviews)}")
    print(f"   Approved: {approved_count}/5 ({review_result.approval_rate*100:.0f}%)")
    print(f"   Consensus: {review_result.consensus_score:.2f}/10.0")
    print(f"   Critical Issues: {len(review_result.critical_issues)}")
    print(f"   Result: {'APPROVED' if review_result.approved else 'REJECTED'}")

    assert len(review_result.reviews) == 5
    assert approved_count == 5  # All approved
    assert review_result.approval_rate == 1.0
    assert review_result.approved is True
    assert review_result.consensus_score >= 8.0

    print("\n✅ Step 2-3 Integration: SDD Golden Data → Party Mode PASSED\n")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping real LLM test"
)
async def test_full_caas_e_workflow_real_llm():
    """
    Real LLM test for full CAAS-E workflow (optional)

    WARNING: Makes multiple API calls (~60-90 seconds)

    Workflow:
    1. Story Decomposition: Epic → Stories
    2. Golden Data SDD: Story → Features with SDD fields
    3. Party Mode: 5-agent collaborative review
    """
    print("\n" + "="*70)
    print("🚀 CAAS-E Full Workflow - Real LLM Test")
    print("="*70)
    print("⚠️  Makes ~10 OpenAI API calls, takes 60-90 seconds\n")

    # Initialize real LLM
    llm = OpenAIPlugin(
        name="openai",
        config={
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 4000
        }
    )
    await llm.initialize()

    requirement = """
    간단한 할일 관리 시스템을 만들어주세요.

    기능:
    - 할일 추가, 수정, 삭제
    - 할일 완료 표시
    - 할일 목록 조회
    """

    # Phase 1: Story Decomposition
    print("📋 Phase 1: Story Decomposition")
    decomposer = StoryDecomposer(llm_plugin=llm)
    epic = await decomposer.decompose_epic(requirement, domain_hint="TASK_MANAGEMENT")
    print(f"✅ Epic: {epic.name} ({len(epic.stories)} stories)")

    # Phase 2: Golden Data SDD
    print("\n🎯 Phase 2: Golden Data SDD")
    pipeline = GoldenDataPipeline(llm_plugin=llm, use_hierarchical_extraction=False)
    golden_data = await pipeline.generate(
        requirement=epic.stories[0].description if epic.stories else requirement,
        domain="TASK_MANAGEMENT",
        validate=True
    )
    print(f"✅ Golden Data: {len(golden_data.features)} features")

    # Check SDD coverage
    sdd_coverage = sum([
        golden_data.features[0].api_contract is not None,
        golden_data.features[0].data_model is not None,
        len(golden_data.features[0].business_rules) > 0,
        len(golden_data.features[0].test_scenarios) > 0
    ]) if golden_data.features else 0
    print(f"   SDD Coverage: {sdd_coverage}/4")

    # Phase 3: Party Mode Review
    print("\n👥 Phase 3: Party Mode Review")
    coordinator = PartyModeCoordinator(llm_plugin=llm, party_size=5)
    artifact = {
        "type": "golden_data",
        "features": [f.model_dump() for f in golden_data.features]
    }

    review_result = await coordinator.review_artifact(
        artifact=artifact,
        artifact_type="golden_data",
        phase="concretization"
    )

    approved_count = sum(1 for r in review_result.reviews if r.approved)
    print(f"✅ Review: {approved_count}/5 approved ({review_result.consensus_score:.2f}/10.0)")

    # Verify workflow
    print("\n🎊 Workflow Complete!")
    print("="*70)
    assert len(epic.stories) >= 1
    assert len(golden_data.features) >= 1
    assert len(review_result.reviews) == 5
    print("✅ All phases completed successfully\n")


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_caas_e_integration.py -v -s
    pass
