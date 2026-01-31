"""
BMAD Requirement Analyzer

자연어 요구사항을 분석하여 구조화된 형태로 변환합니다.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from enum import Enum

from app.utils.logger import get_logger, LoggerMixin
from app.models.domain_types import DomainClassification, DomainType, ExecutionPattern

if TYPE_CHECKING:
    from app.llm.chains import RequirementAnalysisChain, RequirementAnalysis, DomainClassificationChain

logger = get_logger("bmad.analyzer")


class RequirementType(str, Enum):
    """요구사항 유형"""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"


class ExtractedFeature(BaseModel):
    """추출된 기능"""
    id: str
    name: str
    description: str
    priority: int = Field(default=3, ge=1, le=5)
    type: RequirementType = RequirementType.FUNCTIONAL
    dependencies: List[str] = Field(default_factory=list)


class DomainContext(BaseModel):
    """도메인 컨텍스트"""
    domain: str
    subdomain: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    industry_terms: List[str] = Field(default_factory=list)
    related_domains: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """분석 결과"""
    raw_requirement: str
    domain_context: DomainContext
    domain_classification: Optional[DomainClassification] = Field(
        default=None,
        description="도메인 타입 분류 결과 (DomainType, ExecutionPattern 포함)"
    )
    features: List[ExtractedFeature]
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    suggested_workflow: str = "sequential"
    complexity_score: int = Field(default=5, ge=1, le=10)


class RequirementAnalyzer(LoggerMixin):
    """
    요구사항 분석기
    
    자연어 요구사항을 분석하여 기능, 도메인, 제약사항 등을 추출합니다.
    """
    
    def __init__(self):
        self._analysis_chain = None
        self._domain_classification_chain = None

    @property
    def analysis_chain(self):
        """LLM 체인 (지연 초기화)"""
        if self._analysis_chain is None:
            from app.llm.chains import RequirementAnalysisChain
            self._analysis_chain = RequirementAnalysisChain()
        return self._analysis_chain

    @property
    def domain_classification_chain(self):
        """도메인 분류 체인 (지연 초기화)"""
        if self._domain_classification_chain is None:
            from app.llm.chains import DomainClassificationChain
            self._domain_classification_chain = DomainClassificationChain()
        return self._domain_classification_chain
    
    def analyze(self, requirement: str) -> AnalysisResult:
        """
        요구사항을 분석합니다.

        Args:
            requirement: 자연어 요구사항

        Returns:
            AnalysisResult: 분석 결과
        """
        self.logger.info(f"요구사항 분석 시작: {len(requirement)} chars")

        # 1. 도메인 타입 분류 (우선 실행)
        domain_classification = None
        try:
            # 한글 포함 여부 확인
            use_korean = any('\uac00' <= c <= '\ud7a3' for c in requirement)
            domain_classification = self.domain_classification_chain.classify(
                requirement=requirement,
                use_korean=use_korean
            )
            self.logger.info(
                f"도메인 분류 완료: {domain_classification.domain_type} "
                f"(confidence: {domain_classification.confidence:.2%})"
            )
        except Exception as e:
            self.logger.warning(f"도메인 분류 실패: {e}. 기본값 사용.")
            # 실패 시 기본값 설정
            domain_classification = DomainClassification(
                domain_type=DomainType.CUSTOM,
                confidence=0.5,
                reasoning="도메인 분류 실패로 기본값 사용",
                core_entities=[],
                core_operations=[],
                execution_pattern=ExecutionPattern.CRUD_APPLICATION,
                keywords=[],
                alternate_types=[]
            )

        # 2. LLM 기반 요구사항 분석
        llm_analysis = self.analysis_chain.analyze(requirement)

        # 3. 도메인 컨텍스트 구성
        domain_context = self._extract_domain_context(llm_analysis)

        # 4. 기능 추출
        features = self._extract_features(llm_analysis)

        # 5. 결과 구성
        result = AnalysisResult(
            raw_requirement=requirement,
            domain_context=domain_context,
            domain_classification=domain_classification,
            features=features,
            constraints=llm_analysis.constraints,
            assumptions=[],
            success_criteria=llm_analysis.success_criteria,
            suggested_workflow=llm_analysis.workflow_type,
            complexity_score=self._calculate_complexity(llm_analysis),
        )

        self.logger.info(
            f"분석 완료: domain={domain_context.domain}, "
            f"domain_type={domain_classification.domain_type}, features={len(features)}"
        )
        return result
    
    def _extract_domain_context(self, analysis: "RequirementAnalysis") -> DomainContext:
        """도메인 컨텍스트 추출"""
        return DomainContext(
            domain=analysis.domain,
            subdomain=analysis.subdomain,
            keywords=self._extract_keywords(analysis),
            industry_terms=[],
            related_domains=[],
        )
    
    def _extract_keywords(self, analysis: "RequirementAnalysis") -> List[str]:
        """키워드 추출"""
        keywords = set()
        
        # 에이전트 역할에서 키워드 추출
        for agent in analysis.agents:
            keywords.add(agent.role.lower())
            keywords.update(skill.lower() for skill in agent.skills)
        
        # 태스크 이름에서 키워드 추출
        for task in analysis.tasks:
            keywords.add(task.name.lower())
        
        # 도구에서 키워드 추출
        keywords.update(tool.lower() for tool in analysis.suggested_tools)
        
        return list(keywords)
    
    def _extract_features(self, analysis: "RequirementAnalysis") -> List[ExtractedFeature]:
        """기능 추출"""
        features = []
        
        for i, task in enumerate(analysis.tasks, 1):
            feature = ExtractedFeature(
                id=f"feature_{i}",
                name=task.name,
                description=task.description,
                priority=5 - min(i - 1, 4),  # 앞에 있는 태스크일수록 높은 우선순위
                type=RequirementType.FUNCTIONAL,
                dependencies=[f"feature_{j+1}" for j in range(i-1)] if task.dependencies else [],
            )
            features.append(feature)
        
        return features
    
    def _calculate_complexity(self, analysis: "RequirementAnalysis") -> int:
        """복잡도 계산"""
        # 에이전트 수, 태스크 수, 의존성 수를 기반으로 복잡도 계산
        agent_count = len(analysis.agents)
        task_count = len(analysis.tasks)
        
        # 의존성 수 계산
        dep_count = sum(len(task.dependencies) for task in analysis.tasks)
        
        # 복잡도 점수 (1-10)
        score = min(10, max(1, (agent_count + task_count + dep_count) // 2))
        
        return score
    
    def validate_requirement(self, requirement: str) -> Dict[str, Any]:
        """
        요구사항의 유효성을 검증합니다.
        
        Args:
            requirement: 요구사항 텍스트
        
        Returns:
            Dict: 검증 결과
        """
        issues = []
        warnings = []
        
        # 최소 길이 검사
        if len(requirement.strip()) < 20:
            issues.append("요구사항이 너무 짧습니다. 최소 20자 이상 입력해주세요.")
        
        # 최대 길이 검사
        if len(requirement) > 10000:
            warnings.append("요구사항이 너무 깁니다. 핵심 내용만 포함해주세요.")
        
        # 동사 포함 여부 (간단한 휴리스틱)
        action_words = ["생성", "만들", "분석", "수집", "작성", "검색", "처리", "변환", 
                       "create", "make", "analyze", "collect", "write", "search", "process"]
        has_action = any(word in requirement.lower() for word in action_words)
        
        if not has_action:
            warnings.append("구체적인 동작(생성, 분석, 수집 등)을 포함하면 더 좋은 결과를 얻을 수 있습니다.")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": [
                "목적을 명확히 기술해주세요.",
                "필요한 기능을 구체적으로 나열해주세요.",
                "입력과 출력 형식을 명시해주세요.",
            ] if warnings else [],
        }
