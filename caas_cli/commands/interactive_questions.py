"""
Interactive Questions Command

인터랙티브 질문 생성 및 답변 수집 명령
"""

import click
from caas_cli.config import get_config
from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)


@click.command()
@click.option(
    "--gaps",
    "-g",
    type=click.Path(exists=True),
    required=True,
    help="[Phase 0] Gap Analysis results JSON file (from 'caas analyze-gaps')",
)
@click.option(
    "--domain",
    "-d",
    type=str,
    required=True,
    help="Domain context for question generation (TASK_MANAGEMENT, E_COMMERCE, FINANCE, HEALTHCARE, etc.)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output answers JSON file path (default: answers.json)",
)
@click.option("--api-url", type=str, help="API URL (overrides config) - for remote API mode")
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Enable interactive CLI mode for answering questions (default: enabled)",
)
@handle_keyboard_interrupt
def questions(gaps, domain, output, api_url, interactive):
    """
    \b
    [Phase 0] Interactive question-driven requirement clarification

    \b
    💬 WHAT IT DOES:
    ═══════════════════════════════════════════════════════════════════════════
    Generates intelligent questions to fill requirement gaps:
    • Converts gaps into clear, actionable questions
    • Adapts questions to domain context
    • Collects user answers interactively (or batch mode)
    • Generates structured answers.json for requirement expansion

    \b
    🎯 QUESTION TYPES:
    ═══════════════════════════════════════════════════════════════════════════
    • Multiple choice (feature selection)
    • Yes/No (feature inclusion)
    • Text input (detailed specifications)
    • Numeric input (constraints, limits)
    • Priority ranking (feature prioritization)

    \b
    🔄 WORKFLOW INTEGRATION:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Generate & analyze gaps:
       $ caas generate "Build a task app" -o ./output
       $ caas analyze-gaps "task app" -g ./output/golden_data.json -o gaps.json

    \b
    2️⃣  Interactive question session:
       $ caas questions -g gaps.json -d TASK_MANAGEMENT

    \b
    3️⃣  Use answers to expand requirements:
       $ caas expand "task app" \\
           --golden-data ./output/golden_data.json \\
           --gaps gaps.json \\
           --answers answers.json

    \b
    4️⃣  Regenerate with complete requirements:
       $ caas generate "task app" \\
           --golden-data expanded_golden.json

    \b
    📋 EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Interactive mode (default):
       $ caas questions --gaps gaps.json --domain TASK_MANAGEMENT

    \b
    2️⃣  Save answers to specific file:
       $ caas questions -g gaps.json -d E_COMMERCE -o my_answers.json

    \b
    3️⃣  Batch mode (no interaction - uses defaults):
       $ caas questions -g gaps.json -d FINANCE --no-interactive

    \b
    4️⃣  Complex domain with many gaps:
       $ caas questions \\
           --gaps healthcare_gaps.json \\
           --domain HEALTHCARE \\
           --output healthcare_answers.json

    \b
    💡 TIPS:
    ═══════════════════════════════════════════════════════════════════════════
    • Interactive mode allows you to review/edit each answer
    • Questions are prioritized by gap severity (critical → low)
    • Domain context improves question relevance and defaults
    • Can skip questions - they'll use domain best-practice defaults

    \b
    ⚙️  VS. AUTO-EXPANSION:
    ═══════════════════════════════════════════════════════════════════════════
    • Use 'caas questions' when you want control and review
    • Use 'caas expand' when you want fast auto-fill with AI

    \b
    📚 See also:
       caas analyze-gaps --help    (Generate gaps first)
       caas expand --help          (Auto-expansion alternative)
    """
    import json
    from pathlib import Path

    # Load config
    config = get_config()
    api_url = api_url or config.get("api_url", "http://localhost:8000")

    # Load gaps
    try:
        with open(gaps, "r", encoding="utf-8") as f:
            gaps_result = json.load(f)
            gaps_list = gaps_result.get("gaps", [])
    except Exception as e:
        echo_error(f"Failed to load gaps file: {e}")
        return

    click.echo(
        """
╔══════════════════════════════════════════════════════════════╗
║            CAAS Interactive Questions                        ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    echo_info(f"Domain: {domain}")
    echo_info(f"Gaps: {len(gaps_list)}")
    click.echo()

    # Generate questions via API
    try:
        import requests

        response = requests.post(
            f"{api_url}/api/v1/requirements/generate-questions",
            json={"gaps": gaps_list, "domain": domain},
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            questions_list = result.get("questions", [])

            if not questions_list:
                echo_success("✅ No questions needed - all information is sufficient!")
                return

            click.echo(click.style(f"📋 Generated {len(questions_list)} questions:", bold=True))
            click.echo()

            answers = {}

            # Interactive mode - ask questions
            if interactive:
                for i, q in enumerate(questions_list, 1):
                    click.echo(click.style(f"Q{i}. {q['question_text']}", bold=True))

                    if q.get("help_text"):
                        click.echo(click.style(f"   💡 {q['help_text']}", fg="blue"))

                    q_type = q["question_type"]
                    q_id = q["id"]

                    if q_type == "YES_NO":
                        answer = click.confirm("   답변", default=True)
                        answers[q_id] = "yes" if answer else "no"

                    elif q_type == "SINGLE_CHOICE":
                        options = q.get("options", [])
                        click.echo("   선택지:")
                        for idx, opt in enumerate(options, 1):
                            click.echo(f"     {idx}. {opt}")

                        choice = click.prompt(
                            "   선택", type=click.IntRange(1, len(options)), default=1
                        )
                        answers[q_id] = options[choice - 1]

                    elif q_type == "MULTI_CHOICE":
                        options = q.get("options", [])
                        click.echo("   선택지 (쉼표로 구분):")
                        for idx, opt in enumerate(options, 1):
                            click.echo(f"     {idx}. {opt}")

                        choices_str = click.prompt("   선택 (예: 1,3,4)", type=str, default="1")

                        try:
                            choice_indices = [int(c.strip()) for c in choices_str.split(",")]
                            selected = [
                                options[idx - 1]
                                for idx in choice_indices
                                if 1 <= idx <= len(options)
                            ]
                            answers[q_id] = selected
                        except (ValueError, IndexError):
                            echo_warning("Invalid input, skipping question")

                    elif q_type == "TEXT_INPUT":
                        answer = click.prompt(
                            "   입력",
                            type=str,
                            default=q.get("default_value", ""),
                            show_default=True,
                        )
                        answers[q_id] = answer

                    elif q_type == "NUMBER_INPUT":
                        min_val = q.get("min_value", 0)
                        max_val = q.get("max_value", 1000000)
                        default_val = float(q.get("default_value", min_val))

                        answer = click.prompt("   숫자 입력", type=float, default=default_val)
                        answers[q_id] = answer

                    click.echo()

                echo_success(f"✅ {len(answers)}개 질문에 답변했습니다!")

            else:
                # Non-interactive mode - just show questions
                for i, q in enumerate(questions_list, 1):
                    click.echo(f"{i}. [{q['question_type']}] {q['question_text']}")
                    if q.get("options"):
                        click.echo(f"   Options: {', '.join(q['options'])}")

                echo_info("Run with --interactive to answer questions")

            # Save answers
            if output and answers:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                output_data = {
                    "domain": domain,
                    "questions": questions_list,
                    "answers": answers,
                    "total_questions": len(questions_list),
                    "total_answers": len(answers),
                }

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)

                echo_success(f"Answers saved to: {output}")

        else:
            echo_error(f"API error: {response.status_code}")
            echo_error(response.text)

    except requests.exceptions.ConnectionError:
        echo_error("Failed to connect to API server")
        echo_info(f"Make sure the API server is running at {api_url}")
    except KeyboardInterrupt:
        echo_warning("\n\nInterrupted by user")
        if answers and output:
            # Save partial answers
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            output_data = {"domain": domain, "answers": answers, "partial": True}

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            echo_info(f"Partial answers saved to: {output}")
    except Exception as e:
        echo_error(f"Error: {e}")
