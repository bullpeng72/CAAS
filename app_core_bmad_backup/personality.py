"""
BMAD Agent Personality Customization

에이전트 성격 커스터마이징 (BMAD 방법론 확장)
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from app.utils.logger import get_logger, LoggerMixin

logger = get_logger("bmad.personality")


class PersonalityTone(str, Enum):
    """성격 톤"""
    PROFESSIONAL = "professional"      # 전문적이고 격식있는
    FRIENDLY = "friendly"             # 친근하고 접근하기 쉬운
    TECHNICAL = "technical"           # 기술적이고 정확한
    CREATIVE = "creative"             # 창의적이고 혁신적인
    ANALYTICAL = "analytical"         # 분석적이고 논리적인
    ENTHUSIASTIC = "enthusiastic"     # 열정적이고 긍정적인


class VerbosityLevel(str, Enum):
    """상세도 레벨"""
    CONCISE = "concise"               # 간결하고 핵심만
    MODERATE = "moderate"             # 적당한 설명
    DETAILED = "detailed"             # 상세한 설명
    VERBOSE = "verbose"               # 매우 자세한 설명


class RiskTolerance(str, Enum):
    """리스크 허용도"""
    CONSERVATIVE = "conservative"     # 보수적, 안전 우선
    BALANCED = "balanced"             # 균형잡힌 접근
    AGGRESSIVE = "aggressive"         # 공격적, 혁신 우선


class AgentPersonality(BaseModel):
    """에이전트 성격"""
    tone: PersonalityTone = PersonalityTone.PROFESSIONAL
    verbosity: VerbosityLevel = VerbosityLevel.MODERATE
    creativity: float = Field(default=0.7, ge=0.0, le=1.0, description="LLM temperature (창의성)")
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED
    formality: float = Field(default=0.7, ge=0.0, le=1.0, description="격식 수준")
    empathy: float = Field(default=0.5, ge=0.0, le=1.0, description="공감 수준")

    class Config:
        use_enum_values = True


class PersonalityPreset(str, Enum):
    """성격 프리셋"""
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    CREATIVE_WRITER = "creative_writer"
    TECHNICAL_EXPERT = "technical_expert"
    CUSTOMER_SERVICE = "customer_service"
    STARTUP_FOUNDER = "startup_founder"
    FINANCE_ADVISOR = "finance_advisor"


class PersonalityManager(LoggerMixin):
    """
    성격 관리자

    에이전트 성격을 커스터마이즈하여 도메인별 최적화된 행동을 유도합니다.
    """

    def __init__(self):
        self.logger.info("PersonalityManager 초기화")

        # 프리셋 정의
        self.presets = {
            PersonalityPreset.RESEARCHER: AgentPersonality(
                tone=PersonalityTone.ANALYTICAL,
                verbosity=VerbosityLevel.DETAILED,
                creativity=0.5,  # 낮은 창의성 (정확성 우선)
                risk_tolerance=RiskTolerance.CONSERVATIVE,
                formality=0.8,
                empathy=0.3
            ),
            PersonalityPreset.ANALYST: AgentPersonality(
                tone=PersonalityTone.TECHNICAL,
                verbosity=VerbosityLevel.DETAILED,
                creativity=0.6,
                risk_tolerance=RiskTolerance.CONSERVATIVE,
                formality=0.9,
                empathy=0.2
            ),
            PersonalityPreset.CREATIVE_WRITER: AgentPersonality(
                tone=PersonalityTone.CREATIVE,
                verbosity=VerbosityLevel.VERBOSE,
                creativity=0.9,  # 높은 창의성
                risk_tolerance=RiskTolerance.AGGRESSIVE,
                formality=0.4,
                empathy=0.8
            ),
            PersonalityPreset.TECHNICAL_EXPERT: AgentPersonality(
                tone=PersonalityTone.TECHNICAL,
                verbosity=VerbosityLevel.CONCISE,
                creativity=0.4,
                risk_tolerance=RiskTolerance.CONSERVATIVE,
                formality=0.8,
                empathy=0.1
            ),
            PersonalityPreset.CUSTOMER_SERVICE: AgentPersonality(
                tone=PersonalityTone.FRIENDLY,
                verbosity=VerbosityLevel.MODERATE,
                creativity=0.6,
                risk_tolerance=RiskTolerance.BALANCED,
                formality=0.5,
                empathy=0.9  # 높은 공감
            ),
            PersonalityPreset.STARTUP_FOUNDER: AgentPersonality(
                tone=PersonalityTone.ENTHUSIASTIC,
                verbosity=VerbosityLevel.CONCISE,
                creativity=0.8,
                risk_tolerance=RiskTolerance.AGGRESSIVE,
                formality=0.3,
                empathy=0.7
            ),
            PersonalityPreset.FINANCE_ADVISOR: AgentPersonality(
                tone=PersonalityTone.PROFESSIONAL,
                verbosity=VerbosityLevel.DETAILED,
                creativity=0.4,
                risk_tolerance=RiskTolerance.CONSERVATIVE,
                formality=0.9,
                empathy=0.6
            ),
        }

    def get_preset(self, preset: PersonalityPreset) -> AgentPersonality:
        """
        프리셋 가져오기

        Args:
            preset: 프리셋 타입

        Returns:
            AgentPersonality: 성격
        """
        return self.presets.get(preset, AgentPersonality())

    def customize_backstory(
        self,
        base_backstory: str,
        personality: AgentPersonality
    ) -> str:
        """
        성격에 맞게 백스토리 커스터마이즈

        Args:
            base_backstory: 기본 백스토리
            personality: 성격

        Returns:
            str: 커스터마이즈된 백스토리
        """
        self.logger.debug(f"백스토리 커스터마이즈: tone={personality.tone}")

        # 톤에 따른 수정자
        tone_modifiers = {
            PersonalityTone.PROFESSIONAL: [
                "with a proven track record",
                "highly experienced",
                "dedicated professional"
            ],
            PersonalityTone.FRIENDLY: [
                "approachable and collaborative",
                "team-oriented",
                "always happy to help"
            ],
            PersonalityTone.TECHNICAL: [
                "technically proficient",
                "detail-oriented",
                "precision-focused"
            ],
            PersonalityTone.CREATIVE: [
                "innovative thinker",
                "creative problem solver",
                "outside-the-box approach"
            ],
            PersonalityTone.ANALYTICAL: [
                "data-driven decision maker",
                "methodical analyst",
                "evidence-based approach"
            ],
            PersonalityTone.ENTHUSIASTIC: [
                "passionate about",
                "energetic and motivated",
                "driven by excitement"
            ],
        }

        # 상세도에 따른 수정
        if personality.verbosity == VerbosityLevel.CONCISE:
            # 간결하게: 첫 2문장만
            sentences = base_backstory.split('.')
            customized = '. '.join(sentences[:2]) + '.'
        elif personality.verbosity == VerbosityLevel.VERBOSE:
            # 자세하게: 추가 문장
            modifier = tone_modifiers.get(personality.tone, ["experienced"])[0]
            customized = base_backstory + f" Known for being {modifier} in the field."
        else:
            customized = base_backstory

        return customized

    def get_llm_config(self, personality: AgentPersonality) -> Dict[str, Any]:
        """
        성격에 맞는 LLM 설정 생성

        Args:
            personality: 성격

        Returns:
            Dict: LLM 설정
        """
        config = {
            "temperature": personality.creativity,
            "top_p": 0.9 if personality.creativity > 0.7 else 0.8,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        # 리스크 허용도에 따른 조정
        if personality.risk_tolerance == RiskTolerance.CONSERVATIVE:
            config["temperature"] = min(config["temperature"], 0.6)
            config["top_p"] = 0.8
        elif personality.risk_tolerance == RiskTolerance.AGGRESSIVE:
            config["temperature"] = max(config["temperature"], 0.8)
            config["top_p"] = 0.95

        self.logger.debug(f"LLM 설정 생성: {config}")
        return config

    def infer_personality_from_domain(self, domain: str) -> AgentPersonality:
        """
        도메인에서 성격 추론

        Args:
            domain: 도메인 (finance, healthcare, etc.)

        Returns:
            AgentPersonality: 추론된 성격
        """
        domain_mapping = {
            "finance": PersonalityPreset.FINANCE_ADVISOR,
            "banking": PersonalityPreset.FINANCE_ADVISOR,
            "healthcare": PersonalityPreset.ANALYST,
            "medical": PersonalityPreset.ANALYST,
            "research": PersonalityPreset.RESEARCHER,
            "science": PersonalityPreset.RESEARCHER,
            "marketing": PersonalityPreset.CREATIVE_WRITER,
            "advertising": PersonalityPreset.CREATIVE_WRITER,
            "technology": PersonalityPreset.TECHNICAL_EXPERT,
            "engineering": PersonalityPreset.TECHNICAL_EXPERT,
            "customer_service": PersonalityPreset.CUSTOMER_SERVICE,
            "support": PersonalityPreset.CUSTOMER_SERVICE,
            "startup": PersonalityPreset.STARTUP_FOUNDER,
            "entrepreneurship": PersonalityPreset.STARTUP_FOUNDER,
        }

        preset = domain_mapping.get(domain.lower(), PersonalityPreset.ANALYST)
        self.logger.info(f"도메인 '{domain}'에서 성격 '{preset}' 추론")

        return self.get_preset(preset)

    def blend_personalities(
        self,
        personalities: list[AgentPersonality],
        weights: Optional[list[float]] = None
    ) -> AgentPersonality:
        """
        여러 성격을 혼합

        Args:
            personalities: 성격 목록
            weights: 가중치 (None이면 균등)

        Returns:
            AgentPersonality: 혼합된 성격
        """
        if not personalities:
            return AgentPersonality()

        if weights is None:
            weights = [1.0 / len(personalities)] * len(personalities)

        # 정규화
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        # 수치 필드 평균
        avg_creativity = sum(p.creativity * w for p, w in zip(personalities, weights))
        avg_formality = sum(p.formality * w for p, w in zip(personalities, weights))
        avg_empathy = sum(p.empathy * w for p, w in zip(personalities, weights))

        # 가장 많이 나타나는 tone/verbosity/risk
        from collections import Counter

        tone_counter = Counter(p.tone for p in personalities)
        verbosity_counter = Counter(p.verbosity for p in personalities)
        risk_counter = Counter(p.risk_tolerance for p in personalities)

        blended = AgentPersonality(
            tone=tone_counter.most_common(1)[0][0],
            verbosity=verbosity_counter.most_common(1)[0][0],
            creativity=avg_creativity,
            risk_tolerance=risk_counter.most_common(1)[0][0],
            formality=avg_formality,
            empathy=avg_empathy,
        )

        self.logger.info(f"{len(personalities)}개 성격 혼합 완료")
        return blended
