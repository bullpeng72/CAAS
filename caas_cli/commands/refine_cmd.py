"""
Refine Command — 요구사항 정제 통합 파이프라인

갭 분석 → 인터랙티브 Q&A → 자동 확장을 단일 명령어로 실행합니다.
기존 analyze-gaps / questions / expand 3개 명령어를 하나로 통합.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)


# ─────────────────────────────────────────────────────────────
# LLM 초기화 헬퍼
# ─────────────────────────────────────────────────────────────

async def _init_llm(name: str = "openai-refine"):
    """OpenAIPlugin 초기화 후 반환."""
    import os
    from caas_framework.config.loader import load_config
    from caas_framework.plugins.llm.openai import OpenAIPlugin

    cfg = load_config()
    plugin = OpenAIPlugin(
        name=name,
        config={
            "model": cfg.llm.model,
            "api_key": cfg.llm.api_key or os.environ.get("OPENAI_API_KEY", ""),
            "temperature": cfg.llm.temperature,
            "max_tokens": cfg.llm.max_tokens,
        },
    )
    await plugin.initialize()
    return plugin


# ─────────────────────────────────────────────────────────────
# Golden Data 로드 헬퍼
# ─────────────────────────────────────────────────────────────

def _load_golden_data(golden_data_path: str):
    """golden_data.json → ConcretizedRequirement 로드."""
    from caas_framework.models.specifications import ConcretizedRequirement

    with open(golden_data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return ConcretizedRequirement(**raw), raw


# ─────────────────────────────────────────────────────────────
# 인터랙티브 Q&A 헬퍼
# ─────────────────────────────────────────────────────────────

def _run_interactive_qa(questions: list) -> Dict[str, Any]:
    """질문 목록을 받아 Rich CLI로 인터랙티브 Q&A를 진행합니다."""
    from rich.console import Console
    from rich.rule import Rule

    console = Console()
    answers: Dict[str, Any] = {}

    console.print()
    console.print(Rule("[bold cyan]📋 요구사항 구체화 질문[/bold cyan]", style="cyan"))
    console.print(f"  총 {len(questions)}개 질문에 답해주시면 더 정확한 코드를 생성합니다.\n")

    for i, q in enumerate(questions, 1):
        q_type = (
            q.question_type.value
            if hasattr(q.question_type, "value")
            else str(q.question_type)
        )
        console.print(f"[bold white]Q{i}. {q.question_text}[/bold white]")
        if q.help_text:
            console.print(f"    [dim]{q.help_text}[/dim]")

        try:
            if q_type == "yes_no":
                answer = click.confirm("   답변", default=True)
                answers[q.id] = "yes" if answer else "no"

            elif q_type == "single_choice":
                options = q.options or []
                for idx, opt in enumerate(options, 1):
                    console.print(f"    [cyan]{idx}.[/cyan] {opt}")
                choice = click.prompt(
                    "   선택 번호",
                    type=click.IntRange(1, len(options)),
                    default=1,
                )
                answers[q.id] = options[choice - 1]

            elif q_type == "multi_choice":
                options = q.options or []
                for idx, opt in enumerate(options, 1):
                    console.print(f"    [cyan]{idx}.[/cyan] {opt}")
                raw = click.prompt("   선택 번호 (쉼표 구분, 예: 1,3)", type=str, default="1")
                try:
                    indices = [int(c.strip()) for c in raw.split(",")]
                    answers[q.id] = [
                        options[idx - 1] for idx in indices if 1 <= idx <= len(options)
                    ]
                except (ValueError, IndexError):
                    echo_warning("잘못된 입력, 첫 번째 옵션으로 설정합니다.")
                    answers[q.id] = [options[0]] if options else []

            elif q_type == "text_input":
                answers[q.id] = click.prompt(
                    "   입력",
                    type=str,
                    default=q.default_value or "",
                    show_default=bool(q.default_value),
                )

            elif q_type == "number_input":
                answers[q.id] = click.prompt(
                    "   숫자 입력",
                    type=float,
                    default=float(q.default_value) if q.default_value else 0.0,
                )

            elif q_type == "range_slider":
                min_v = q.min_value or 0
                max_v = q.max_value or 100
                answers[q.id] = click.prompt(
                    f"   값 입력 ({min_v}~{max_v})",
                    type=click.IntRange(min_v, max_v),
                    default=int(q.default_value) if q.default_value else min_v,
                )

            else:
                answers[q.id] = click.prompt("   입력", type=str, default="")

        except click.Abort:
            console.print("\n[yellow]⚠️  Q&A 중단. 현재까지 답변으로 진행합니다.[/yellow]")
            break

        console.print()

    echo_success(f"{len(answers)}개 질문에 답변 완료")
    return answers


# ─────────────────────────────────────────────────────────────
# 갭 결과 저장 헬퍼
# ─────────────────────────────────────────────────────────────

def _save_gaps(gap_result, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        gaps_data = [g.model_dump() for g in gap_result.gaps]
        json.dump(gaps_data, f, indent=2, ensure_ascii=False)
    echo_info(f"갭 분석 결과 저장: {output_path}")


def _save_answers(
    answers: Dict[str, Any],
    questions: list,
    domain: str,
    output_path: str,
) -> None:
    data = {
        "domain": domain,
        "total_questions": len(questions),
        "total_answers": len(answers),
        "answers": answers,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    echo_info(f"Q&A 답변 저장: {output_path}")


# ─────────────────────────────────────────────────────────────
# 결과 출력 헬퍼
# ─────────────────────────────────────────────────────────────

def _display_refinement_summary(gap_result, expanded, output_path: str) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("항목", style="cyan")
    table.add_column("값", style="white")

    orig_features = len(expanded.original.features) if expanded.original.features else 0
    new_features = len(expanded.auto_expanded_features)
    new_dm = len(expanded.auto_expanded_data_models)
    new_ui = len(expanded.auto_expanded_ui_components)
    remaining = len(expanded.remaining_gaps)

    table.add_row("발견된 갭", f"{gap_result.total_gaps}개 (Critical: {gap_result.critical_gaps}, High: {gap_result.high_gaps})")
    table.add_row("기존 기능", f"{orig_features}개")
    table.add_row("추가된 기능", f"[green]+{new_features}개[/green]" if new_features else "0개")
    table.add_row("추가된 데이터모델", f"[green]+{new_dm}개[/green]" if new_dm else "0개")
    table.add_row("추가된 UI컴포넌트", f"[green]+{new_ui}개[/green]" if new_ui else "0개")
    table.add_row("남은 갭", f"[yellow]{remaining}개[/yellow]" if remaining else "[green]0개 (완료)[/green]")
    table.add_row("출력 파일", f"[bold]{output_path}[/bold]")

    if expanded.expansion_summary:
        table.add_row("요약", expanded.expansion_summary[:80] + "..." if len(expanded.expansion_summary) > 80 else expanded.expansion_summary)

    console.print()
    console.print(Panel(table, title="[bold green]✅ 요구사항 정제 완료[/bold green]", border_style="green"))
    console.print()
    console.print(f"  [dim]다음 단계:[/dim] [bold]caas generate --golden-data {output_path}[/bold]")
    console.print()


# ─────────────────────────────────────────────────────────────
# Click 명령어 그룹
# ─────────────────────────────────────────────────────────────

@click.group(name="refine")
def refine_group():
    """[Phase 0] 요구사항 정제 통합 파이프라인.

    갭 분석 → 인터랙티브 Q&A → 자동 확장을 한 번에 실행합니다.
    기존 analyze-gaps / questions / expand 3단계 워크플로우를 대체합니다.

    \b
    예시:
      # Golden Data 생성 후 정제
      caas generate-phase --phase 0 "별자리 운세 시스템" --output ./project
      caas refine run "별자리 운세 시스템" --golden-data ./project/golden_data.json

      # 단계별 실행
      caas refine gaps "별자리 운세 시스템" --golden-data ./project/golden_data.json
      caas refine ask --gaps gaps.json --domain CUSTOM
      caas refine expand "별자리 운세 시스템" --golden-data ./project/golden_data.json --gaps gaps.json
    """
    pass


# ─────────────────────────────────────────────────────────────
# caas refine run — 전체 파이프라인
# ─────────────────────────────────────────────────────────────

@refine_group.command(name="run")
@click.argument("requirement")
@click.option(
    "--golden-data", "-g",
    type=click.Path(exists=True),
    required=True,
    help="Phase 0 결과물 golden_data.json 경로",
)
@click.option(
    "--domain", "-d",
    type=str,
    default="CUSTOM",
    show_default=True,
    help="도메인 (TASK_MANAGEMENT, DATA_ANALYSIS, CONVERSATIONAL_AI, CUSTOM 등)",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="refined_golden.json",
    show_default=True,
    help="정제된 Golden Data 출력 경로",
)
@click.option(
    "--gaps-output",
    type=click.Path(),
    default=None,
    help="갭 분석 결과 저장 경로 (선택)",
)
@click.option(
    "--answers-output",
    type=click.Path(),
    default=None,
    help="Q&A 답변 저장 경로 (선택)",
)
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="인터랙티브 Q&A 모드 (기본: 활성화)",
)
@click.option(
    "--skip-questions",
    is_flag=True,
    default=False,
    help="Q&A 단계 건너뛰기 (갭 분석 + 자동 확장만 실행)",
)
@handle_keyboard_interrupt
def refine_run(
    requirement,
    golden_data,
    domain,
    output,
    gaps_output,
    answers_output,
    interactive,
    skip_questions,
):
    """전체 정제 파이프라인 실행: 갭 분석 → Q&A → 확장.

    \b
    예시:
      caas refine run "할일 관리 시스템" --golden-data ./golden_data.json
      caas refine run "챗봇" -g golden.json --domain CONVERSATIONAL_AI --no-interactive
      caas refine run "분석 시스템" -g golden.json --skip-questions -o refined.json
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule

    from caas_framework.refinement.gap_analyzer import RequirementGapAnalyzer
    from caas_framework.refinement.expander import RequirementExpander
    from caas_framework.refinement.question_generator import InteractiveQuestionGenerator

    console = Console()

    # ── 헤더 출력 ──
    console.print()
    console.print(Panel.fit(
        "[bold magenta]🔬 CAAS 요구사항 정제 파이프라인[/bold magenta]\n"
        f"[dim]갭 분석 → 인터랙티브 Q&A → 자동 확장[/dim]",
        border_style="magenta",
    ))
    console.print(f"  요구사항: [bold]{requirement}[/bold]")
    console.print(f"  도메인:   [cyan]{domain}[/cyan]")
    console.print(f"  입력:     [dim]{golden_data}[/dim]")
    console.print()

    # ── Golden Data 로드 ──
    try:
        concretized, raw_dict = _load_golden_data(golden_data)
    except Exception as e:
        echo_error(f"Golden Data 로드 실패: {e}")
        raise click.Abort()

    # ══════════════════════════════════════════
    # STAGE 1: 갭 분석
    # ══════════════════════════════════════════
    console.print(Rule("[bold]Stage 1/3  갭 분석[/bold]", style="blue"))

    try:
        async def _run_gap_analysis():
            llm = await _init_llm("openai-refine-gaps")
            try:
                analyzer = RequirementGapAnalyzer(llm_client=llm)
                return analyzer.analyze_gaps(requirement, concretized)
            finally:
                await llm.close()

        with console.status("[bold blue]갭 분석 중...[/bold blue]", spinner="dots"):
            gap_result = asyncio.run(_run_gap_analysis())

    except Exception as e:
        echo_error(f"갭 분석 실패: {e}")
        raise click.Abort()

    # 갭 결과 출력
    score_color = "green" if gap_result.completeness_score >= 0.8 else "yellow" if gap_result.completeness_score >= 0.5 else "red"
    console.print(
        f"  완전성 점수: [{score_color}]{gap_result.completeness_score:.1%}[/{score_color}]  "
        f"| 갭: {gap_result.total_gaps}개 "
        f"(Critical: [red]{gap_result.critical_gaps}[/red], "
        f"High: [yellow]{gap_result.high_gaps}[/yellow], "
        f"Medium: {gap_result.medium_gaps}, Low: {gap_result.low_gaps})"
    )
    console.print()

    if gaps_output:
        _save_gaps(gap_result, gaps_output)

    if gap_result.total_gaps == 0:
        echo_success("갭이 없습니다. 요구사항이 완전합니다.")
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(raw_dict, f, indent=2, ensure_ascii=False)
        echo_success(f"출력 저장: {output}")
        return

    # ══════════════════════════════════════════
    # STAGE 2: 인터랙티브 Q&A
    # ══════════════════════════════════════════
    answers: Dict[str, Any] = {}

    if skip_questions:
        console.print(Rule("[bold]Stage 2/3  Q&A (건너뜀)[/bold]", style="dim"))
        echo_info("--skip-questions 플래그로 Q&A 단계를 건너뜁니다.")
    else:
        console.print(Rule("[bold]Stage 2/3  인터랙티브 Q&A[/bold]", style="blue"))

        try:
            generator = InteractiveQuestionGenerator()
            questions = generator.generate_questions(gap_result.gaps, domain)
        except Exception as e:
            echo_warning(f"질문 생성 실패: {e}. Q&A 단계를 건너뜁니다.")
            questions = []

        if questions and interactive:
            answers = _run_interactive_qa(questions)
            if answers_output:
                _save_answers(answers, questions, domain, answers_output)
        elif questions and not interactive:
            echo_info(f"--no-interactive 모드: {len(questions)}개 질문을 건너뜁니다.")
        else:
            echo_info("생성된 질문이 없습니다. 자동 확장으로 진행합니다.")

    console.print()

    # ══════════════════════════════════════════
    # STAGE 3: 자동 확장
    # ══════════════════════════════════════════
    console.print(Rule("[bold]Stage 3/3  자동 확장[/bold]", style="blue"))

    try:
        async def _run_expansion():
            llm = await _init_llm("openai-refine-expand")
            try:
                expander = RequirementExpander(llm)
                return expander.expand_requirement(requirement, concretized, gap_result.gaps)
            finally:
                await llm.close()

        with console.status("[bold blue]요구사항 확장 중...[/bold blue]", spinner="dots"):
            expanded = asyncio.run(_run_expansion())

    except Exception as e:
        echo_error(f"확장 실패: {e}")
        raise click.Abort()

    # ── 출력 파일 저장 (ConcretizedRequirement 형식으로 병합) ──
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    merged = expanded.original.model_dump()
    # 자동 확장된 피처/데이터모델/UI컴포넌트를 원본에 병합
    if expanded.auto_expanded_features:
        merged["features"] = (
            merged.get("features", []) +
            [f.model_dump() for f in expanded.auto_expanded_features]
        )
    if expanded.auto_expanded_data_models:
        merged["data_models"] = (
            merged.get("data_models", []) +
            [dm.model_dump() for dm in expanded.auto_expanded_data_models]
        )
    if expanded.auto_expanded_ui_components:
        merged["ui_components"] = (
            merged.get("ui_components", []) +
            [ui.model_dump() for ui in expanded.auto_expanded_ui_components]
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    _display_refinement_summary(gap_result, expanded, str(output_path))


# ─────────────────────────────────────────────────────────────
# caas refine gaps — 갭 분석만 실행
# ─────────────────────────────────────────────────────────────

@refine_group.command(name="gaps")
@click.argument("requirement")
@click.option("--golden-data", "-g", type=click.Path(exists=True), required=True,
              help="golden_data.json 경로")
@click.option("--output", "-o", type=click.Path(), default="gaps.json", show_default=True,
              help="갭 분석 결과 저장 경로")
@handle_keyboard_interrupt
def refine_gaps(requirement, golden_data, output):
    """Stage 1만 실행: 요구사항 갭 분석.

    \b
    예시:
      caas refine gaps "할일 관리 시스템" --golden-data ./golden_data.json
      caas refine gaps "챗봇" -g golden.json -o my_gaps.json
    """
    from rich.console import Console
    from rich.table import Table

    from caas_framework.refinement.gap_analyzer import RequirementGapAnalyzer

    console = Console()

    try:
        concretized, _ = _load_golden_data(golden_data)
    except Exception as e:
        echo_error(f"Golden Data 로드 실패: {e}")
        raise click.Abort()

    try:
        async def _run():
            llm = await _init_llm("openai-gaps")
            try:
                analyzer = RequirementGapAnalyzer(llm_client=llm)
                return analyzer.analyze_gaps(requirement, concretized)
            finally:
                await llm.close()

        with console.status("[bold blue]갭 분석 중...[/bold blue]", spinner="dots"):
            result = asyncio.run(_run())

    except Exception as e:
        echo_error(f"갭 분석 실패: {e}")
        raise click.Abort()

    # 결과 테이블 출력
    table = Table(title="갭 분석 결과", show_header=True, header_style="bold cyan")
    table.add_column("심각도", style="bold", width=10)
    table.add_column("갭 유형", width=25)
    table.add_column("설명", width=50)
    table.add_column("자동수정", width=8)

    severity_colors = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "dim"}
    for gap in result.gaps:
        color = severity_colors.get(gap.severity, "white")
        table.add_row(
            f"[{color}]{gap.severity.upper()}[/{color}]",
            gap.gap_type,
            gap.description[:50] + ("..." if len(gap.description) > 50 else ""),
            "✅" if gap.auto_fixable else "❌",
        )

    console.print()
    console.print(table)
    echo_info(
        f"총 {result.total_gaps}개 갭 | 완전성: {result.completeness_score:.1%} "
        f"| 자동수정 가능: {result.auto_fixable_gaps}개"
    )

    _save_gaps(result, output)
    echo_success(f"결과 저장 완료: {output}")
    echo_info(f"다음 단계: caas refine ask --gaps {output} --domain <도메인>")


