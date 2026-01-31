"""
Interactive Question Generator

인터랙티브 질문 생성기 - 갭을 채우기 위한 사용자 질문 생성
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .gap_analyzer import RequirementGap, GapType
from ..utils import JsonExtractor, LLMHelper


class QuestionType(str, Enum):
    """질문 타입"""

    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    TEXT_INPUT = "text_input"
    NUMBER_INPUT = "number_input"
    YES_NO = "yes_no"
    RANGE_SLIDER = "range_slider"


class Question(BaseModel):
    """질문"""

    id: str
    question_text: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    default_value: Optional[Any] = None
    required: bool = True
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    conditional_on: Optional[str] = None  # 조건부 질문
    conditional_value: Optional[Any] = None  # 조건 값


class QuestionnaireResult(BaseModel):
    """설문 결과"""

    answers: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(
        default=1.0, description="0.0 ~ 1.0"
    )
    remaining_ambiguities: List[str] = Field(default_factory=list)


class InteractiveQuestionGenerator:
    """인터랙티브 질문 생성기"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 클라이언트 (선택적)
        """
        self.llm = llm_client
        # Question templates (currently not loaded from external file)
        self.question_templates = {}

    def generate_questions(
        self, gaps: List[RequirementGap], domain: str
    ) -> List[Question]:
        """
        갭 기반 질문 생성

        Args:
            gaps: 요구사항 갭 목록
            domain: 도메인

        Returns:
            List[Question]: 질문 목록
        """
        questions = []

        # ✅ 1. LLM 기반 동적 질문 생성 (우선)
        if self.llm and gaps:
            llm_questions = self._generate_dynamic_questions(gaps, domain)
            questions.extend(llm_questions)

        # 2. Rule-based 질문 (보완용)
        for gap in gaps:
            if gap.severity in ["critical", "high"] and not gap.auto_fixable:
                q = self._create_question_from_gap(gap, domain)
                if q:
                    questions.append(q)

        # 3. 도메인별 표준 질문
        domain_questions = self._get_domain_questions(domain)
        questions.extend(domain_questions)

        # 4. 중복 제거
        questions = self._deduplicate_questions(questions)

        # 5. 질문 순서 최적화
        optimized = self._optimize_question_order(questions)

        return optimized

    def _create_question_from_gap(
        self, gap: RequirementGap, domain: str
    ) -> Optional[Question]:
        """갭에서 질문 생성"""

        if gap.gap_type == GapType.MISSING_SECURITY:
            return Question(
                id="nfr_security_auth",
                question_text="사용자 인증이 필요한가요?",
                question_type=QuestionType.YES_NO,
                default_value="yes",
                help_text="로그인/회원가입 기능 필요 여부",
            )

        elif gap.gap_type == GapType.MISSING_PERFORMANCE:
            return Question(
                id="nfr_performance_users",
                question_text="예상 동시 사용자 수는 얼마나 되나요?",
                question_type=QuestionType.SINGLE_CHOICE,
                options=[
                    "소규모 (1-100명)",
                    "중규모 (100-1,000명)",
                    "대규모 (1,000-10,000명)",
                    "초대규모 (10,000명 이상)",
                ],
                default_value="소규모 (1-100명)",
                help_text="시스템의 성능 및 인프라 구성에 영향을 줍니다",
            )

        elif gap.gap_type == GapType.MISSING_DATA_MODEL:
            return Question(
                id="data_retention",
                question_text="데이터 보관 기간은 어떻게 되나요?",
                question_type=QuestionType.SINGLE_CHOICE,
                options=["영구 보관", "1년", "3년", "5년", "커스텀"],
                default_value="영구 보관",
                help_text="개인정보보호법 준수를 위해 필요합니다",
            )

        elif gap.gap_type == GapType.MISSING_UI_SPEC:
            return Question(
                id="ui_framework",
                question_text="선호하는 프론트엔드 프레임워크가 있나요?",
                question_type=QuestionType.SINGLE_CHOICE,
                options=["Streamlit (간단)", "Gradio (ML 친화)", "React (전문)", "자동 선택"],
                default_value="자동 선택",
                help_text="자동 선택 시 프로젝트에 최적화된 프레임워크를 선택합니다",
            )

        elif gap.gap_type == GapType.MISSING_CONSTRAINTS:
            # 도메인별 제약사항 질문
            if "결제" in gap.description:
                return Question(
                    id="payment_methods",
                    question_text="지원할 결제 수단을 선택하세요",
                    question_type=QuestionType.MULTI_CHOICE,
                    options=[
                        "신용카드",
                        "계좌이체",
                        "카카오페이",
                        "네이버페이",
                        "페이팔",
                    ],
                    help_text="여러 개 선택 가능합니다",
                )
            elif "권한" in gap.description:
                return Question(
                    id="auth_roles",
                    question_text="사용자 역할(Role)이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                    help_text="관리자, 일반 사용자 등의 역할 구분",
                )

        # 매칭되는 템플릿이 없으면 None 반환
        # (동적 질문 생성은 _generate_dynamic_questions 메서드 사용)
        return None

    def _generate_dynamic_questions(
        self, gaps: List[RequirementGap], domain: str
    ) -> List[Question]:
        """
        LLM으로 갭 기반 맞춤형 질문 생성

        Args:
            gaps: 요구사항 갭 목록
            domain: 도메인

        Returns:
            List[Question]: 생성된 질문 목록
        """
        if not gaps:
            return []

        # 질문이 필요한 갭만 선택 (auto_fixable=False)
        manual_gaps = [g for g in gaps if not g.auto_fixable and g.severity in ["critical", "high"]]

        if not manual_gaps:
            return []

        # 갭을 포맷팅
        gaps_text = self._format_gaps_for_prompt(manual_gaps)

        prompt = f"""당신은 요구사항 수집 전문가입니다. 다음 갭을 해결하기 위한 질문을 생성하세요.

