"""
Traceability Command

추적성 매트릭스 조회 명령
"""

import click

from caas_cli.config import get_config
from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    handle_keyboard_interrupt,
)


@click.command()
@click.option("--requirement", "-r", required=True, help="Original requirement text to trace")
@click.option(
    "--golden-data",
    "-g",
    type=click.Path(exists=True),
    required=True,
    help="[Phase 0] Golden Data JSON file (structured requirements)",
)
@click.option(
    "--agents",
    "-a",
    type=click.Path(exists=True),
    required=True,
    help="[Phase 1] Agents JSON file (agent specifications)",
)
@click.option(
    "--tasks",
    "-t",
    type=click.Path(exists=True),
    required=True,
    help="[Phase 1] Tasks JSON file (task specifications)",
)
@click.option("--output", "-o", type=click.Path(), help="Output report file path (default: stdout)")
@click.option(
    "--format",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
    help="Output format: text (human-readable), json (structured), markdown (documentation)",
)
@click.option("--api-url", type=str, help="API URL (overrides config) - for remote API mode")
@handle_keyboard_interrupt
def traceability(requirement, golden_data, agents, tasks, output, format, api_url):
    """
    \b
    [Phase 2] Verify requirement → agent → task traceability mappings

    \b
    🔗 WHAT IT DOES:
    ═══════════════════════════════════════════════════════════════════════════
    Generates a traceability matrix to verify:
    • Requirements → Features mapping (모든 요구사항이 기능으로 변환됐는지)
    • Features → Agents mapping (각 기능이 담당 에이전트가 있는지)
    • Agents → Tasks mapping (에이전트마다 수행할 작업이 정의됐는지)
    • Orphaned agents/tasks (불필요한 에이전트/작업 식별)
    • Coverage gaps (누락된 요구사항 식별)

    \b
    📊 TRACEABILITY REPORT INCLUDES:
    ═══════════════════════════════════════════════════════════════════════════
    • Full trace paths: Requirement → Feature → Agent → Task
    • Coverage statistics: % requirements implemented
    • Orphaned elements: Agents/tasks not linked to requirements
    • Missing implementations: Requirements without agents/tasks
    • Validation status: Pass/Fail per requirement

    \b
    🎯 WHY USE THIS:
    ═══════════════════════════════════════════════════════════════════════════
    • Ensure all requirements are implemented
    • Identify unnecessary agents/tasks (bloat)
    • Validate completeness before deployment
    • Generate audit trail for compliance
    • Debug missing functionality

    \b
    📋 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Basic traceability check (text output):
       $ caas traceability \\
           -r "할일 관리 앱" \\
           -g golden.json \\
           -a agents.json \\
           -t tasks.json

    \b
    2️⃣  Generate markdown report:
       $ caas traceability \\
           -r "E-commerce platform" \\
           -g golden.json \\
           -a agents.json \\
           -t tasks.json \\
           -o traceability_report.md \\
           --format markdown

    \b
    3️⃣  JSON output for programmatic use:
       $ caas traceability \\
           -r "Healthcare system" \\
           -g golden_data.json \\
           -a agents.json \\
           -t tasks.json \\
           --format json \\
           -o traceability.json

    \b
    💡 TYPICAL WORKFLOW:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Generate code:
       $ caas generate "Build a task app" -o ./output

    \b
    2️⃣  Verify traceability:
       $ caas traceability \\
           -r "task app" \\
           -g ./output/golden_data.json \\
           -a ./output/agents.json \\
           -t ./output/tasks.json

    \b
    3️⃣  If gaps found, refine and regenerate:
       $ caas analyze-gaps "task app" -g ./output/golden_data.json
       $ caas expand "task app" -g ./output/golden_data.json --gaps gaps.json
       $ caas generate "task app" --golden-data expanded_golden.json

    \b
    📈 OUTPUT FORMATS:
    ═══════════════════════════════════════════════════════════════════════════
    • text: Human-readable console output
    • markdown: Documentation-ready .md file
    • json: Structured data for CI/CD integration

    \b
    ⚠️  VALIDATION RULES:
    ═══════════════════════════════════════════════════════════════════════════
    • Every feature must have ≥1 agent assigned
    • Every agent must have ≥1 task assigned
    • Every task must trace back to ≥1 feature
    • No orphaned agents or tasks allowed

    \b
    📚 See also:
       caas generate --help         (Automatic traceability during generation)
       caas generate --no-traceability  (Skip traceability check)
    """
    import json
    from pathlib import Path

    # Load config
    config = get_config()
    api_url = api_url or config.get("api_url", "http://localhost:8000")

    # Load files
    try:
        with open(golden_data, "r", encoding="utf-8") as f:
            golden_data_dict = json.load(f)
        with open(agents, "r", encoding="utf-8") as f:
            agents_list = json.load(f)
        with open(tasks, "r", encoding="utf-8") as f:
            tasks_list = json.load(f)
    except Exception as e:
        echo_error(f"Failed to load files: {e}")
        return

    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║              CAAS Traceability Matrix                         ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    echo_info(f"Requirement: {requirement}")
    click.echo()

    # Call API
    try:
        import requests

        response = requests.post(
            f"{api_url}/api/v1/traceability/build",
            json={
                "requirement": requirement,
                "golden_data": golden_data_dict,
                "agents": agents_list,
                "tasks": tasks_list,
            },
            timeout=120,
        )

        if response.status_code == 200:
            result = response.json()

            if format == "text":
                # Text format
                click.echo(click.style("Traceability Matrix Results:", bold=True))
                click.echo()

                # Metrics
                click.echo(f"  전체 링크:   {result['total_links']}")
                click.echo(f"  커버리지:    {result['coverage_percentage']:.1f}%")
                click.echo(f"  미구현 항목: {len(result['gaps'])}")
                click.echo()

                # Links sample
                if result["links"]:
                    click.echo(click.style("추적 링크 (최대 20개):", bold=True))
                    click.echo()

                    for i, link in enumerate(result["links"][:20], 1):
                        click.echo(
                            f"{i}. {link['source_type']}:{link['source_id']} "
                            f"→ {link['target_type']}:{link['target_id']} "
                            f"({link['confidence']:.0%})"
                        )

                    if len(result["links"]) > 20:
                        echo_info(f"... and {len(result['links']) - 20} more links")

                click.echo()

                # Gaps
                if result["gaps"]:
                    click.echo(click.style("미구현 항목:", bold=True))
                    for gap in result["gaps"][:10]:
                        click.echo(f"  ⚠️  {gap}")

            elif format == "json":
                # JSON format
                click.echo(json.dumps(result, indent=2, ensure_ascii=False))

            elif format == "markdown":
                # Markdown format
                report = f"""# Traceability Matrix Report

## Summary

- **전체 링크**: {result['total_links']}
- **커버리지**: {result['coverage_percentage']:.1f}%
- **미구현 항목**: {len(result['gaps'])}

## 추적 링크

| # | Source | → | Target | Confidence |
|---|--------|---|--------|------------|
"""
                for i, link in enumerate(result["links"][:50], 1):
                    report += f"| {i} | {link['source_type']}:{link['source_id']} | → | {link['target_type']}:{link['target_id']} | {link['confidence']:.0%} |\n"

                if result["gaps"]:
                    report += "\n## 미구현 항목\n\n"
                    for gap in result["gaps"]:
                        report += f"- ⚠️ {gap}\n"

                click.echo(report)

            # Save to file
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                if format == "markdown":
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(
                            report
                            if format == "markdown"
                            else json.dumps(result, indent=2, ensure_ascii=False)
                        )
                else:
                    with open(output_path, "w", encoding="utf-8") as f:
                        if format == "json":
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        else:
                            # Text format - just save JSON
                            json.dump(result, f, indent=2, ensure_ascii=False)

                echo_success(f"Report saved to: {output}")

        else:
            echo_error(f"API error: {response.status_code}")
            echo_error(response.text)

    except Exception as e:
        echo_error(f"Error: {e}")
