"""
caas refine 명령어 테스트

갭 분석 → Q&A → 자동 확장 통합 파이프라인 CLI 테스트
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from caas_cli.cli import cli


# ─────────────────────────────────────────────────────────────
# 테스트 픽스처
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def golden_data_file(tmp_path):
    """최소한의 유효한 golden_data.json 생성."""
    data = {
        "project_name": "테스트 프로젝트",
        "description": "테스트용 요구사항",
        "features": [
            {
                "id": "F1",
                "name": "기능1",
                "description": "테스트 기능",
                "priority": "high",
                "acceptance_criteria": ["기준1"],
                "api_contract": {},
                "data_model": {},
                "business_rules": [],
                "test_scenarios": [],
            }
        ],
        "data_models": [],
        "ui_components": [],
        "non_functional_requirements": {
            "security": "",
            "scalability": "",
            "performance": "",
            "reliability": "",
        },
        "workflow_type": "sequential",
        "deployment_target": "docker",
        "boundaries": {
            "always_allowed": [],
            "ask_first": [],
            "never_allowed": [],
        },
        "commands": {
            "install": "pip install -r requirements.txt",
            "test": "pytest tests/",
            "run": "python main.py",
            "lint": "pylint src/",
            "format": "black src/",
        },
        "code_style": {
            "formatter": "black",
            "line_length": 88,
            "use_type_hints": True,
            "docstring_style": "google",
            "import_order": "isort",
        },
        "git_workflow": {
            "branch_naming": "feature/{description}",
            "commit_message_format": "<type>: <subject>",
            "requires_pr": True,
            "main_branch": "main",
        },
    }
    p = tmp_path / "golden_data.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


@pytest.fixture
def mock_gap_result():
    """GapAnalysisResult 목 객체."""
    from caas_framework.refinement.gap_analyzer import GapAnalysisResult, RequirementGap

    gap = RequirementGap(
        gap_type="ambiguous_feature",
        severity="medium",
        description="바이오리듬 기능 미명시",
        affected_feature="F1",
        suggested_fix="바이오리듬 계산 기능 추가",
        auto_fixable=True,
    )
    return GapAnalysisResult(
        total_gaps=1,
        critical_gaps=0,
        high_gaps=0,
        medium_gaps=1,
        low_gaps=0,
        auto_fixable_gaps=1,
        gaps=[gap],
        completeness_score=0.75,
    )


@pytest.fixture
def mock_expanded_result(golden_data_file):
    """ExpandedRequirement 목 객체."""
    from caas_framework.refinement.expander import ExpandedRequirement
    from caas_framework.models.specifications import ConcretizedRequirement

    with open(golden_data_file) as f:
        raw = json.load(f)
    original = ConcretizedRequirement(**raw)

    return ExpandedRequirement(
        original=original,
        auto_expanded_features=[],
        auto_expanded_data_models=[],
        auto_expanded_ui_components=[],
        suggested_nfr={},
        best_practices=[],
        remaining_gaps=[],
        expansion_summary="테스트 확장 완료",
    )


# ─────────────────────────────────────────────────────────────
# caas refine --help
# ─────────────────────────────────────────────────────────────

def test_refine_group_help(runner):
    result = runner.invoke(cli, ["refine", "--help"])
    assert result.exit_code == 0
    assert "요구사항 정제 통합 파이프라인" in result.output
    assert "run" in result.output
    assert "gaps" in result.output
    assert "ask" in result.output
    assert "expand" in result.output


def test_refine_run_help(runner):
    result = runner.invoke(cli, ["refine", "run", "--help"])
    assert result.exit_code == 0
    assert "--golden-data" in result.output
    assert "--domain" in result.output
    assert "--skip-questions" in result.output


def test_refine_gaps_help(runner):
    result = runner.invoke(cli, ["refine", "gaps", "--help"])
    assert result.exit_code == 0
    assert "--golden-data" in result.output


def test_refine_ask_help(runner):
    result = runner.invoke(cli, ["refine", "ask", "--help"])
    assert result.exit_code == 0
    assert "--gaps" in result.output
    assert "--domain" in result.output


def test_refine_expand_help(runner):
    result = runner.invoke(cli, ["refine", "expand", "--help"])
    assert result.exit_code == 0
    assert "--golden-data" in result.output


# ─────────────────────────────────────────────────────────────
# caas refine run — 통합 파이프라인
# ─────────────────────────────────────────────────────────────

def test_refine_run_missing_golden_data(runner):
    """--golden-data 없으면 오류."""
    result = runner.invoke(cli, ["refine", "run", "요구사항"])
    assert result.exit_code != 0
    assert "golden-data" in result.output.lower() or "missing" in result.output.lower()


def test_refine_run_invalid_golden_data(runner, tmp_path):
    """존재하지 않는 golden_data.json 경로 → 오류."""
    result = runner.invoke(
        cli, ["refine", "run", "요구사항", "--golden-data", "/nonexistent/path.json"]
    )
    assert result.exit_code != 0


def test_refine_run_skip_questions_no_interactive(
    runner, golden_data_file, mock_gap_result, mock_expanded_result, tmp_path
):
    """--skip-questions + --no-interactive: Q&A 없이 갭분석+확장만 실행."""
    output_path = str(tmp_path / "refined.json")

    with (
        patch("caas_cli.commands.refine_cmd._init_llm") as mock_init_llm,
        patch(
            "caas_framework.refinement.gap_analyzer.RequirementGapAnalyzer.analyze_gaps",
            return_value=mock_gap_result,
        ),
        patch(
            "caas_framework.refinement.expander.RequirementExpander.expand_requirement",
            return_value=mock_expanded_result,
        ),
    ):
        # _init_llm async mock
        mock_plugin = MagicMock()
        mock_plugin.close = AsyncMock()
        mock_init_llm.return_value = mock_plugin
        mock_init_llm.side_effect = None

        async def fake_init(name=""):
            return mock_plugin
        mock_init_llm.side_effect = fake_init

        result = runner.invoke(
            cli,
            [
                "refine", "run", "테스트 요구사항",
                "--golden-data", golden_data_file,
                "--skip-questions",
                "--no-interactive",
                "--output", output_path,
            ],
        )

    # 출력 파일이 생성됐는지 확인
    assert Path(output_path).exists(), f"Output not created. Exit: {result.exit_code}\n{result.output}"
    with open(output_path) as f:
        data = json.load(f)
    assert "features" in data


def test_refine_run_zero_gaps(runner, golden_data_file, tmp_path):
    """갭이 0개이면 바로 원본 Golden Data를 출력으로 저장."""
    from caas_framework.refinement.gap_analyzer import GapAnalysisResult

    zero_gap_result = GapAnalysisResult(
        total_gaps=0,
        critical_gaps=0,
        high_gaps=0,
        medium_gaps=0,
        low_gaps=0,
        auto_fixable_gaps=0,
        gaps=[],
        completeness_score=1.0,
    )
    output_path = str(tmp_path / "refined.json")

    with (
        patch("caas_cli.commands.refine_cmd._init_llm") as mock_init_llm,
        patch(
            "caas_framework.refinement.gap_analyzer.RequirementGapAnalyzer.analyze_gaps",
            return_value=zero_gap_result,
        ),
    ):
        mock_plugin = MagicMock()
        mock_plugin.close = AsyncMock()
        async def fake_init(name=""):
            return mock_plugin
        mock_init_llm.side_effect = fake_init

        result = runner.invoke(
            cli,
            [
                "refine", "run", "완전한 요구사항",
                "--golden-data", golden_data_file,
                "--output", output_path,
            ],
        )

    assert Path(output_path).exists()
    assert "갭이 없습니다" in result.output or "complete" in result.output.lower()


# ─────────────────────────────────────────────────────────────
# caas refine gaps
# ─────────────────────────────────────────────────────────────

def test_refine_gaps_creates_output_file(runner, golden_data_file, mock_gap_result, tmp_path):
    """gaps 서브커맨드가 gaps.json 파일을 생성한다."""
    output_path = str(tmp_path / "gaps.json")

    with (
        patch("caas_cli.commands.refine_cmd._init_llm") as mock_init_llm,
        patch(
            "caas_framework.refinement.gap_analyzer.RequirementGapAnalyzer.analyze_gaps",
            return_value=mock_gap_result,
        ),
    ):
        mock_plugin = MagicMock()
        mock_plugin.close = AsyncMock()
        async def fake_init(name=""):
            return mock_plugin
        mock_init_llm.side_effect = fake_init

        result = runner.invoke(
            cli,
            [
                "refine", "gaps", "테스트 요구사항",
                "--golden-data", golden_data_file,
                "--output", output_path,
            ],
        )

    assert Path(output_path).exists(), f"Exit: {result.exit_code}\n{result.output}"
    with open(output_path) as f:
        gaps = json.load(f)
    assert isinstance(gaps, list)
    assert len(gaps) == 1
    assert gaps[0]["gap_type"] == "ambiguous_feature"


# ─────────────────────────────────────────────────────────────
# caas refine ask
# ─────────────────────────────────────────────────────────────

def test_refine_ask_no_interactive(runner, tmp_path):
    """--no-interactive: 기본값으로 자동 답변."""
    from caas_framework.refinement.gap_analyzer import RequirementGap
    from caas_framework.refinement.question_generator import Question, QuestionType

    gaps_data = [
        {
            "gap_type": "ambiguous_feature",
            "severity": "medium",
            "description": "테스트 갭",
            "affected_feature": "F1",
            "suggested_fix": "기능 추가",
            "auto_fixable": True,
        }
    ]
    gaps_file = tmp_path / "gaps.json"
    gaps_file.write_text(json.dumps(gaps_data))
    output_path = str(tmp_path / "answers.json")

    mock_question = Question(
        id="q1",
        question_text="UI가 필요한가요?",
        question_type=QuestionType.YES_NO,
        options=None,
        default_value="yes",
        required=False,
        help_text=None,
    )

    with patch(
        "caas_framework.refinement.question_generator.InteractiveQuestionGenerator.generate_questions",
        return_value=[mock_question],
    ):
        result = runner.invoke(
            cli,
            [
                "refine", "ask",
                "--gaps", str(gaps_file),
                "--domain", "CUSTOM",
                "--output", output_path,
                "--no-interactive",
            ],
        )

    assert Path(output_path).exists(), f"Exit: {result.exit_code}\n{result.output}"
    with open(output_path) as f:
        data = json.load(f)
    assert "answers" in data
    assert data["domain"] == "CUSTOM"


# ─────────────────────────────────────────────────────────────
# caas refine expand
# ─────────────────────────────────────────────────────────────

def test_refine_expand_creates_output(
    runner, golden_data_file, mock_expanded_result, tmp_path
):
    """expand 서브커맨드가 refined_golden.json을 생성한다."""
    output_path = str(tmp_path / "refined.json")

    with (
        patch("caas_cli.commands.refine_cmd._init_llm") as mock_init_llm,
        patch(
            "caas_framework.refinement.expander.RequirementExpander.expand_requirement",
            return_value=mock_expanded_result,
        ),
    ):
        mock_plugin = MagicMock()
        mock_plugin.close = AsyncMock()
        async def fake_init(name=""):
            return mock_plugin
        mock_init_llm.side_effect = fake_init

        result = runner.invoke(
            cli,
            [
                "refine", "expand", "테스트 요구사항",
                "--golden-data", golden_data_file,
                "--output", output_path,
            ],
        )

    assert Path(output_path).exists(), f"Exit: {result.exit_code}\n{result.output}"
    with open(output_path) as f:
        data = json.load(f)
    assert "features" in data
    # project_name은 system_scope 내부 또는 최상위에 위치
    assert "system_scope" in data or "project_name" in data


def test_refine_expand_with_gaps_file(
    runner, golden_data_file, mock_expanded_result, tmp_path
):
    """--gaps 옵션으로 갭 파일을 전달할 수 있다."""
    gaps_data = [
        {
            "gap_type": "ambiguous_feature",
            "severity": "high",
            "description": "테스트",
            "affected_feature": "F1",
            "suggested_fix": "수정",
            "auto_fixable": False,
        }
    ]
    gaps_file = tmp_path / "gaps.json"
    gaps_file.write_text(json.dumps(gaps_data))
    output_path = str(tmp_path / "refined.json")

    with (
        patch("caas_cli.commands.refine_cmd._init_llm") as mock_init_llm,
        patch(
            "caas_framework.refinement.expander.RequirementExpander.expand_requirement",
            return_value=mock_expanded_result,
        ),
    ):
        mock_plugin = MagicMock()
        mock_plugin.close = AsyncMock()
        async def fake_init(name=""):
            return mock_plugin
        mock_init_llm.side_effect = fake_init

        result = runner.invoke(
            cli,
            [
                "refine", "expand", "테스트",
                "--golden-data", golden_data_file,
                "--gaps", str(gaps_file),
                "--output", output_path,
            ],
        )

    assert Path(output_path).exists(), f"Exit: {result.exit_code}\n{result.output}"