# ─────────────────────────────────────────────────────────────
# caas refine ask — Q&A만 실행
# ─────────────────────────────────────────────────────────────

@refine_group.command(name="ask")
@click.option("--gaps", "-g", type=click.Path(exists=True), required=True,
              help="gaps.json 경로")
@click.option("--domain", "-d", type=str, default="CUSTOM", show_default=True,
              help="도메인")
@click.option("--output", "-o", type=click.Path(), default="answers.json", show_default=True,
              help="답변 저장 경로")
@click.option("--interactive/--no-interactive", default=True,
              help="인터랙티브 모드 (기본: 활성화)")
@handle_keyboard_interrupt
def refine_ask(gaps, domain, output, interactive):
    """Stage 2만 실행: 인터랙티브 질문 생성 및 답변 수집.

    \b
    예시:
      caas refine ask --gaps gaps.json --domain TASK_MANAGEMENT
      caas refine ask -g gaps.json -d CUSTOM -o my_answers.json
    """
    from caas_framework.refinement.gap_analyzer import RequirementGap
    from caas_framework.refinement.question_generator import InteractiveQuestionGenerator

    # 갭 로드
    try:
        with open(gaps, "r", encoding="utf-8") as f:
            gaps_raw = json.load(f)
        if isinstance(gaps_raw, list):
            gaps_list = [RequirementGap(**g) for g in gaps_raw]
        else:
            gaps_list = [RequirementGap(**g) for g in gaps_raw.get("gaps", [])]
    except Exception as e:
        echo_error(f"갭 파일 로드 실패: {e}")
        raise click.Abort()

    # 질문 생성
    try:
        generator = InteractiveQuestionGenerator()
        questions = generator.generate_questions(gaps_list, domain)
    except Exception as e:
        echo_error(f"질문 생성 실패: {e}")
        raise click.Abort()

    if not questions:
        echo_info("생성된 질문이 없습니다.")
        return

    echo_info(f"{len(questions)}개 질문이 생성됐습니다.")

    if interactive:
        answers = _run_interactive_qa(questions)
    else:
        echo_info("--no-interactive 모드: 기본값으로 자동 답변합니다.")
        answers = {q.id: q.default_value or "" for q in questions}

    _save_answers(answers, questions, domain, output)
    echo_success(f"답변 저장 완료: {output}")
    echo_info(f"다음 단계: caas refine expand <요구사항> --golden-data <파일> --gaps {gaps}")


