"""
Analyze Gaps Command

요구사항 갭 분석 명령 - caas_framework를 직접 사용
"""

import asyncio

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    handle_keyboard_interrupt,
)


@click.command()
@click.argument("requirement")
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    required=True,
    help="[Phase 0] Golden Data JSON file to analyze against",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output JSON file path for gap analysis results (default: gaps.json)",
)
@handle_keyboard_interrupt
def analyze_gaps(requirement, golden_data, output):
    """
    \b
    [Phase 0] Analyze requirement gaps against Golden Data

    \b
    🔍 WHAT IT DOES:
    ═══════════════════════════════════════════════════════════════════════════
    Compares user requirements with Golden Data to identify:
    • Missing features (기능 누락)
    • Ambiguous specifications (모호한 요구사항)
    • Incomplete data models (불완전한 데이터 모델)
    • Missing non-functional requirements (비기능 요구사항 누락)
    • UI/UX specification gaps (UI/UX 명세 부족)

    \b
    📊 OUTPUT:
    ═══════════════════════════════════════════════════════════════════════════
    Generates gaps.json containing:
    • gap_type: Type of gap (missing_feature, ambiguous, etc.)
    • severity: low, medium, high, critical
    • description: Detailed gap description
    • suggestions: Recommendations to fill the gap
    • affected_areas: Which parts are affected

    \b
    💡 TYPICAL WORKFLOW:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Generate initial code:
       $ caas generate "Build a task management app" -o ./output

    \b
    2️⃣  Analyze gaps in your requirement:
       $ caas analyze-gaps "task management app" \\
           --golden-data ./output/golden_data.json \\
           --output gaps.json

    \b
    3️⃣  Review gaps and decide:
       • Use 'caas expand' to auto-fill gaps
       • Use 'caas questions' for interactive clarification

    \b
    📋 EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Basic gap analysis:
       $ caas analyze-gaps "할일 관리 앱" --golden-data golden.json

    \b
    2️⃣  Save results to specific file:
       $ caas analyze-gaps "E-commerce platform" \\
           -g golden.json \\
           -o ecommerce_gaps.json

    \b
    3️⃣  Analyze complex requirements:
       $ caas analyze-gaps "Healthcare patient management system with AI diagnosis" \\
           --golden-data ./healthcare_golden.json

    \b
    📚 See also:
       caas expand --help        (Auto-fill gaps)
       caas questions --help     (Interactive gap filling)
    """
    import json
    from pathlib import Path

    from caas_framework.models.specifications import ConcretizedRequirement
    from caas_framework.plugins.llm.openai import OpenAIPlugin
    from caas_framework.refinement import RequirementGapAnalyzer

    # Load golden data
    try:
        with open(golden_data, "r", encoding="utf-8") as f:
            golden_data_dict = json.load(f)

        # Convert to ConcretizedRequirement
        concretized = ConcretizedRequirement(**golden_data_dict)
    except Exception as e:
        echo_error(f"Failed to load golden data: {e}")
        return

    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║                  CAAS Gap Analysis                            ║
║            (Using caas_framework directly)                   ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    echo_info(f"Requirement: {requirement}")
    echo_info(f"Golden Data: {golden_data}")
    click.echo()

    try:
        # Initialize LLM plugin
        async def run_analysis():
            import os
            from caas_framework.config.loader import load_config
            cfg = load_config()
            llm_plugin = OpenAIPlugin(
                name="openai-analyze-gaps",
                config={
                    "model": cfg.llm.model,
                    "api_key": cfg.llm.api_key or os.environ.get("OPENAI_API_KEY"),
                    "temperature": cfg.llm.temperature,
                    "max_tokens": cfg.llm.max_tokens,
                },
            )
            await llm_plugin.initialize()

            # Create gap analyzer
            analyzer = RequirementGapAnalyzer(llm_client=llm_plugin)

            # Run analysis
            result = analyzer.analyze_gaps(requirement, concretized)

            await llm_plugin.close()
            return result

        # Run async analysis
        result = asyncio.run(run_analysis())

        # Display results
        click.echo(click.style("Gap Analysis Results:", bold=True))
        click.echo()

        # Metrics
        click.echo(f"  전체 갭:        {result.total_gaps}")
        click.echo(f"  Critical:       {result.critical_gaps}")
        click.echo(f"  High:           {result.high_gaps}")
        click.echo(f"  Medium:         {result.medium_gaps}")
        click.echo(f"  Low:            {result.low_gaps}")
        click.echo(f"  자동 수정 가능: {result.auto_fixable_gaps}")
        click.echo(f"  완성도:         {result.completeness_score:.1%}")
        click.echo()

        # Gaps detail
        if result.gaps:
            click.echo(click.style("탐지된 갭:", bold=True))
            click.echo()

            for i, gap in enumerate(result.gaps[:10], 1):  # Show first 10
                severity_color = {
                    "critical": "red",
                    "high": "yellow",
                    "medium": "blue",
                    "low": "green",
                }.get(gap.severity, "white")

                click.echo(
                    click.style(
                        f"{i}. [{gap.severity.upper()}] {gap.description}",
                        fg=severity_color,
                    )
                )

                if gap.suggestions:
                    for suggestion in gap.suggestions[:2]:  # Show first 2 suggestions
                        click.echo(f"   💡 {suggestion}")

                click.echo()

            if len(result.gaps) > 10:
                echo_info(f"... and {len(result.gaps) - 10} more gaps")

        # Save to file
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict for JSON serialization
            result_dict = {
                "total_gaps": result.total_gaps,
                "critical_gaps": result.critical_gaps,
                "high_gaps": result.high_gaps,
                "medium_gaps": result.medium_gaps,
                "low_gaps": result.low_gaps,
                "auto_fixable_gaps": result.auto_fixable_gaps,
                "completeness_score": result.completeness_score,
                "gaps": [gap.model_dump() for gap in result.gaps],
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)

            echo_success(f"Results saved to: {output}")

    except Exception as e:
        echo_error(f"Error: {e}")
        import traceback

        echo_error(traceback.format_exc())
