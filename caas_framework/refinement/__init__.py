"""
Requirement Refinement Module

요구사항 정제 및 확장 모듈
- Gap Analysis: 요구사항 갭 분석
- Auto-Expansion: 자동 확장
- Interactive Elicitation: 인터랙티브 수집
"""

from .expander import AutoFixResult, ExpandedRequirement, RequirementExpander
from .gap_analyzer import GapAnalysisResult, GapType, RequirementGap, RequirementGapAnalyzer
from .question_generator import (
    InteractiveQuestionGenerator,
    Question,
    QuestionnaireResult,
    QuestionType,
)

__all__ = [
    # Gap Analysis
    "GapType",
    "RequirementGap",
    "RequirementGapAnalyzer",
    "GapAnalysisResult",
    # Expansion
    "RequirementExpander",
    "ExpandedRequirement",
    "AutoFixResult",
    # Questions
    "QuestionType",
    "Question",
    "QuestionnaireResult",
    "InteractiveQuestionGenerator",
]
