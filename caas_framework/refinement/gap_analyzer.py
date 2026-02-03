"""
Requirement Gap Analyzer

요구사항 갭 분석기 - 누락되거나 불충분한 요구사항 항목 탐지
"""

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..models.specifications import ConcretizedRequirement
from ..utils import JsonExtractor, LLMHelper, ObjectAccessor


class GapType(str, Enum):
    """갭 타입"""

    MISSING_NFR = "non_functional_requirements"
    MISSING_DATA_MODEL = "data_model"
    MISSING_UI_SPEC = "ui_specification"
    AMBIGUOUS_FEATURE = "ambiguous_feature"
    MISSING_CONSTRAINTS = "constraints"
    MISSING_ACCEPTANCE = "acceptance_criteria"
    MISSING_ERROR_HANDLING = "error_handling"
    MISSING_SECURITY = "security"
    MISSING_PERFORMANCE = "performance"
    INCOMPLETE_WORKFLOW = "incomplete_workflow"


class RequirementGap(BaseModel):
    """요구사항 갭"""

    gap_type: GapType
    description: str
    severity: str = Field(..., description="Severity level: critical, high, medium, low")
    suggestions: List[str] = Field(default_factory=list)
    auto_fixable: bool = False
    related_feature_id: Optional[str] = None


class GapAnalysisResult(BaseModel):
    """갭 분석 결과"""

    total_gaps: int
    critical_gaps: int
    high_gaps: int
    medium_gaps: int
    low_gaps: int
    auto_fixable_gaps: int
    gaps: List[RequirementGap]
    completeness_score: float = Field(..., description="0.0 ~ 1.0, higher is better")