# 도메인
{domain}

# 발견된 갭 (사용자 입력 필요)
{gaps_text}

# 질문 생성 요청
각 갭에 대해 사용자에게 물어볼 질문을 생성하세요.

# 질문 타입 설명
- SINGLE_CHOICE: 여러 옵션 중 하나 선택
- MULTI_CHOICE: 여러 옵션 중 복수 선택
- YES_NO: 예/아니오
- TEXT_INPUT: 텍스트 직접 입력
- NUMBER_INPUT: 숫자 입력

# 응답 형식 (JSON 배열)
[
  {{
    "id": "unique_id_1",
    "question_text": "사용자에게 물어볼 질문",
    "question_type": "SINGLE_CHOICE",
    "options": ["옵션1", "옵션2", "옵션3"],
    "default_value": "옵션1",
    "help_text": "질문에 대한 설명",
    "placeholder": null
  }},
  {{
    "id": "unique_id_2",
    "question_text": "다른 질문",
    "question_type": "YES_NO",
    "options": null,
    "default_value": "yes",
    "help_text": "설명",
    "placeholder": null
  }}
]

**중요 규칙**:
1. 질문은 명확하고 구체적으로 작성
2. SINGLE_CHOICE/MULTI_CHOICE는 options 필수 (3-5개)
3. TEXT_INPUT/NUMBER_INPUT은 placeholder 제공
4. 도메인({domain})에 맞는 용어 사용
5. 사용자가 쉽게 답할 수 있도록
6. 최대 5개 질문까지만 생성
7. id는 snake_case로 (예: nfr_security_auth)"""

        try:
            # LLM 호출
            content = LLMHelper.invoke_with_message(self.llm, prompt)

            # JSON 추출 및 파싱
            questions_data = JsonExtractor.safe_parse(content, default=[])

            # Question 객체로 변환
            questions = []
            for q_data in questions_data:
                try:
                    # question_type 검증
                    q_type_str = q_data.get("question_type", "TEXT_INPUT")
                    try:
                        q_type = QuestionType(q_type_str)
                    except ValueError:
                        # 유효하지 않은 타입은 TEXT_INPUT으로 대체
                        q_type = QuestionType.TEXT_INPUT

                    question = Question(
                        id=q_data.get("id", f"llm_q_{len(questions)}"),
                        question_text=q_data.get("question_text", ""),
                        question_type=q_type,
                        options=q_data.get("options"),
                        default_value=q_data.get("default_value"),
                        help_text=q_data.get("help_text"),
                        placeholder=q_data.get("placeholder"),
                        required=True  # 기본적으로 필수
                    )
                    questions.append(question)
                except Exception:
                    continue

            return questions

        except Exception as e:
            # LLM 질문 생성 실패 시 빈 리스트 (Rule-based로 대체)
            return []

    def _format_gaps_for_prompt(self, gaps: List[RequirementGap]) -> str:
        """LLM 프롬프트용 갭 포맷"""
        lines = []
        for i, gap in enumerate(gaps, 1):
            lines.append(f"{i}. [{gap.severity.upper()}] {gap.description}")
            if gap.suggestions:
                lines.append(f"   제안: {', '.join(gap.suggestions[:3])}")
        return "\n".join(lines)

    def _get_domain_questions(self, domain: str) -> List[Question]:
        """도메인별 표준 질문"""

        templates = {
            "TASK_MANAGEMENT": [
                Question(
                    id="task_auth_required",
                    question_text="사용자 로그인이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                    help_text="개인용이면 불필요, 팀용이면 필요",
                ),
                Question(
                    id="task_team_collaboration",
                    question_text="팀 협업 기능이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="no",
                    conditional_on="task_auth_required",
                    conditional_value="yes",
                    help_text="할일 공유, 댓글, 멘션 등의 기능",
                ),
                Question(
                    id="task_notification_channels",
                    question_text="알림을 어떻게 받고 싶으신가요?",
                    question_type=QuestionType.MULTI_CHOICE,
                    options=["이메일", "푸시 알림", "SMS", "슬랙 연동"],
                    help_text="여러 개 선택 가능합니다",
                ),
                Question(
                    id="task_priority_levels",
                    question_text="우선순위는 몇 단계로 구분하나요?",
                    question_type=QuestionType.SINGLE_CHOICE,
                    options=[
                        "3단계 (높음/중간/낮음)",
                        "5단계 (P0~P4)",
                        "커스텀",
                    ],
                    default_value="3단계 (높음/중간/낮음)",
                ),
            ],
            "E_COMMERCE": [
                Question(
                    id="ecom_payment_methods",
                    question_text="지원할 결제 수단을 선택하세요",
                    question_type=QuestionType.MULTI_CHOICE,
                    options=[
                        "신용카드",
                        "계좌이체",
                        "카카오페이",
                        "네이버페이",
                        "페이팔",
                    ],
                    required=True,
                ),
                Question(
                    id="ecom_inventory",
                    question_text="재고 관리 기능이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                    help_text="상품 재고 추적 및 알림",
                ),
                Question(
                    id="ecom_shipping",
                    question_text="배송 추적 기능이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                ),
            ],
            "HEALTHCARE": [
                Question(
                    id="health_compliance",
                    question_text="HIPAA/개인정보보호법 준수가 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                    required=True,
                    help_text="환자 정보 처리 시 필수",
                ),
                Question(
                    id="health_data_encryption",
                    question_text="데이터 암호화 수준은?",
                    question_type=QuestionType.SINGLE_CHOICE,
                    options=[
                        "전송 중 암호화 (TLS)",
                        "저장 시 암호화 (AES-256)",
                        "전송 + 저장 모두 암호화 (권장)",
                    ],
                    default_value="전송 + 저장 모두 암호화 (권장)",
                ),
            ],
            "FINANCE": [
                Question(
                    id="fin_2fa",
                    question_text="2단계 인증(2FA)이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                    required=True,
                    help_text="금융 서비스는 2FA 필수 권장",
                ),
                Question(
                    id="fin_audit_trail",
                    question_text="감사 추적(Audit Trail)이 필요한가요?",
                    question_type=QuestionType.YES_NO,
                    default_value="yes",
                    help_text="모든 거래 내역 불변 로그 저장",
                ),
            ],
            "CHATBOT": [
                Question(
                    id="chat_context_memory",
                    question_text="대화 컨텍스트를 얼마나 유지하나요?",
                    question_type=QuestionType.SINGLE_CHOICE,
                    options=[
                        "단일 세션만 (세션 종료 시 삭제)",
                        "영구 저장 (사용자별)",
                        "제한적 (최근 N개 대화)",
                    ],
                    default_value="단일 세션만 (세션 종료 시 삭제)",
                ),
                Question(
                    id="chat_multilingual",
                    question_text="다국어 지원이 필요한가요?",
                    question_type=QuestionType.MULTI_CHOICE,
                    options=["한국어", "영어", "일본어", "중국어"],
                    help_text="여러 개 선택 가능",
                ),
            ],
        }

        return templates.get(domain, [])

    def _deduplicate_questions(self, questions: List[Question]) -> List[Question]:
        """
        중복 질문 제거

        Args:
            questions: 질문 목록

        Returns:
            List[Question]: 중복이 제거된 질문 목록
        """
        seen_ids = set()
        seen_texts = set()
        unique = []

        for q in questions:
            # ID 중복 체크
            if q.id in seen_ids:
                continue

            # 질문 텍스트 유사도 체크 (간단한 방식)
            # 정규화: 소문자 + 공백 제거
            normalized_text = q.question_text.lower().replace(" ", "")

            # 매우 유사한 질문은 제거
            is_similar = False
            for seen_text in seen_texts:
                # 80% 이상 일치하면 유사한 질문으로 판단
                similarity = self._text_similarity(normalized_text, seen_text)
                if similarity > 0.8:
                    is_similar = True
                    break

            if not is_similar:
                seen_ids.add(q.id)
                seen_texts.add(normalized_text)
                unique.append(q)

        return unique

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 유사도 계산 (간단한 Jaccard 유사도)

        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트

        Returns:
            float: 유사도 (0.0 ~ 1.0)
        """
        # 문자 단위 집합으로 Jaccard 유사도 계산
        set1 = set(text1)
        set2 = set(text2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _optimize_question_order(self, questions: List[Question]) -> List[Question]:
        """
        질문 순서 최적화
        - 필수 질문 우선
        - 조건부 질문은 조건 다음에 배치
        """
        required = [q for q in questions if q.required and not q.conditional_on]
        optional = [q for q in questions if not q.required and not q.conditional_on]
        conditional = [q for q in questions if q.conditional_on]

        # 조건부 질문은 조건 질문 바로 다음에 배치
        ordered = []

        # 필수 질문 먼저
        for q in required:
            ordered.append(q)
            # 이 질문에 의존하는 조건부 질문 추가
            dependent = [c for c in conditional if c.conditional_on == q.id]
            ordered.extend(dependent)

        # 옵션 질문
        for q in optional:
            if q not in ordered:
                ordered.append(q)
                # 이 질문에 의존하는 조건부 질문 추가
                dependent = [c for c in conditional if c.conditional_on == q.id]
                ordered.extend(dependent)

        # 아직 추가되지 않은 조건부 질문 (조건이 없는 경우)
        for q in conditional:
            if q not in ordered:
                ordered.append(q)

        return ordered

    def process_answers(
        self, questions: List[Question], answers: Dict[str, Any]
    ) -> QuestionnaireResult:
        """
        답변 처리

        Args:
            questions: 질문 목록
            answers: 사용자 답변

        Returns:
            QuestionnaireResult
        """
        # 조건부 질문 필터링
        applicable_questions = self._filter_conditional_questions(questions, answers)

        # 필수 질문 답변 확인
        remaining_ambiguities = []
        for q in applicable_questions:
            if q.required and q.id not in answers:
                remaining_ambiguities.append(f"{q.question_text} (필수)")

        # 신뢰도 점수 계산
        answered = len([q for q in applicable_questions if q.id in answers])
        total = len(applicable_questions)
        confidence_score = answered / total if total > 0 else 1.0

        return QuestionnaireResult(
            answers=answers,
            confidence_score=confidence_score,
            remaining_ambiguities=remaining_ambiguities,
        )

    def _filter_conditional_questions(
        self, questions: List[Question], answers: Dict[str, Any]
    ) -> List[Question]:
        """조건부 질문 필터링"""
        applicable = []

        for q in questions:
            if not q.conditional_on:
                # 무조건 질문
                applicable.append(q)
            else:
                # 조건 확인
                condition_met = answers.get(q.conditional_on) == q.conditional_value
                if condition_met:
                    applicable.append(q)

        return applicable


def generate_interactive_questions(
    gaps: List[RequirementGap], domain: str, llm_client=None
) -> List[Question]:
    """
    Helper function - 인터랙티브 질문 생성

    Args:
        gaps: 요구사항 갭
        domain: 도메인
        llm_client: LLM 클라이언트

    Returns:
        List[Question]
    """
    generator = InteractiveQuestionGenerator(llm_client=llm_client)
    return generator.generate_questions(gaps, domain)
