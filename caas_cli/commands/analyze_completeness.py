"""
Analyze Completeness Command

Analyze implementation completeness against Golden Data requirements.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    handle_keyboard_interrupt,
    load_json,
)


@click.command()
@click.option(
    "--project",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    help="Path to generated project directory",
)
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    required=True,
    help="Path to golden_data.json file",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save analysis report to JSON file",
)
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed traceability analysis",
)
@handle_keyboard_interrupt
def analyze_completeness(project, golden_data, output, detailed):
    """
    Analyze implementation completeness against Golden Data

    Validates that generated code implements all features and acceptance
    criteria from Golden Data. Provides traceability analysis and identifies
    implementation gaps.

    \b
    ANALYSIS INCLUDES:
    ═══════════════════════════════════════════════════════════════════════════
    • Feature coverage percentage
    • Traceability matrix (Golden Data → Implementation)
    • Missing requirements detection
    • Business rule violations
    • Implementation gap analysis
    • Actionable recommendations

    \b
    OUTPUT METRICS:
    ═══════════════════════════════════════════════════════════════════════════
    • Total features vs. implemented
    • Overall coverage percentage
    • Missing/partial/complete features
    • Critical violations count

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Basic completeness analysis:
       $ caas analyze-completeness --project ./generated_project \\
           --golden-data golden_data.json

    \b
    2️⃣  Detailed analysis with report:
       $ caas analyze-completeness -p ./project -g golden_data.json \\
           --detailed --output completeness_report.json

    \b
    3️⃣  Quick coverage check:
       $ caas analyze-completeness -p ./project -g golden_data.json

    \b
    INTERPRETATION:
    ═══════════════════════════════════════════════════════════════════════════
    • Coverage >= 90%: Excellent - production ready
    • Coverage 70-90%: Good - minor gaps acceptable
    • Coverage 50-70%: Fair - review missing features
    • Coverage < 50%: Poor - major features missing

    \b
    NEXT STEPS:
    ═══════════════════════════════════════════════════════════════════════════
    • Review implementation gaps in report
    • Use 'caas fix' to address violations
    • Regenerate specific components with 'caas generate-code'
    • Re-run analysis to verify improvements
    """
    from caas_framework.agents.code_analysis_agent import CodeAnalysisAgent
    from caas_framework.config.loader import load_config
    from caas_framework.models.specifications import ConcretizedRequirement
    from caas_framework.plugins.llm.factory import create_llm_plugin

    echo_progress("Initializing Code Analysis Agent...")

    try:
        # Load configuration
        config = load_config()

        # Load Golden Data
        echo_progress(f"Loading Golden Data from {golden_data}...")
        golden_data_dict = load_json(golden_data)
        golden_data_obj = ConcretizedRequirement(**golden_data_dict)

        # Create LLM plugin
        llm_plugin = create_llm_plugin(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
            api_base=config.llm.api_base,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        # Create Code Analysis Agent
        agent = CodeAnalysisAgent(llm_plugin=llm_plugin, golden_data=golden_data_obj)

        # Run analysis
        echo_progress(f"Analyzing implementation in {project}...")
        project_path = Path(project)

        result = asyncio.run(
            agent.analyze_implementation(
                project_path=project_path, golden_data=golden_data_obj
            )
        )

        # Display results
        echo_success(f"\n{'='*70}")
        echo_success("IMPLEMENTATION COMPLETENESS ANALYSIS")
        echo_success(f"{'='*70}\n")

        echo_info(f"Project: {result.project_name}")
        echo_info(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary statistics
        echo_success("📊 COVERAGE SUMMARY:")
        echo_info(f"  Total Features:        {result.total_features}")
        echo_info(f"  ✅ Implemented:        {result.implemented_features}")
        echo_info(f"  ⚠️  Partial:            {result.partial_features}")
        echo_info(f"  ❌ Missing:            {result.missing_features}")
        echo_info(f"  📈 Overall Coverage:   {result.overall_coverage:.1f}%\n")

        # Coverage interpretation
        coverage = result.overall_coverage
        if coverage >= 90:
            echo_success("✨ Excellent coverage - production ready!")
        elif coverage >= 70:
            echo_info("✅ Good coverage - minor gaps acceptable")
        elif coverage >= 50:
            echo_error("⚠️  Fair coverage - review missing features")
        else:
            echo_error("❌ Poor coverage - major features missing")

        # Business rule violations
        if result.business_rule_violations:
            echo_error(f"\n🚨 BUSINESS RULE VIOLATIONS ({len(result.business_rule_violations)}):")
            critical = [
                v for v in result.business_rule_violations if v.severity == "critical"
            ]
            if critical:
                echo_error(f"  ⛔ Critical: {len(critical)}")
            high = [v for v in result.business_rule_violations if v.severity == "high"]
            if high:
                echo_error(f"  🔴 High: {len(high)}")

        # Implementation gaps
        if result.implementation_gaps:
            echo_info(f"\n📋 IMPLEMENTATION GAPS ({len(result.implementation_gaps)}):")
            missing = [g for g in result.implementation_gaps if g.gap_type == "missing"]
            partial = [g for g in result.implementation_gaps if g.gap_type == "partial"]
            if missing:
                echo_info(f"  Missing: {len(missing)}")
            if partial:
                echo_info(f"  Partial: {len(partial)}")

        # Recommendations
        if result.recommendations:
            echo_success(f"\n💡 RECOMMENDATIONS:")
            for rec in result.recommendations:
                echo_info(f"  • {rec}")

        # Detailed traceability
        if detailed:
            echo_success(f"\n{'='*70}")
            echo_success("DETAILED TRACEABILITY ANALYSIS")
            echo_success(f"{'='*70}\n")

            for tr in result.traceability_results:
                status = "✅" if tr.is_implemented else "❌"
                echo_info(f"{status} {tr.feature_name} (Coverage: {tr.coverage_percentage:.1f}%)")

                if tr.implementation_files:
                    echo_info(f"   Files: {', '.join(tr.implementation_files[:3])}")

                if tr.missing_requirements:
                    echo_error(f"   Missing: {len(tr.missing_requirements)} requirements")
                    if detailed and len(tr.missing_requirements) <= 3:
                        for req in tr.missing_requirements:
                            echo_error(f"     - {req[:80]}...")

                echo_info("")

        # Save report
        if output:
            report = {
                "analysis_type": "completeness",
                "project_path": str(project_path),
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "project_name": result.project_name,
                    "total_features": result.total_features,
                    "implemented_features": result.implemented_features,
                    "partial_features": result.partial_features,
                    "missing_features": result.missing_features,
                    "overall_coverage": result.overall_coverage,
                },
                "implementation_analysis": result.dict(),
            }

            with open(output, "w") as f:
                json.dump(report, f, indent=2)

            echo_success(f"\n📄 Report saved to: {output}")

        # Exit code based on coverage
        if coverage < 50:
            raise click.Abort()

    except click.Abort:
        raise
    except FileNotFoundError as e:
        echo_error(f"File not found: {e}")
        raise click.Abort()
    except Exception as e:
        echo_error(f"Analysis failed: {e}")
        import traceback

        echo_error(traceback.format_exc())
        raise click.Abort()