class RequirementGapAnalyzer:
    """요구사항 갭 분석기"""

    def __init__(self, llm_client=None, domain_checklists_path: Optional[Path] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (선택적)
            domain_checklists_path: 도메인 체크리스트 경로
        """
        self.llm = llm_client
        self.domain_checklists = self._load_domain_checklists(domain_checklists_path)
        self._cache = {}  # 갭 분석 결과 캐시

    def analyze_gaps(
        self, requirement: str, concretized: ConcretizedRequirement
    ) -> GapAnalysisResult:
        """
        요구사항 갭 분석 (캐싱 지원)

        Args:
            requirement: 원본 요구사항 텍스트
            concretized: 구체화된 요구사항

        Returns:
            GapAnalysisResult: 갭 분석 결과
        """
        # ✅ 캐시 확인
        cache_key = self._generate_cache_key(requirement, concretized)
        if cache_key in self._cache:
            return self._cache[cache_key]

        gaps: List[RequirementGap] = []

        # ✅ 0. LLM 기반 원본 요구사항 분석 (새로 추가!)
        if self.llm and requirement:
            llm_gaps = self._analyze_requirement_with_llm(requirement, concretized)
            gaps.extend(llm_gaps)

        # 1. 비기능 요구사항 체크 (Rule-based, 보완용)
        nfr_gaps = self._check_nfr_gaps(concretized)
        gaps.extend(nfr_gaps)

        # 2. 데이터 모델 체크
        data_gaps = self._check_data_model_gaps(concretized)
        gaps.extend(data_gaps)

        # 3. UI 컴포넌트 체크
        ui_gaps = self._check_ui_gaps(concretized)
        gaps.extend(ui_gaps)

        # 4. 기능별 인수 기준 체크
        acceptance_gaps = self._check_acceptance_criteria_gaps(concretized)
        gaps.extend(acceptance_gaps)

        # 5. 도메인 특화 체크
        domain_gaps = self._check_domain_specific_gaps(concretized)
        gaps.extend(domain_gaps)

        # 6. 워크플로우 완전성 체크
        workflow_gaps = self._check_workflow_completeness(concretized)
        gaps.extend(workflow_gaps)

        # 중복 제거 (LLM + Rule-based 병합 시)
        gaps = self._deduplicate_gaps(gaps)

        # 통계 계산 (복잡도 기반 가중치 적용)
        result = self._compute_result(gaps, spec=concretized)

        # ✅ 캐시에 저장
        self._cache[cache_key] = result

        return result

    def _generate_cache_key(self, requirement: str, concretized: ConcretizedRequirement) -> str:
        """
        캐시 키 생성 (요구사항 + Golden Data 해시)

        Args:
            requirement: 원본 요구사항
            concretized: 구체화된 요구사항

        Returns:
            str: MD5 해시 키
        """
        # 요구사항 텍스트 + Golden Data를 결합하여 해시 생성
        content = f"{requirement}_{concretized.model_dump_json()}"
        return hashlib.md5(content.encode()).hexdigest()

    def _check_nfr_gaps(self, concretized: ConcretizedRequirement) -> List[RequirementGap]:
        """비기능 요구사항 갭 체크"""
        gaps = []
        nfr = concretized.non_functional_requirements

        # 보안 요구사항
        if not ObjectAccessor.get_value(nfr, "security"):
            gaps.append(
                RequirementGap(
                    gap_type=GapType.MISSING_SECURITY,
                    description="보안 요구사항이 명시되지 않았습니다",
                    severity="high",
                    suggestions=[
                        "사용자 인증이 필요한가요?",
                        "개인정보를 처리하나요? (GDPR, 개인정보보호법)",
                        "데이터 암호화가 필요한가요?",
                        "접근 권한 관리가 필요한가요?",
                    ],
                    auto_fixable=False,
                )
            )

        # 성능 요구사항
        if not ObjectAccessor.get_value(nfr, "performance"):
            gaps.append(
                RequirementGap(
                    gap_type=GapType.MISSING_PERFORMANCE,
                    description="성능 요구사항이 명시되지 않았습니다",
                    severity="medium",
                    suggestions=[
                        "예상 동시 사용자 수는?",
                        "응답 시간 요구사항은? (예: 페이지 로드 3초 이내)",
                        "처리할 데이터 규모는?",
                    ],
                    auto_fixable=True,  # 기본값 제안 가능
                )
            )

        # 확장성
        if not ObjectAccessor.get_value(nfr, "scalability"):
            gaps.append(
                RequirementGap(
                    gap_type=GapType.MISSING_NFR,
                    description="확장성 요구사항이 명시되지 않았습니다",
                    severity="low",
                    suggestions=[
                        "향후 사용자 증가를 어느 정도 예상하나요?",
                        "수평 확장(scale-out)이 필요한가요?",
                    ],
                    auto_fixable=True,
                )
            )

        # 신뢰성
        if not ObjectAccessor.get_value(nfr, "reliability"):
            gaps.append(
                RequirementGap(
                    gap_type=GapType.MISSING_NFR,
                    description="신뢰성 요구사항이 명시되지 않았습니다",
                    severity="medium",
                    suggestions=[
                        "목표 가용성은? (예: 99.9% uptime)",
                        "데이터 백업 전략은?",
                        "장애 복구 시간(RTO)은?",
                    ],
                    auto_fixable=True,
                )
            )

        return gaps

    def _check_data_model_gaps(self, concretized: ConcretizedRequirement) -> List[RequirementGap]:
        """데이터 모델 갭 체크"""
        gaps = []

        if len(concretized.data_models) == 0:
            gaps.append(
                RequirementGap(
                    gap_type=GapType.MISSING_DATA_MODEL,
                    description="저장할 데이터 구조가 정의되지 않았습니다",
                    severity="critical",
                    suggestions=[
                        "어떤 데이터를 저장해야 하나요?",
                        "엔티티(객체)는 무엇인가요?",
                        "각 엔티티의 속성은?",
                    ],
                    auto_fixable=True,  # LLM으로 추론 가능
                )
            )
        else:
            # 각 데이터 모델의 완전성 체크
            data_models = concretized.data_models if concretized.data_models else []
            for dm in data_models:
                if len(dm.attributes) == 0:
                    gaps.append(
                        RequirementGap(
                            gap_type=GapType.MISSING_DATA_MODEL,
                            description=f"데이터 모델 '{dm.entity_name}'의 속성이 정의되지 않았습니다",
                            severity="high",
                            suggestions=[f"{dm.entity_name}은(는) 어떤 정보를 가지고 있나요?"],
                            auto_fixable=True,
                        )
                    )

        return gaps

    def _check_ui_gaps(self, concretized: ConcretizedRequirement) -> List[RequirementGap]:
        """UI 갭 체크"""
        gaps = []

        # UI 컴포넌트가 전혀 없는 경우
        if len(concretized.ui_components) == 0:
            # 도메인에 따라 UI가 필요 없을 수도 있음 (예: API 서비스)
            if concretized.domain not in [
                "API_SERVICE",
                "DATA_PIPELINE",
                "BACKEND_SERVICE",
            ]:
                gaps.append(
                    RequirementGap(
                        gap_type=GapType.MISSING_UI_SPEC,
                        description="사용자 인터페이스가 정의되지 않았습니다",
                        severity="medium",
                        suggestions=[
                            "웹 UI가 필요한가요?",
                            "어떤 화면(페이지)이 필요한가요?",
                            "각 화면에서 사용자가 할 수 있는 작업은?",
                        ],
                        auto_fixable=True,
                    )
                )

        return gaps

    def _check_acceptance_criteria_gaps(
        self, concretized: ConcretizedRequirement
    ) -> List[RequirementGap]:
        """인수 기준 갭 체크"""
        gaps = []

        features = concretized.features if concretized.features else []
        for feature in features:
            if not feature.acceptance_criteria or len(feature.acceptance_criteria) == 0:
                gaps.append(
                    RequirementGap(
                        gap_type=GapType.MISSING_ACCEPTANCE,
                        description=f"기능 '{feature.name}'의 완료 기준이 명확하지 않습니다",
                        severity="medium",
                        suggestions=[
                            "이 기능이 완료되었다는 것을 어떻게 확인하나요?",
                            "성공/실패 조건은 무엇인가요?",
                            "예상되는 결과물은?",
                        ],
                        auto_fixable=True,
                        related_feature_id=feature.id,
                    )
                )

            # 모호한 인수 기준 탐지
            if feature.acceptance_criteria:
                for criterion in feature.acceptance_criteria:
                    if self._is_ambiguous(criterion):
                        gaps.append(
                            RequirementGap(
                                gap_type=GapType.AMBIGUOUS_FEATURE,
                                description=f"기능 '{feature.name}'의 인수 기준이 모호합니다: '{criterion}'",
                                severity="low",
                                suggestions=[
                                    "구체적인 수치나 기준을 제시해주세요",
                                    "측정 가능한 기준으로 변경해주세요",
                                ],
                                auto_fixable=False,
                                related_feature_id=feature.id,
                            )
                        )

        return gaps

    def _check_domain_specific_gaps(
        self, concretized: ConcretizedRequirement
    ) -> List[RequirementGap]:
        """도메인별 필수 항목 체크"""
        gaps = []
        domain = concretized.domain
        checklist = self.domain_checklists.get(domain, [])

        for item in checklist:
            if not self._has_requirement(concretized, item):
                gaps.append(
                    RequirementGap(
                        gap_type=GapType.MISSING_CONSTRAINTS,
                        description=f"도메인 '{domain}'에 일반적으로 필요한 '{item['name']}' 항목이 누락되었습니다",
                        severity=item["severity"],
                        suggestions=item["questions"],
                        auto_fixable=item.get("auto_fixable", False),
                    )
                )

        return gaps

    def _check_workflow_completeness(
        self, concretized: ConcretizedRequirement
    ) -> List[RequirementGap]:
        """워크플로우 완전성 체크"""
        gaps = []

        # 에러 처리 확인
        features = concretized.features if concretized.features else []
        error_handling_mentioned = any(
            "에러" in f.description or "오류" in f.description or "error" in f.description.lower()
            for f in features
        )

        if not error_handling_mentioned:
            gaps.append(
                RequirementGap(
                    gap_type=GapType.MISSING_ERROR_HANDLING,
                    description="에러 처리 방안이 명시되지 않았습니다",
                    severity="medium",
                    suggestions=[
                        "오류 발생 시 어떻게 처리하나요?",
                        "사용자에게 어떤 메시지를 보여주나요?",
                        "로그는 어떻게 남기나요?",
                    ],
                    auto_fixable=True,
                )
            )

        return gaps

    def _is_ambiguous(self, text: str) -> bool:
        """텍스트가 모호한지 판단"""
        ambiguous_terms = [
            "적절한",
            "충분한",
            "빠른",
            "좋은",
            "나쁜",
            "많은",
            "적은",
            "대부분",
            "일반적으로",
            "보통",
            "적당한",
        ]
        return any(term in text for term in ambiguous_terms)

    def _has_requirement(self, concretized: ConcretizedRequirement, item: Dict) -> bool:
        """특정 요구사항이 있는지 확인"""
        keywords = item.get("keywords", [])

        # 기능 설명에서 키워드 검색
        features = concretized.features if concretized.features else []
        for feature in features:
            if any(keyword in feature.description for keyword in keywords):
                return True

        # NFR에서 검색
        nfr = concretized.non_functional_requirements

        nfr_text = (
            f"{ObjectAccessor.get_value(nfr,'security')} "
            f"{ObjectAccessor.get_value(nfr,'performance')} "
            f"{ObjectAccessor.get_value(nfr,'scalability')} "
            f"{ObjectAccessor.get_value(nfr,'reliability')}"
        )
        if any(keyword in nfr_text for keyword in keywords):
            return True

        return False

    def _estimate_complexity(self, spec: ConcretizedRequirement) -> int:
        """
        프로젝트 복잡도 추정 (1~10)

        Args:
            spec: 구체화된 요구사항

        Returns:
            int: 복잡도 점수 (1=매우 간단, 10=매우 복잡)
        """
        score = 0

        # 1. 기능 개수 (최대 5점)
        feature_count = len(spec.features)
        if feature_count >= 20:
            score += 5
        elif feature_count >= 10:
            score += 4
        elif feature_count >= 5:
            score += 3
        elif feature_count >= 3:
            score += 2
        else:
            score += 1

        # 2. 데이터 모델 복잡도 (최대 3점)
        data_model_count = len(spec.data_models)
        if data_model_count >= 10:
            score += 3
        elif data_model_count >= 5:
            score += 2
        elif data_model_count >= 1:
            score += 1

        # 3. UI 컴포넌트 수 (최대 2점)
        ui_count = len(spec.ui_components)
        if ui_count >= 10:
            score += 2
        elif ui_count >= 5:
            score += 1

        # 4. 도메인 복잡도 (최대 3점)
        complex_domains = {
            "FINANCE": 3,
            "HEALTHCARE": 3,
            "E_COMMERCE": 2,
            "CHATBOT": 2,
            "DATA_PIPELINE": 2,
        }
        domain_score = complex_domains.get(spec.domain, 1)
        score += domain_score

        # 5. NFR 정의 여부 (복잡도 감소 요인)
        nfr = spec.non_functional_requirements

        nfr_defined = sum(
            [
                1
                for key in ["security", "performance", "scalability", "reliability"]
                if ObjectAccessor.get_value(nfr, key)
            ]
        )
        # NFR이 잘 정의되어 있으면 상대적으로 간단 (복잡도 감소)
        if nfr_defined >= 3:
            score -= 1

        return max(1, min(score, 10))

    def _compute_result(
        self, gaps: List[RequirementGap], spec: Optional[ConcretizedRequirement] = None
    ) -> GapAnalysisResult:
        """
        갭 분석 결과 계산 (복잡도 기반 가중치 적용)

        Args:
            gaps: 탐지된 갭 목록
            spec: 구체화된 요구사항 (복잡도 계산용)

        Returns:
            GapAnalysisResult
        """
        total = len(gaps)
        critical = sum(1 for g in gaps if g.severity == "critical")
        high = sum(1 for g in gaps if g.severity == "high")
        medium = sum(1 for g in gaps if g.severity == "medium")
        low = sum(1 for g in gaps if g.severity == "low")
        auto_fixable = sum(1 for g in gaps if g.auto_fixable)

        # 완성도 점수 계산 (0.0 ~ 1.0)
        if total == 0:
            completeness_score = 1.0
        else:
            # 심각도별 가중치
            weighted_gaps = critical * 4 + high * 3 + medium * 2 + low * 1

            # 동적 최대 갭 수 계산 (프로젝트 복잡도 기반)
            if spec:
                complexity = self._estimate_complexity(spec)
                # 복잡도가 높을수록 더 많은 갭이 허용됨
                max_possible_gaps = 10 + (complexity * 2)  # 12~30개
            else:
                max_possible_gaps = 20  # 기본값

            max_weighted_score = max_possible_gaps * 4  # 모두 critical이면
            completeness_score = max(0.0, 1.0 - (weighted_gaps / max_weighted_score))

        return GapAnalysisResult(
            total_gaps=total,
            critical_gaps=critical,
            high_gaps=high,
            medium_gaps=medium,
            low_gaps=low,
            auto_fixable_gaps=auto_fixable,
            gaps=gaps,
            completeness_score=completeness_score,
        )

    def _load_domain_checklists(self, checklists_path: Optional[Path]) -> Dict[str, List[Dict]]:
        """도메인별 체크리스트 로드"""
        if checklists_path and checklists_path.exists():
            with open(checklists_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # 기본 체크리스트
        return self._get_default_checklists()

    def _get_default_checklists(self) -> Dict[str, List[Dict]]:
        """기본 도메인 체크리스트"""
        return {
            "TASK_MANAGEMENT": [
                {
                    "name": "사용자 권한 관리",
                    "severity": "high",
                    "keywords": ["권한", "인증", "로그인", "사용자"],
                    "questions": ["누가 할일을 생성/수정/삭제할 수 있나요?"],
                    "auto_fixable": False,
                },
                {
                    "name": "알림 시스템",
                    "severity": "medium",
                    "keywords": ["알림", "notification", "메일", "푸시"],
                    "questions": ["마감일 임박 시 알림이 필요한가요?"],
                    "auto_fixable": False,
                },
            ],
            "E_COMMERCE": [
                {
                    "name": "결제 시스템",
                    "severity": "critical",
                    "keywords": ["결제", "payment", "구매", "카드"],
                    "questions": ["어떤 결제 수단을 지원하나요?"],
                    "auto_fixable": False,
                },
                {
                    "name": "재고 관리",
                    "severity": "high",
                    "keywords": ["재고", "inventory", "수량"],
                    "questions": ["재고가 부족할 때 어떻게 처리하나요?"],
                    "auto_fixable": False,
                },
            ],
            "HEALTHCARE": [
                {
                    "name": "환자 정보 보안",
                    "severity": "critical",
                    "keywords": ["환자", "의료", "개인정보"],
                    "questions": ["HIPAA/개인정보보호법 준수가 필요한가요?"],
                    "auto_fixable": False,
                },
            ],
            "FINANCE": [
                {
                    "name": "금융 규제 준수",
                    "severity": "critical",
                    "keywords": ["금융", "거래", "계좌"],
                    "questions": ["금융 규제(금융위원회 등) 준수가 필요한가요?"],
                    "auto_fixable": False,
                },
                {
                    "name": "감사 추적",
                    "severity": "high",
                    "keywords": ["감사", "audit", "로그"],
                    "questions": ["모든 거래 내역을 추적해야 하나요?"],
                    "auto_fixable": False,
                },
            ],
        }

    def _analyze_requirement_with_llm(
        self, requirement: str, concretized: ConcretizedRequirement
    ) -> List[RequirementGap]:
        """LLM으로 원본 요구사항 텍스트 직접 분석"""

        # NFR 상태 요약
        nfr = concretized.non_functional_requirements

        prompt = f"""당신은 요구사항 분석 전문가입니다. 다음 요구사항을 분석하고, 누락되거나 불충분한 항목을 탐지하세요.

# 원본 요구사항
{requirement}

# 현재 분석된 구조 (Golden Data)
- 도메인: {concretized.domain}
- 프로젝트명: {concretized.project_name}
- 기능 수: {len(concretized.features)}
- 데이터 모델 수: {len(concretized.data_models)}
- UI 컴포넌트 수: {len(concretized.ui_components)}

# NFR 현황
- 보안: {ObjectAccessor.get_value(nfr,'security') or "미정의"}
- 성능: {ObjectAccessor.get_value(nfr,'performance') or "미정의"}
- 확장성: {ObjectAccessor.get_value(nfr,'scalability') or "미정의"}
- 신뢰성: {ObjectAccessor.get_value(nfr,'reliability') or "미정의"}

# 분석 요청
다음 관점에서 갭을 찾아주세요:

1. **보안 요구사항**: 인증, 권한, 데이터 암호화, 개인정보 보호
2. **성능 요구사항**: 응답시간, 동시 사용자, 처리량, 데이터 규모
3. **데이터 관련**: 필요한 데이터 모델, 데이터 보관 기간, 백업 전략
4. **사용자 경험**: 필요한 UI/UX, 에러 처리, 사용자 피드백
5. **운영 요구사항**: 배포 방식, 모니터링, 로깅, 장애 복구
6. **비즈니스 제약**: 예산, 일정, 규제 준수, 통합 요구사항

# 응답 형식 (JSON 배열)
각 갭은 다음 형식으로:
[
  {{
    "gap_type": "MISSING_SECURITY",
    "description": "구체적인 갭 설명",
    "severity": "critical",
    "suggestions": ["제안1", "제안2", "제안3"],
    "auto_fixable": false,
    "reasoning": "이 갭을 중요하게 판단한 이유"
  }}
]

**gap_type 옵션**: MISSING_SECURITY, MISSING_PERFORMANCE, MISSING_DATA_MODEL, MISSING_UI_SPEC, MISSING_CONSTRAINTS, MISSING_ACCEPTANCE, MISSING_ERROR_HANDLING, MISSING_NFR, AMBIGUOUS_FEATURE, INCOMPLETE_WORKFLOW

**severity 옵션**: critical, high, medium, low

**중요**:
- 원본 요구사항 텍스트에서 언급되지 않았지만 일반적으로 필요한 항목만 갭으로 보고
- 이미 충분히 명시된 항목은 갭으로 보고하지 마세요
- 도메인({concretized.domain})에 맞는 관점에서 분석하세요
- 최대 10개 갭까지만 보고 (우선순위 높은 것 위주)"""

        try:
            # LLM 호출
            content = LLMHelper.invoke_with_message(self.llm, prompt)

            # JSON 추출 및 파싱
            gaps_data = JsonExtractor.safe_parse(content, default=[])

            # RequirementGap 객체로 변환
            llm_gaps = []
            for gap_data in gaps_data:
                try:
                    # gap_type 검증
                    gap_type_str = gap_data.get("gap_type", "MISSING_NFR")
                    try:
                        gap_type = GapType(gap_type_str)
                    except ValueError:
                        # 유효하지 않은 gap_type은 MISSING_NFR로 대체
                        gap_type = GapType.MISSING_NFR

                    gap = RequirementGap(
                        gap_type=gap_type,
                        description=gap_data.get("description", ""),
                        severity=gap_data.get("severity", "medium"),
                        suggestions=gap_data.get("suggestions", []),
                        auto_fixable=gap_data.get("auto_fixable", False),
                        related_feature_id=gap_data.get("related_feature_id"),
                    )
                    llm_gaps.append(gap)
                except Exception:
                    # 개별 갭 파싱 실패 시 스킵
                    continue

            return llm_gaps

        except Exception:
            # LLM 분석 실패 시 빈 리스트 (Rule-based로 대체)
            return []

    def _deduplicate_gaps(self, gaps: List[RequirementGap]) -> List[RequirementGap]:
        """중복된 갭 제거 (LLM + Rule-based 병합 시)"""
        seen = set()
        unique_gaps = []

        for gap in gaps:
            # 갭 타입과 설명의 일부로 중복 판단
            key = (gap.gap_type, gap.description[:50])
            if key not in seen:
                seen.add(key)
                unique_gaps.append(gap)

        return unique_gaps


def analyze_requirement_gaps(
    requirement: str,
    concretized: ConcretizedRequirement,
    llm_client=None,
) -> GapAnalysisResult:
    """
    Helper function - 요구사항 갭 분석

    Args:
        requirement: 원본 요구사항
        concretized: 구체화된 요구사항
        llm_client: LLM 클라이언트 (선택적)

    Returns:
        GapAnalysisResult
    """
    analyzer = RequirementGapAnalyzer(llm_client=llm_client)
    return analyzer.analyze_gaps(requirement, concretized)
