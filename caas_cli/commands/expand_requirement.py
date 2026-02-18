"""
Expand Requirement Command

요구사항 자동 확장 명령 - caas_framework를 직접 사용
"""

import asyncio

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)


@click.command()
@click.argument("requirement")
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    required=True,
    help="[Phase 0] Base Golden Data JSON file to expand",
)
@click.option(
    "--gaps",
    type=click.Path(exists=True),
    help="Gap Analysis results JSON file (from 'caas analyze-gaps') - optional but recommended",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output JSON file path for expanded Golden Data (default: expanded_golden.json)",
)
@handle_keyboard_interrupt
def expand(requirement, golden_data, gaps, output):
    """
    \b
    [Phase 0] Auto-expand requirements to fill identified gaps

    \b
    ✨ WHAT IT DOES:
    ═══════════════════════════════════════════════════════════════════════════
    Automatically fills requirement gaps by:
    • Adding missing features based on domain best practices
    • Expanding ambiguous specifications with detailed descriptions
    • Completing incomplete data models with suggested fields
    • Adding standard non-functional requirements (security, performance)
    • Enriching UI/UX specifications with common patterns

    \b
    🔄 TWO MODES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1. Gap-driven expansion (recommended):
       Uses gap analysis results to target specific missing areas

    \b
    2. General expansion:
       Enriches all areas based on domain knowledge

    \b
    📊 OUTPUT:
    ═══════════════════════════════════════════════════════════════════════════
    Generates expanded_golden.json containing:
    • Original Golden Data + filled gaps
    • expansion_summary: What was added/modified
    • confidence_score: AI confidence in expansions (0-1)
    • suggestions: Manual review recommendations

    \b
    💡 RECOMMENDED WORKFLOW:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Generate initial Golden Data:
       $ caas generate "Build a shopping mall" -o ./output

    \b
    2️⃣  Analyze gaps:
       $ caas analyze-gaps "shopping mall" \\
           -g ./output/golden_data.json \\
           -o gaps.json

    \b
    3️⃣  Auto-expand to fill gaps:
       $ caas expand "shopping mall" \\
           -g ./output/golden_data.json \\
           --gaps gaps.json \\
           -o expanded_golden.json

    \b
    4️⃣  Regenerate with expanded requirements:
       $ caas generate "shopping mall" \\
           --golden-data expanded_golden.json \\
           -o ./final_output

    \b
    📋 EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Gap-driven expansion (best):
       $ caas expand "할일 관리 앱" \\
           --golden-data golden.json \\
           --gaps gaps.json

    \b
    2️⃣  General expansion (no gap analysis):
       $ caas expand "E-commerce platform" \\
           -g golden.json \\
           -o expanded.json

    \b
    3️⃣  Complex system expansion:
       $ caas expand "Healthcare patient management with AI diagnosis" \\
           --golden-data healthcare_golden.json \\
           --gaps healthcare_gaps.json \\
           --output healthcare_expanded.json

    \b
    ⚠️  RECOMMENDATION:
    ═══════════════════════════════════════════════════════════════════════════
    • Always review expanded requirements before final generation
    • AI-generated expansions may not match your exact intent
    • Use 'caas questions' for interactive control instead of auto-expansion

    \b
    📚 See also:
       caas analyze-gaps --help    (Identify gaps first)
       caas questions --help       (Interactive alternative)
    """
    import json
    from pathlib import Path

    from caas_framework.models.specifications import ConcretizedRequirement
    from caas_framework.plugins.llm.openai import OpenAIPlugin
    from caas_framework.refinement import RequirementExpander, RequirementGap

    # Load golden data
    try:
        with open(golden_data, "r", encoding="utf-8") as f:
            golden_data_dict = json.load(f)

        concretized = ConcretizedRequirement(**golden_data_dict)
    except Exception as e:
        echo_error(f"Failed to load golden data: {e}")
        return

    # Load gaps if provided
    gaps_list = []
    if gaps:
        try:
            with open(gaps, "r", encoding="utf-8") as f:
                gaps_result = json.load(f)
                gaps_list = [RequirementGap(**g) for g in gaps_result.get("gaps", [])]
        except Exception as e:
            echo_warning(f"Failed to load gaps file: {e}")
            echo_info("Continuing without gap analysis results...")

    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║               CAAS Auto-Expansion                            ║
║            (Using caas_framework directly)                   ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    echo_info(f"Requirement: {requirement}")
    echo_info(f"Golden Data: {golden_data}")
    if gaps:
        echo_info(f"Gaps: {gaps} ({len(gaps_list)} gaps)")
    click.echo()

    try:
        # Run expansion
        async def run_expansion():
            import os
            from caas_framework.config.loader import load_config
            cfg = load_config()
            llm_plugin = OpenAIPlugin(
                name="openai-expand",
                config={
                    "model": cfg.llm.model,
                    "api_key": cfg.llm.api_key or os.environ.get("OPENAI_API_KEY"),
                    "temperature": cfg.llm.temperature,
                    "max_tokens": cfg.llm.max_tokens,
                },
            )
            await llm_plugin.initialize()

            expander = RequirementExpander(llm_client=llm_plugin)
            result = expander.expand_requirement(requirement, concretized, gaps_list)

            await llm_plugin.close()
            return result

        result = asyncio.run(run_expansion())

        # Display results
        click.echo(click.style("Auto-Expansion Results:", bold=True))
        click.echo()

        # Summary
        if result.expansion_summary:
            click.echo(click.style("📋 Summary:", bold=True))
            click.echo(f"  {result.expansion_summary}")
            click.echo()

        # Added features
        added_features = result.auto_expanded_features
        if added_features:
            click.echo(
                click.style(f"✨ Added Features ({len(added_features)}):", bold=True)
            )
            for i, feature in enumerate(added_features, 1):
                click.echo(f"  {i}. {feature.name}")
                click.echo(f"     {feature.description}")
                if feature.acceptance_criteria:
                    click.echo(f"     인수 기준: {len(feature.acceptance_criteria)}개")
            click.echo()

        # Added data models
        added_models = result.auto_expanded_data_models
        if added_models:
            click.echo(
                click.style(f"💾 Added Data Models ({len(added_models)}):", bold=True)
            )
            for i, dm in enumerate(added_models, 1):
                click.echo(f"  {i}. {dm.entity_name}")
                attrs = [f.name for f in dm.fields[:3]]
                click.echo(f"     속성: {', '.join(attrs)}...")
            click.echo()

        # Added UI components
        added_ui = result.auto_expanded_ui_components
        if added_ui:
            click.echo(
                click.style(f"🎨 Added UI Components ({len(added_ui)}):", bold=True)
            )
            for i, ui in enumerate(added_ui, 1):
                click.echo(f"  {i}. {ui.page_name} ({ui.component_type})")
            click.echo()

        # Best practices
        best_practices = result.best_practices
        if best_practices:
            click.echo(
                click.style(f"💡 Best Practices ({len(best_practices)}):", bold=True)
            )
            for i, bp in enumerate(best_practices[:5], 1):  # Show first 5
                click.echo(f"  {i}. [{bp.category}] {bp.recommendation}")
            if len(best_practices) > 5:
                echo_info(f"... and {len(best_practices) - 5} more best practices")
            click.echo()

        # Save to file
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result.model_dump(), f, indent=2, ensure_ascii=False)

            echo_success(f"Results saved to: {output}")

    except Exception as e:
        echo_error(f"Error: {e}")
        import traceback

        echo_error(traceback.format_exc())
