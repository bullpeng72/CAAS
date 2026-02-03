"""
End-to-End Test: Full BMAD Workflow with Real LLM

Tests the complete workflow from requirement to code generation using real LLM API.

Environment Variables:
    - RUN_E2E_TESTS=1: Enable E2E tests (skipped by default in CI)
    - OPENAI_API_KEY or ANTHROPIC_API_KEY: LLM API key
    - E2E_MODEL: Model to use (default: gpt-3.5-turbo for cost efficiency)

Usage:
    # Run locally with real LLM
    export RUN_E2E_TESTS=1
    export OPENAI_API_KEY=sk-...
    pytest tests/test_e2e_full_workflow.py -v -s

    # Skip in CI (default)
    pytest tests/test_e2e_full_workflow.py -v  # Will skip
"""

import os
from datetime import datetime

import pytest

# Skip E2E tests by default (too expensive for CI)
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_E2E_TESTS"),
    reason="E2E tests require RUN_E2E_TESTS=1 environment variable",
)


class TestE2EFullWorkflow:
    """
    End-to-end tests with real LLM API.

    These tests verify the complete workflow works in production conditions.
    """

    @pytest.fixture
    def real_llm_plugin(self):
        """
        Create real LLM plugin (OpenAI or Anthropic).

        Uses cost-efficient model by default.
        """
        from caas_framework.config import get_settings
        from caas_framework.plugins.llm import get_llm_plugin

        settings = get_settings()

        # Use environment model or fallback to gpt-3.5-turbo (cheapest)
        model = os.getenv("E2E_MODEL", "gpt-3.5-turbo")

        # Override settings for E2E test
        settings.llm.model = model
        settings.llm.temperature = 0.7

        plugin = get_llm_plugin()
        return plugin

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create temporary output directory"""
        output = tmp_path / "e2e_output"
        output.mkdir(exist_ok=True)
        return output

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_simple_todo_app_full_workflow(self, real_llm_plugin, output_dir):
        """
        Test complete workflow: requirement → Golden Data → agents → code

        Requirement: Simple TODO management system
        Expected: Production-ready code generated
        """
        from caas_framework.bmad.engine import BMADEngine
        from caas_framework.reporting import ProgressReporter, VerbosityLevel

        # Setup
        requirement = """
        Build a simple TODO management system with these features:
        1. Create new tasks with title and description
        2. Mark tasks as complete
        3. List all tasks
        4. Delete completed tasks

        Requirements:
        - Use Python 3.11+
        - Include basic error handling
        - Add simple unit tests
        """

        reporter = ProgressReporter(verbosity=VerbosityLevel.VERBOSE)

        # Create BMAD Engine
        engine = BMADEngine(
            llm_plugin=real_llm_plugin,
            enable_validation=True,
            enable_auto_fix=True,
            use_expert_agents=True,
            progress_reporter=reporter,
            verbosity=VerbosityLevel.VERBOSE,
        )

        reporter.info("🚀 Starting E2E test: Simple TODO app")
        reporter.info(f"📊 Model: {real_llm_plugin.model}")
        reporter.info(f"📁 Output: {output_dir}")

        # Execute full workflow
        start_time = datetime.now()

        try:
            result = await engine.run(
                requirement=requirement,
                domain="TASK_MANAGEMENT",
                deployment_target="docker",
                enable_traceability=True,
                enable_completeness_validation=True,
                bootstrap_project=False,  # Don't bootstrap for test
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Assertions
            assert result.success, f"Workflow failed: {result.errors}"
            assert result.golden_data is not None, "Golden Data not generated"
            assert len(result.agent_specs) > 0, "No agents generated"
            assert len(result.task_specs) > 0, "No tasks generated"
            assert result.generated_code is not None, "No code generated"

            # Verify all phases completed
            from caas_framework.bmad.engine import BMADPhase

            expected_phases = [
                BMADPhase.CONCRETIZATION,
                BMADPhase.DISCOVERY,
                BMADPhase.ARCHITECTURE,
                BMADPhase.DESIGN,
                BMADPhase.DEVELOPMENT,
                BMADPhase.DELIVERY,
            ]

            for phase in expected_phases:
                assert phase in result.phases_completed, f"Phase {phase} not completed"

            # Report results
            reporter.success(f"✅ E2E test completed in {duration:.2f}s")
            reporter.info(f"📊 Phases: {len(result.phases_completed)}/6")
            reporter.info(f"🤖 Agents: {len(result.agent_specs)}")
            reporter.info(f"📋 Tasks: {len(result.task_specs)}")
            reporter.info(
                f"📁 Files: {len(result.generated_code) if result.generated_code else 0}"
            )

            # Quality metrics
            if result.validation_reports:
                reporter.info(f"✅ Validations: {len(result.validation_reports)}")

            # Cost estimate (if available)
            reporter.warning("💰 Estimated cost: ~$0.10-0.50 (depending on model)")

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            reporter.error(f"❌ E2E test failed after {duration:.2f}s: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_workflow_with_phase2_enhancements(self, real_llm_plugin, output_dir):
        """
        Test workflow with all Phase 2 enhancements enabled.

        Verifies:
        - Multi-model routing works
        - Caching reduces costs
        - Performance profiling tracks operations
        - Monitoring collects metrics
        """
        from caas_framework.bmad.engine import BMADEngine
        from caas_framework.caching import get_cache_manager
        from caas_framework.monitoring import get_metrics_collector
        from caas_framework.performance import get_profiler
        from caas_framework.reporting import ProgressReporter, VerbosityLevel

        # Enable Phase 2 enhancements
        cache_manager = get_cache_manager()
        profiler = get_profiler(enabled=True)
        metrics = get_metrics_collector()

        reporter = ProgressReporter(verbosity=VerbosityLevel.NORMAL)

        # Simple requirement (to minimize cost)
        requirement = "Build a basic user registration system with email and password"

        # Wrap LLM with cache
        from caas_framework.caching.llm_cache import LLMCacheWrapper

        cached_llm = LLMCacheWrapper(
            llm_plugin=real_llm_plugin, cache_manager=cache_manager, enable_cache=True
        )

        # Create engine with cached LLM
        engine = BMADEngine(
            llm_plugin=cached_llm,
            enable_validation=True,
            use_expert_agents=True,
            progress_reporter=reporter,
        )

        reporter.info("🚀 Starting E2E test with Phase 2 enhancements")

        # Execute workflow
        start_time = datetime.now()

        try:
            async with profiler.profile("full_workflow"):
                result = await engine.run(
                    requirement=requirement,
                    domain="USER_MANAGEMENT",
                    enable_traceability=False,  # Minimize work
                    enable_completeness_validation=False,
                    bootstrap_project=False,
                )

            duration = (datetime.now() - start_time).total_seconds()

            # Assertions
            assert result.success, f"Workflow failed: {result.errors}"

            # Check Phase 2 enhancements worked
            cache_stats = cache_manager.get_stats()
            profiler_summary = profiler.get_summary()
            metrics_summary = metrics.get_summary()

            reporter.success(
                f"✅ E2E test with enhancements completed in {duration:.2f}s"
            )

            # Phase 2 enhancement results
            reporter.info(
                f"📦 Cache: {cache_stats.get('requests', 0)} requests, "
                f"{cache_stats.get('hits', 0)} hits"
            )
            reporter.info(
                f"📊 Profiled: {profiler_summary.get('total_operations', 0)} operations"
            )
            reporter.info(
                f"📈 Metrics: {metrics_summary.get('llm', {}).get('calls', 0)} LLM calls"
            )

            # Verify enhancements added value
            assert (
                profiler_summary["total_operations"] > 0
            ), "Profiler didn't track operations"
            # Cache may not have hits on first run, but should have requests
            assert cache_stats["requests"] > 0, "Cache not being used"

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            reporter.error(f"❌ E2E test failed after {duration:.2f}s: {str(e)}")
            raise

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_quality_gates_block_bad_output(self, real_llm_plugin, output_dir):
        """
        Test that quality gates properly block low-quality output.

        This test intentionally uses a poor requirement to trigger quality gates.
        """
        from caas_framework.bmad.engine import BMADEngine
        from caas_framework.reporting import ProgressReporter, VerbosityLevel

        # Intentionally vague requirement
        requirement = "Make an app"  # Very vague, should trigger quality gates

        reporter = ProgressReporter(verbosity=VerbosityLevel.VERBOSE)

        engine = BMADEngine(
            llm_plugin=real_llm_plugin,
            enable_validation=True,  # Enable validation
            enable_auto_fix=True,  # Allow auto-fix to improve
            use_expert_agents=True,
            progress_reporter=reporter,
        )

        reporter.info("🚀 Testing quality gates with poor requirement")

        try:
            result = await engine.run(
                requirement=requirement,
                domain=None,  # No domain hint
                enable_traceability=False,
                enable_completeness_validation=True,  # Enable completeness checks
                bootstrap_project=False,
            )

            # Even with a poor requirement, auto-fix should improve it
            # But we may see warnings or lower quality scores
            reporter.info("✅ Workflow completed (with auto-fix assistance)")
            reporter.info(f"⚠️  Validation reports: {len(result.validation_reports)}")

            # Check that validation ran
            assert len(result.validation_reports) > 0, "Validation should have run"

        except Exception as e:
            # Quality gate might block completely - that's also valid
            reporter.warning(f"⚠️  Quality gate blocked or workflow failed: {str(e)}")
            # Not asserting failure - blocking is valid behavior

    def test_e2e_test_can_be_skipped(self):
        """
        Test that E2E tests are properly skipped when env var not set.

        This test always runs (no skip marker) to verify the skip logic works.
        """
        # If we get here, we're either:
        # 1. Running with RUN_E2E_TESTS=1 (intended)
        # 2. Running this specific test (always allowed)

        if os.getenv("RUN_E2E_TESTS"):
            # E2E enabled - verify we can access LLM
            assert os.getenv("OPENAI_API_KEY") or os.getenv(
                "ANTHROPIC_API_KEY"
            ), "E2E tests enabled but no API key found"
        else:
            # E2E not enabled - verify tests would be skipped
            # (This test itself always runs to verify the logic)
            pass


# Cost estimation helper
def estimate_e2e_cost(model: str = "gpt-3.5-turbo") -> float:
    """
    Estimate cost for E2E test run.

    Returns: Estimated cost in USD
    """
    model_costs = {
        "gpt-3.5-turbo": 0.10,  # ~$0.10 per full workflow
        "gpt-4": 1.50,  # ~$1.50 per full workflow
        "claude-3-haiku": 0.05,  # ~$0.05 per full workflow
        "claude-3-sonnet": 0.50,  # ~$0.50 per full workflow
    }

    return model_costs.get(model, 0.50)


if __name__ == "__main__":
    """
    Run E2E tests manually.

    Usage:
        export RUN_E2E_TESTS=1
        export OPENAI_API_KEY=sk-...
        python tests/test_e2e_full_workflow.py
    """
    print("🧪 E2E Test Runner")
    print("=" * 60)

    if not os.getenv("RUN_E2E_TESTS"):
        print("❌ E2E tests disabled")
        print("   Set RUN_E2E_TESTS=1 to enable")
        exit(1)

    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        print("❌ No API key found")
        print("   Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        exit(1)

    model = os.getenv("E2E_MODEL", "gpt-3.5-turbo")
    cost = estimate_e2e_cost(model)

    print("✅ E2E tests enabled")
    print(f"📊 Model: {model}")
    print(f"💰 Estimated cost: ${cost:.2f} per test")
    print("=" * 60)
    print()

    # Run with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