# ─────────────────────────────────────────────────────────────
# caas refine expand — 확장만 실행
# ─────────────────────────────────────────────────────────────

@refine_group.command(name="expand")
@click.argument("requirement")
@click.option("--golden-data", "-g", type=click.Path(exists=True), required=True,
              help="golden_data.json 경로")
@click.option("--gaps", type=click.Path(exists=True), default=None,
              help="gaps.json 경로 (없으면 빈 갭 목록 사용)")
@click.option("--output", "-o", type=click.Path(), default="refined_golden.json", show_default=True,
              help="정제된 Golden Data 출력 경로")
@handle_keyboard_interrupt
def refine_expand(requirement, golden_data, gaps, output):
    """Stage 3만 실행: 요구사항 자동 확장.

    \b
    예시:
      caas refine expand "할일 관리 시스템" --golden-data ./golden_data.json
      caas refine expand "챗봇" -g golden.json --gaps gaps.json -o refined.json
    """
    from rich.console import Console

    from caas_framework.refinement.gap_analyzer import RequirementGap
    from caas_framework.refinement.expander import RequirementExpander

    console = Console()

    try:
        concretized, _ = _load_golden_data(golden_data)
    except Exception as e:
        echo_error(f"Golden Data 로드 실패: {e}")
        raise click.Abort()

    # 갭 로드 (선택적)
    gaps_list = []
    if gaps:
        try:
            with open(gaps, "r", encoding="utf-8") as f:
                gaps_raw = json.load(f)
            if isinstance(gaps_raw, list):
                gaps_list = [RequirementGap(**g) for g in gaps_raw]
            else:
                gaps_list = [RequirementGap(**g) for g in gaps_raw.get("gaps", [])]
        except Exception as e:
            echo_warning(f"갭 파일 로드 실패: {e}. 빈 갭 목록으로 진행합니다.")

    try:
        async def _run():
            llm = await _init_llm("openai-expand")
            try:
                expander = RequirementExpander(llm)
                return expander.expand_requirement(requirement, concretized, gaps_list)
            finally:
                await llm.close()

        with console.status("[bold blue]요구사항 확장 중...[/bold blue]", spinner="dots"):
            expanded = asyncio.run(_run())

    except Exception as e:
        echo_error(f"확장 실패: {e}")
        raise click.Abort()

    # 저장
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    merged = expanded.original.model_dump()
    if expanded.auto_expanded_features:
        merged["features"] = (
            merged.get("features", []) +
            [f.model_dump() for f in expanded.auto_expanded_features]
        )
    if expanded.auto_expanded_data_models:
        merged["data_models"] = (
            merged.get("data_models", []) +
            [dm.model_dump() for dm in expanded.auto_expanded_data_models]
        )
    if expanded.auto_expanded_ui_components:
        merged["ui_components"] = (
            merged.get("ui_components", []) +
            [ui.model_dump() for ui in expanded.auto_expanded_ui_components]
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    new_f = len(expanded.auto_expanded_features)
    new_dm = len(expanded.auto_expanded_data_models)
    echo_success(
        f"확장 완료: 기능 +{new_f}개, 데이터모델 +{new_dm}개 추가 → {output}"
    )
    echo_info(f"다음 단계: caas generate --golden-data {output}")
