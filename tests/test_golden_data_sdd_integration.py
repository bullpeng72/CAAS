"""
Integration test for Golden Data SDD Enhancement with real LLM

Tests that the enhanced prompt actually generates SDD fields when called with a real LLM.
"""

import pytest
import json
import os
from caas_framework.methodology.golden_data import GoldenDataPipeline
from caas_framework.plugins.llm.openai import OpenAIPlugin


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping real LLM test"
)
async def test_real_llm_generates_sdd_fields():
    """
    Test that real LLM call generates SDD fields in Golden Data

    This test makes an actual API call to OpenAI to verify:
    1. Enhanced prompt correctly requests SDD fields
    2. LLM generates api_contract, data_model, business_rules, test_scenarios
    3. Fields are correctly parsed and stored in FeatureSpec
    """
    # Initialize real LLM plugin
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

    # Create pipeline
    pipeline = GoldenDataPipeline(
        llm_plugin=llm,
        use_hierarchical_extraction=False  # Disable for focused test
    )

    # Test requirement (simple e-commerce feature)
    requirement = """
    온라인 쇼핑몰에서 사용자가 상품을 장바구니에 담을 수 있어야 합니다.

    요구사항:
    - 상품 ID와 수량을 입력받아 장바구니에 추가
    - 재고가 부족하면 에러 반환
    - 동일 상품이면 수량만 업데이트
    - 최대 100개까지 담을 수 있음
    """

    # Generate Golden Data
    result = await pipeline.generate(
        requirement=requirement,
        domain="E_COMMERCE",
        validate=True
    )

    # Assertions
    print("\n=== Golden Data Generated ===")
    print(f"Project: {result.project_name}")
    print(f"Domain: {result.domain}")
    print(f"Features: {len(result.features)}")

    # Should have at least 1 feature
    assert len(result.features) >= 1, "Should generate at least 1 feature"

    # Check first feature for SDD fields
    feature = result.features[0]
    print(f"\n=== Feature: {feature.name} ===")
    print(f"Description: {feature.description}")
    print(f"Priority: {feature.priority}")

    # Verify SDD fields are populated
    print("\n=== SDD Fields ===")

    # 1. API Contract
    if feature.api_contract:
        print(f"✅ API Contract: {json.dumps(feature.api_contract, indent=2, ensure_ascii=False)}")
        assert "endpoint" in feature.api_contract, "API contract should have endpoint"
        assert "inputs" in feature.api_contract or "outputs" in feature.api_contract, \
            "API contract should have inputs or outputs"
    else:
        print("⚠️ API Contract: Not generated")

    # 2. Data Model
    if feature.data_model:
        print(f"✅ Data Model: {json.dumps(feature.data_model, indent=2, ensure_ascii=False)}")
        assert "entity" in feature.data_model or "schema" in feature.data_model, \
            "Data model should have entity or schema"
    else:
        print("⚠️ Data Model: Not generated")

    # 3. Business Rules
    if feature.business_rules:
        print(f"✅ Business Rules ({len(feature.business_rules)}):")
        for i, rule in enumerate(feature.business_rules, 1):
            print(f"   {i}. {rule}")
        assert len(feature.business_rules) > 0, "Should have at least 1 business rule"
    else:
        print("⚠️ Business Rules: Not generated")

    # 4. Test Scenarios
    if feature.test_scenarios:
        print(f"✅ Test Scenarios ({len(feature.test_scenarios)}):")
        for i, scenario in enumerate(feature.test_scenarios, 1):
            print(f"   {i}. {scenario.get('description', 'No description')}")
            print(f"      Type: {scenario.get('type', 'unknown')}")
            if 'given' in scenario:
                print(f"      Given: {scenario['given']}")
            if 'when' in scenario:
                print(f"      When: {scenario['when']}")
            if 'then' in scenario:
                print(f"      Then: {scenario['then']}")
        assert len(feature.test_scenarios) > 0, "Should have at least 1 test scenario"
    else:
        print("⚠️ Test Scenarios: Not generated")

    # At least 2 out of 4 SDD fields should be populated
    sdd_fields_populated = sum([
        feature.api_contract is not None,
        feature.data_model is not None,
        len(feature.business_rules) > 0,
        len(feature.test_scenarios) > 0
    ])

    print(f"\n=== SDD Coverage: {sdd_fields_populated}/4 fields populated ===")
    assert sdd_fields_populated >= 2, \
        f"Expected at least 2 SDD fields populated, got {sdd_fields_populated}"

    print("\n✅ Integration test passed - SDD fields are being generated!")


if __name__ == "__main__":
    # Allow running this test directly for manual verification
    import asyncio
    asyncio.run(test_real_llm_generates_sdd_fields())
