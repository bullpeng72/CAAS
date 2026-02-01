"""
CAAS LLM Chains

LangChain 기반의 복합 체인을 정의합니다.
요구사항 분석, 스펙 생성, 코드 생성 등의 워크플로우를 구현합니다.
"""

import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel
from caas_framework.utils.json_helper import JSONHelper

# 타입 힌트용 import
if TYPE_CHECKING:
    from caas_framework.llm.client import LLMConfig

# 선택적 의존성
LANGCHAIN_AVAILABLE = False
ChatPromptTemplate = None
JsonOutputParser = None
StrOutputParser = None
RunnablePassthrough = None
RunnableLambda = None

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    # SECURITY: 의존성 누락을 로깅하여 디버깅 용이하게 함
    import logging
    logging.getLogger("llm.chains").warning(
        f"LangChain Core를 사용할 수 없습니다: {e}. "
        "설치하려면: pip install langchain-core"
    )

from caas_framework.llm.prompts.analysis import (
    REQUIREMENT_ANALYSIS_SYSTEM,
    REQUIREMENT_ANALYSIS_USER,
    AGENT_DESIGN_SYSTEM,
    AGENT_DESIGN_USER,
    TASK_DESIGN_SYSTEM,
    TASK_DESIGN_USER,
    ONTOLOGY_CONTEXT_TEMPLATE,
    PATTERN_CONTEXT_TEMPLATE,
)
from caas_framework.llm.prompts.domain_classification import (
    DOMAIN_CLASSIFICATION_SYSTEM,
    DOMAIN_CLASSIFICATION_USER,
    DOMAIN_CLASSIFICATION_USER_KO,
)
from caas_framework.llm.prompts.spec_generation import (
    SPEC_GENERATION_SYSTEM,
    SPEC_GENERATION_USER,
    SPEC_VALIDATION_SYSTEM,
    SPEC_VALIDATION_USER,
)
from caas_framework.llm.prompts.concretization import (
    CONCRETIZATION_SYSTEM,
    CONCRETIZATION_USER_TEMPLATE,
)
import logging
from caas_framework.models import (
    RequirementAnalysis,
    AgentSpecModel as AgentSpec,
    TaskSpecModel as TaskSpec,
    ProjectTemplate,
    ConcretizedRequirement,
)
from caas_framework.models import DomainClassification, DomainType, ExecutionPattern
from caas_framework.llm.chain_factory import (
    BaseChainFactory,
    SimpleChainFactory,
    check_langchain,
)

logger = logging.getLogger("caas_framework.llm.chains")


# =============================================================================
# Output Models
# NOTE: 공통 스키마는 app.models.schemas에서 import됨
# =============================================================================


class ValidationResult(BaseModel):
    """검증 결과 모델"""
    valid: bool
    errors: List[Dict[str, str]] = []
    warnings: List[str] = []
    suggestions: List[str] = []


# =============================================================================
# Chain Implementations
# =============================================================================

class RequirementAnalysisChain(BaseChainFactory):
    """요구사항 분석 체인 (온톨로지 통합)"""

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return REQUIREMENT_ANALYSIS_SYSTEM

    def get_user_prompt(self) -> str:
        """사용자 프롬프트 반환"""
        return REQUIREMENT_ANALYSIS_USER

    def get_output_model(self):
        """출력 모델 반환"""
        return RequirementAnalysis

    def _build_ontology_context(self) -> str:
        """
        온톨로지 지식을 구조화된 텍스트로 생성합니다.

        Returns:
            str: 온톨로지 컨텍스트 문자열
        """
        from caas_app.knowledge.ontology import (
            AgentRole,
            TaskType,
            ROLE_TASK_MAPPINGS,
            TASK_TOOL_MAPPINGS
        )

        # 1. Agent Roles 목록
        agent_roles_list = "\n".join([
            f"  - {role.value}" for role in AgentRole
        ])

        # 2. Task Types 목록
        task_types_list = "\n".join([
            f"  - {task.value}" for task in TaskType
        ])

        # 3. Role → Task Mappings
        role_task_mappings = ""
        for role, tasks in ROLE_TASK_MAPPINGS.items():
            task_names = ", ".join([t.value for t in tasks[:5]])  # 최대 5개만 표시
            if len(tasks) > 5:
                task_names += f" (+{len(tasks)-5} more)"
            role_task_mappings += f"  • {role.value}: [{task_names}]\n"

        # 4. Task → Tool Capability Mappings
        task_capability_mappings = ""
        for task_type, capabilities in TASK_TOOL_MAPPINGS.items():
            cap_names = ", ".join([c.value for c in capabilities])
            task_capability_mappings += f"  • {task_type.value}: requires [{cap_names}]\n"

        # 템플릿에 정보 주입
        ontology_context = ONTOLOGY_CONTEXT_TEMPLATE.format(
            agent_roles_list=agent_roles_list,
            task_types_list=task_types_list,
            role_task_mappings=role_task_mappings,
            task_capability_mappings=task_capability_mappings
        )

        return ontology_context

    def _extract_keywords(self, requirement: str) -> List[str]:
        """
        요구사항에서 키워드를 추출합니다 (간단한 구현).

        Args:
            requirement: 요구사항 텍스트

        Returns:
            List[str]: 추출된 키워드 목록
        """
        # 간단한 키워드 추출 (공백 기반)
        # 향후 NLP 라이브러리로 개선 가능
        import re

        # 특수문자 제거, 소문자 변환
        cleaned = re.sub(r'[^\w\s가-힣]', ' ', requirement.lower())

        # 단어 추출 (2글자 이상)
        words = [w.strip() for w in cleaned.split() if len(w.strip()) >= 2]

        # 불용어 제거 (간단한 버전)
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     '을', '를', '이', '가', '은', '는', '의', '와', '과', '에', '에서', '로', '으로'}
        keywords = [w for w in words if w not in stopwords]

        # 중복 제거 및 빈도순 정렬 (간단히 unique만)
        unique_keywords = list(dict.fromkeys(keywords))

        return unique_keywords[:20]  # 최대 20개

    def _match_pattern(self, requirement: str, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """
        요구사항과 키워드를 기반으로 최적의 패턴을 찾습니다.

        Args:
            requirement: 요구사항 텍스트
            keywords: 추출된 키워드

        Returns:
            Optional[Dict]: 매칭된 패턴 정보 (없으면 None)
        """
        from caas_app.knowledge.graph.patterns import PatternMatcher

        try:
            pattern_matcher = PatternMatcher()

            # 도메인 추론 (간단한 키워드 기반)
            domain = self._infer_domain_from_keywords(keywords)

            # 패턴 검색
            matched_patterns = pattern_matcher.match_pattern(
                requirement_features=keywords,
                domain=domain
            )

            if matched_patterns and len(matched_patterns) > 0:
                # 최고 유사도 패턴 선택
                best_match = matched_patterns[0]

                # 패턴 ID로 실제 패턴 객체 찾기
                pattern = next(
                    (p for p in pattern_matcher.builtin_patterns if p.id == best_match.pattern_id),
                    None
                )

                if pattern:
                    logger.info(f"✅ 패턴 매칭 성공: {pattern.name} (유사도: {best_match.similarity_score})")
                    return {
                        "pattern": pattern,
                        "match": best_match
                    }

            logger.info("패턴 매칭 실패: 유사한 패턴 없음")
            return None

        except Exception as e:
            logger.warning(f"패턴 매칭 중 오류: {e}")
            return None

    def _infer_domain_from_keywords(self, keywords: List[str]) -> str:
        """
        키워드에서 도메인을 추론합니다.

        Args:
            keywords: 키워드 목록

        Returns:
            str: 추론된 도메인
        """
        domain_keywords = {
            "finance": ["금융", "투자", "주식", "finance", "investment", "stock", "trading", "portfolio", "risk"],
            "healthcare": ["의료", "건강", "환자", "health", "medical", "patient", "clinical", "diagnosis"],
            "education": ["교육", "학생", "커리큘럼", "education", "student", "curriculum", "learning", "course"],
            "technology": ["개발", "코드", "소프트웨어", "development", "code", "software", "programming", "api"],
            "marketing": ["마케팅", "캠페인", "광고", "marketing", "campaign", "advertisement", "content", "social"],
            "research": ["연구", "분석", "조사", "research", "analysis", "investigation", "study"],
            "customer_service": ["고객", "지원", "서비스", "customer", "support", "service", "feedback"],
            "ecommerce": ["쇼핑", "상품", "구매", "shopping", "product", "purchase", "recommendation"]
        }

        scores = {domain: 0 for domain in domain_keywords}

        for keyword in keywords:
            for domain, domain_kw_list in domain_keywords.items():
                if keyword in domain_kw_list:
                    scores[domain] += 1

        # 최고 점수 도메인 반환
        best_domain = max(scores, key=scores.get)

        return best_domain if scores[best_domain] > 0 else "general"

    def _build_pattern_context(self, pattern_info: Dict[str, Any]) -> str:
        """
        매칭된 패턴 정보를 컨텍스트 문자열로 변환합니다.

        Args:
            pattern_info: 패턴 및 매칭 정보

        Returns:
            str: 패턴 컨텍스트 문자열
        """
        from caas_app.knowledge.graph.patterns import AgentPattern, PatternMatch

        pattern: AgentPattern = pattern_info["pattern"]
        match: PatternMatch = pattern_info["match"]

        # 에이전트 역할 포매팅
        agent_roles = "\n".join([f"  - {role}" for role in pattern.agent_roles])

        # 태스크 유형 포매팅
        task_types = "\n".join([f"  - {task}" for task in pattern.task_types])

        # 추천 도구 포매팅
        recommended_tools = "\n".join([f"  - {tool}" for tool in pattern.recommended_tools])

        # 적응 제안 포매팅
        adaptations = "\n".join([f"  - {adapt}" for adapt in match.suggested_adaptations])

        # 템플릿 채우기
        pattern_context = PATTERN_CONTEXT_TEMPLATE.format(
            pattern_name=pattern.name,
            similarity_score=f"{match.similarity_score:.2f}",
            domain=pattern.domain,
            use_case=pattern.use_case,
            agent_roles=agent_roles,
            task_types=task_types,
            recommended_tools=recommended_tools,
            workflow_type=pattern.workflow_type,
            adaptations=adaptations if adaptations else "  - No specific adaptations needed"
        )

        return pattern_context

    def _format_golden_data_for_analysis(self, golden_data: "ConcretizedRequirement") -> str:
        """
        Golden Data를 요구사항 분석에 활용할 수 있는 형태로 포맷팅합니다.

        Args:
            golden_data: 구체화된 요구사항

        Returns:
            str: 포맷된 Golden Data 컨텍스트
        """
        context = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        context += "🎯 **GOLDEN DATA CONTEXT** (Concretized Requirement)\n"
        context += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        context += "The following is a detailed, concrete specification of the requirement.\n"
        context += "Use this as the primary reference for your analysis.\n\n"

        # System Scope
        context += f"**System Scope:**\n"
        context += f"- Project: {golden_data.system_scope.project_name}\n"
        context += f"- Purpose: {golden_data.system_scope.purpose}\n"
        context += f"- Domain: {golden_data.domain}\n"
        context += f"- System Type: {golden_data.system_scope.system_type}\n"
        context += f"- Target Users: {', '.join(golden_data.system_scope.target_users)}\n\n"

        # Features
        context += f"**Features ({len(golden_data.features)}):**\n"
        for i, feature in enumerate(golden_data.features, 1):
            context += f"{i}. {feature.name} (Priority: {feature.priority})\n"
            context += f"   - {feature.description}\n"
            if feature.acceptance_criteria:
                context += f"   - Acceptance Criteria: {len(feature.acceptance_criteria)} criteria defined\n"
            if feature.related_features:
                context += f"   - Related features: {', '.join(feature.related_features)}\n"
        context += "\n"

        # Data Models
        if golden_data.data_models:
            context += f"**Data Models ({len(golden_data.data_models)}):**\n"
            for model in golden_data.data_models:
                context += f"- {model.entity_name}: {len(model.attributes)} attributes\n"
            context += "\n"

        # UI Components
        if golden_data.ui_components:
            context += f"**UI Components ({len(golden_data.ui_components)}):**\n"
            for ui in golden_data.ui_components:
                context += f"- {ui.id}: {ui.component_type} on {ui.page_name}\n"
            context += "\n"

        # NFRs
        if golden_data.non_functional_requirements:
            nfr = golden_data.non_functional_requirements
            context += "**Non-Functional Requirements:**\n"
            if nfr.performance:
                context += f"- Performance: {nfr.performance}\n"
            if nfr.security:
                context += f"- Security: {nfr.security}\n"
            if nfr.scalability:
                context += f"- Scalability: {nfr.scalability}\n"
            context += "\n"

        # Success Criteria
        if golden_data.success_criteria:
            context += f"**Success Criteria:**\n"
            for criterion in golden_data.success_criteria:
                context += f"- {criterion}\n"
            context += "\n"

        context += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        context += "👉 **INSTRUCTION:** Analyze the requirement based on the Golden Data above.\n"
        context += "   Extract agents, tasks, and tools that align with the specified features and requirements.\n"
        context += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        return context

    def _validate_with_ontology(self, result: RequirementAnalysis) -> RequirementAnalysis:
        """
        LLM 분석 결과를 온톨로지로 검증하고 보완합니다.

        Args:
            result: LLM 분석 결과

        Returns:
            RequirementAnalysis: 검증 및 보완된 결과
        """
        from caas_app.knowledge.ontology import OntologyManager

        ontology = OntologyManager()

        logger.info("🔍 온톨로지 기반 검증 시작")

        # 1. 에이전트 역할 검증 및 보완
        validated_agents = []
        for agent in result.agents:
            # 역할 정규화
            inferred_role = ontology.infer_role_from_description(
                f"{agent.role} {agent.goal}"
            )

            # 원래 역할이 표준 역할과 다르면 경고
            if agent.role.lower() != inferred_role.value:
                logger.info(f"💡 역할 정규화: '{agent.role}' → '{inferred_role.value}'")

            # 에이전트 관련 태스크 찾기
            agent_tasks = [t for t in result.tasks if t.assigned_agent.lower() in agent.role.lower()]
            task_types = [ontology.infer_task_type_from_description(t.description) for t in agent_tasks]

            # 추천 도구 계산
            recommended_tools = ontology.recommend_agent_tools(
                role=inferred_role,
                assigned_tasks=task_types
            )

            # 기존 도구와 추천 도구 병합
            current_tools = set(agent.skills)  # skills를 도구로 사용
            all_tools = list(current_tools | set(recommended_tools))

            # 누락된 필수 도구 추가
            missing_tools = set(recommended_tools) - current_tools
            if missing_tools:
                logger.info(f"✅ '{agent.role}'에 도구 추가: {', '.join(list(missing_tools)[:3])}")

            # 에이전트 업데이트
            validated_agent = agent.model_copy(update={
                "skills": all_tools[:10]  # 최대 10개로 제한
            })
            validated_agents.append(validated_agent)

        # 2. 태스크 검증
        validated_tasks = []
        for task in result.tasks:
            task_type = ontology.infer_task_type_from_description(task.description)

            # 할당된 에이전트 역할 확인
            assigned_agent = next((a for a in validated_agents if a.role.lower() in task.assigned_agent.lower()), None)

            if assigned_agent:
                inferred_role = ontology.infer_role_from_description(f"{assigned_agent.role} {assigned_agent.goal}")

                # 역할-태스크 적합성 검증
                is_valid = ontology.validate_assignment(inferred_role, task_type)

                if not is_valid:
                    # 더 적합한 역할 찾기
                    suitable_roles = ontology.get_suitable_roles(task_type)
                    if suitable_roles:
                        logger.warning(f"⚠️ 태스크 '{task.name}' ({task_type.value})는 '{inferred_role.value}' 보다 '{suitable_roles[0].value}'가 더 적합")

            validated_tasks.append(task)

        # 3. 도구 검증 (suggested_tools)
        all_task_types = [ontology.infer_task_type_from_description(t.description) for t in validated_tasks]
        required_tools = set()

        for task_type in all_task_types:
            suitable_tools = ontology.get_suitable_tools(task_type)
            required_tools.update(suitable_tools)

        # LLM이 선택한 도구와 온톨로지 추천 도구 병합
        suggested_tools = list(set(result.suggested_tools) | required_tools)

        logger.info(f"✅ 온톨로지 검증 완료: {len(validated_agents)}개 에이전트, {len(validated_tasks)}개 태스크")

        # 결과 업데이트
        return result.model_copy(update={
            "agents": validated_agents,
            "tasks": validated_tasks,
            "suggested_tools": suggested_tools[:15]  # 최대 15개로 제한
        })

    def analyze(
        self,
        requirement: str,
        workflow_type: Optional[str] = None,
        available_tools: Optional[Dict[str, str]] = None,
        tools_info: Optional[str] = None,
        recommended_tools: Optional[List[str]] = None,
        enable_ontology: bool = True,
        enable_pattern_matching: bool = True,
        enable_validation: bool = True,
        golden_data: Optional["ConcretizedRequirement"] = None
    ) -> RequirementAnalysis:
        """
        자연어 요구사항을 분석합니다 (Hybrid: Golden Data 기반 또는 원본 기반).

        Args:
            requirement: 자연어 요구사항 텍스트
            workflow_type: 워크플로우 유형 (선택사항, 지정하지 않으면 LLM이 결정)
            available_tools: 사용 가능한 도구 목록 {name: description}
            tools_info: 풍부한 도구 정보 (카테고리, 키워드, 사용 사례 포함)
            recommended_tools: 키워드 기반 추천 도구 목록
            enable_ontology: 온톨로지 컨텍스트 주입 여부 (기본: True)
            enable_pattern_matching: 패턴 매칭 활성화 여부 (기본: True)
            enable_validation: 온톨로지 기반 검증 활성화 여부 (기본: True)
            golden_data: 구체화된 요구사항 (선택적) - 있으면 Golden Data 기반 분석

        Returns:
            RequirementAnalysis: 구조화된 분석 결과
        """
        # Golden Data 기반 분석 여부 결정
        use_golden_data = golden_data is not None

        if use_golden_data:
            logger.info("🎯 Golden Data 기반 분석 시작 (Hybrid Mode)")
        else:
            logger.info("📝 원본 요구사항 기반 분석 시작 (Classic Mode)")
        try:
            # ═══════════════════════════════════════════════════════════
            # STEP 1: 패턴 매칭 (Pattern-First Approach)
            # ═══════════════════════════════════════════════════════════
            pattern_context = ""
            if enable_pattern_matching:
                # 1-1. 키워드 추출
                keywords = self._extract_keywords(requirement)
                logger.info(f"📝 키워드 추출: {len(keywords)}개")

                # 1-2. 패턴 매칭
                pattern_info = self._match_pattern(requirement, keywords)

                # 1-3. 패턴 컨텍스트 생성
                if pattern_info:
                    pattern_context = self._build_pattern_context(pattern_info)
                    logger.info("✅ 패턴 컨텍스트 생성 완료")

            # ═══════════════════════════════════════════════════════════
            # STEP 2: 온톨로지 컨텍스트 생성
            # ═══════════════════════════════════════════════════════════
            ontology_context = ""
            if enable_ontology:
                ontology_context = self._build_ontology_context()
                logger.info("✅ 온톨로지 컨텍스트 생성 완료")

            # ═══════════════════════════════════════════════════════════
            # STEP 3: 도구 정보 구성
            # ═══════════════════════════════════════════════════════════
            tools_section = ""
            if tools_info:
                tools_section = f"\n\n**Available Tools (categorized with use cases):**\n{tools_info}\n"
                logger.info("카테고리별 도구 정보 포함")
            elif available_tools:
                tools_section = "\n\n**Available Tools:**\n"
                for tool_name, tool_desc in available_tools.items():
                    tools_section += f"- {tool_name}: {tool_desc}\n"
                logger.info(f"사용 가능한 도구: {len(available_tools)}개")

            # 추천 도구 추가
            if recommended_tools:
                tools_section += f"\n**🎯 Recommended Tools (based on requirement keywords):**\n"
                tools_section += f"{', '.join(recommended_tools)}\n"
                tools_section += "These tools are highly relevant to the requirement. Prioritize them when selecting tools.\n"
                logger.info(f"추천 도구: {len(recommended_tools)}개")

            # ═══════════════════════════════════════════════════════════
            # STEP 3.5: Golden Data 컨텍스트 생성 (있는 경우)
            # ═══════════════════════════════════════════════════════════
            golden_data_context = ""
            if use_golden_data:
                golden_data_context = self._format_golden_data_for_analysis(golden_data)
                logger.info("✅ Golden Data 컨텍스트 생성 완료")
                logger.info(f"   - Features: {len(golden_data.features)}")
                logger.info(f"   - Data Models: {len(golden_data.data_models)}")
                logger.info(f"   - UI Components: {len(golden_data.ui_components)}")

            # ═══════════════════════════════════════════════════════════
            # STEP 4: 컨텍스트 결합 (순서: Golden Data → 패턴 → 온톨로지 → 도구)
            # ═══════════════════════════════════════════════════════════
            enhanced_requirement = requirement

            # Golden Data가 최우선 (가장 먼저 추가)
            if golden_data_context:
                enhanced_requirement += golden_data_context

            if pattern_context:
                enhanced_requirement += "\n\n" + pattern_context

            if ontology_context:
                enhanced_requirement += "\n\n" + ontology_context

            if tools_section:
                enhanced_requirement += tools_section

            # ═══════════════════════════════════════════════════════════
            # STEP 5: LLM 체인 실행
            # ═══════════════════════════════════════════════════════════
            result = self.invoke({"requirement": enhanced_requirement})
            logger.info(f"✅ LLM 분석 완료: {result.get('domain', 'unknown')} 도메인")

            # 사용자가 workflow_type을 지정한 경우 덮어쓰기
            if workflow_type is not None:
                result['workflow_type'] = workflow_type
                logger.info(f"워크플로우 유형을 사용자 선택값으로 설정: {workflow_type}")

            # RequirementAnalysis 객체 생성
            analysis_result = RequirementAnalysis(**result)

            # ═══════════════════════════════════════════════════════════
            # STEP 5.5: Domain Type Classification (NEW!)
            # ═══════════════════════════════════════════════════════════
            try:
                domain_classifier = DomainClassificationChain()
                # 한글 포함 여부 확인 (간단히)
                use_korean = any('\uac00' <= c <= '\ud7a3' for c in requirement)

                domain_classification = domain_classifier.classify(
                    requirement=requirement,
                    use_korean=use_korean
                )

                analysis_result.domain_classification = domain_classification.model_dump()
                logger.info(f"🎯 Domain Type: {domain_classification.domain_type} "
                           f"(confidence: {domain_classification.confidence:.2f})")
                logger.info(f"   Core entities: {', '.join(domain_classification.core_entities)}")
                logger.info(f"   Execution pattern: {domain_classification.execution_pattern}")
            except Exception as e:
                logger.warning(f"⚠️ Domain classification failed: {e}")
                # 실패 시 분석 중단하지 않고 계속 진행

            # ═══════════════════════════════════════════════════════════
            # STEP 6: 온톨로지 기반 검증 및 보완
            # ═══════════════════════════════════════════════════════════
            if enable_validation:
                analysis_result = self._validate_with_ontology(analysis_result)

            logger.info("🎉 Phase 2 분석 완료 (패턴 + 온톨로지 + Domain Classification + 검증)")
            return analysis_result

        except Exception as e:
            logger.error(f"❌ 요구사항 분석 실패: {e}")
            raise


class AgentDesignChain(BaseChainFactory):
    """에이전트 설계 체인"""

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return AGENT_DESIGN_SYSTEM

    def get_user_prompt(self) -> str:
        """사용자 프롬프트 반환"""
        return AGENT_DESIGN_USER

    def get_output_model(self):
        """출력 모델 반환"""
        return AgentSpec
    
    def design(
        self,
        domain: str,
        role: str,
        goal: str,
        skills: List[str],
        tasks: List[str],
        available_tools: List[Dict[str, str]],
        architecture_context: Optional[str] = None,
        quality_metrics: Optional[Dict[str, Any]] = None,
    ) -> AgentSpec:
        """
        에이전트를 상세 설계합니다 (개선 버전).

        Args:
            domain: 도메인
            role: 역할
            goal: 목표
            skills: 필요 스킬
            tasks: 관련 태스크
            available_tools: 사용 가능한 도구 목록
            architecture_context: 아키텍처 설계 컨텍스트 (선택)
            quality_metrics: 품질 메트릭 (선택)

        Returns:
            AgentSpec: 에이전트 스펙
        """
        logger.info(f"에이전트 설계: {role}")
        tools_str = "\n".join([
            f"- {t['id']}: {t['description']}" for t in available_tools
        ])

        # 기본 inputs
        inputs = {
            "domain": domain,
            "role": role,
            "goal": goal,
            "skills": ", ".join(skills),
            "tasks": ", ".join(tasks),
            "available_tools": tools_str,
        }

        # Architecture context 추가 (있는 경우)
        if architecture_context:
            inputs["architecture_context"] = architecture_context
            logger.info(f"  ✓ 아키텍처 컨텍스트 포함")

        # Quality metrics 추가 (있는 경우)
        if quality_metrics:
            metrics_summary = f"Completeness: {quality_metrics.get('completeness_score', 0.7):.2f}, "
            metrics_summary += f"Clarity: {quality_metrics.get('clarity_score', 0.7):.2f}, "
            metrics_summary += f"Complexity: {quality_metrics.get('complexity_score', 5)}"
            inputs["quality_context"] = metrics_summary
            logger.info(f"  ✓ 품질 메트릭 컨텍스트 포함")

        result = self.invoke(inputs)

        return AgentSpec(**result)


class TaskDesignChain(BaseChainFactory):
    """태스크 설계 체인"""

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return TASK_DESIGN_SYSTEM

    def get_user_prompt(self) -> str:
        """사용자 프롬프트 반환"""
        return TASK_DESIGN_USER

    def get_output_model(self):
        """출력 모델 반환"""
        return TaskSpec
    
    def design(
        self,
        task_name: str,
        description: str,
        agent_id: str,
        dependencies: List[str],
        output_type: str,
        system_context: str,
        data_flow_context: Optional[str] = None,
        architecture_context: Optional[str] = None,
    ) -> TaskSpec:
        """
        태스크를 상세 설계합니다 (개선 버전).

        Args:
            task_name: 태스크 이름
            description: 설명
            agent_id: 담당 에이전트 ID
            dependencies: 의존 태스크
            output_type: 출력 유형
            system_context: 시스템 컨텍스트
            data_flow_context: 데이터 흐름 컨텍스트 (선택)
            architecture_context: 아키텍처 설계 컨텍스트 (선택)

        Returns:
            TaskSpec: 태스크 스펙
        """
        logger.info(f"태스크 설계: {task_name}")

        # 기본 inputs
        inputs = {
            "task_name": task_name,
            "description": description,
            "agent_id": agent_id,
            "dependencies": ", ".join(dependencies) if dependencies else "None",
            "output_type": output_type,
            "system_context": system_context,
        }

        # Data flow context 추가 (있는 경우)
        if data_flow_context:
            inputs["data_flow_context"] = data_flow_context
            logger.info(f"  ✓ 데이터 흐름 컨텍스트 포함")

        # Architecture context 추가 (있는 경우)
        if architecture_context:
            inputs["architecture_context"] = architecture_context
            logger.info(f"  ✓ 아키텍처 컨텍스트 포함")

        result = self.invoke(inputs)

        return TaskSpec(**result)


class SpecGenerationChain:
    """스펙 생성 체인 (문자열 출력)"""

    def __init__(self, llm_config: Optional["LLMConfig"] = None):
        # SimpleChainFactory를 사용하여 문자열 출력 체인 생성
        self.chain = SimpleChainFactory.create_string_chain(
            SPEC_GENERATION_SYSTEM,
            SPEC_GENERATION_USER,
            llm_config
        )
    
    def generate(
        self,
        domain: str,
        summary: str,
        agents: List[Dict],
        tasks: List[Dict],
        workflow_type: str,
        tools: List[str],
    ) -> str:
        """
        CrewAI YAML 스펙을 생성합니다.
        
        Args:
            domain: 도메인
            summary: 시스템 요약
            agents: 에이전트 목록
            tasks: 태스크 목록
            workflow_type: 워크플로우 유형
            tools: 도구 목록
        
        Returns:
            str: YAML 스펙 문자열
        """
        logger.info("스펙 생성 시작")
        
        result = self.chain.invoke({
            "domain": domain,
            "summary": summary,
            "agents_json": json.dumps(agents, indent=2, ensure_ascii=False),
            "tasks_json": json.dumps(tasks, indent=2, ensure_ascii=False),
            "workflow_type": workflow_type,
            "tools": ", ".join(tools),
        })
        
        # YAML 코드 블록 추출
        if "```yaml" in result:
            result = result.split("```yaml")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        result = result.strip()

        # YAML 구문 검증 및 ID sanitization
        try:
            import yaml

            # YAML 파싱 검증
            data = yaml.safe_load(result)

            if not data or not isinstance(data, dict):
                logger.error("LLM이 빈 YAML 또는 잘못된 형식 생성")
                raise ValueError("생성된 YAML이 비어있거나 유효하지 않습니다")

            # ID sanitization (agent 및 task ID를 snake_case로 자동 변환)
            # agents ID sanitization
            if "agents" in data and isinstance(data["agents"], list):
                for agent in data["agents"]:
                    if isinstance(agent, dict) and "id" in agent:
                        original_id = agent["id"]
                        sanitized_id = JSONHelper.sanitize_id(original_id)
                        if original_id != sanitized_id:
                            logger.warning(f"Agent ID 자동 수정: '{original_id}' → '{sanitized_id}'")
                            agent["id"] = sanitized_id

            # tasks ID 및 agent 참조 sanitization
            if "tasks" in data and isinstance(data["tasks"], list):
                for task in data["tasks"]:
                    if isinstance(task, dict):
                        # task ID sanitization
                        if "id" in task:
                            original_id = task["id"]
                            sanitized_id = JSONHelper.sanitize_id(original_id)
                            if original_id != sanitized_id:
                                logger.warning(f"Task ID 자동 수정: '{original_id}' → '{sanitized_id}'")
                                task["id"] = sanitized_id

                        # agent 참조 sanitization
                        if "agent" in task:
                            original_agent = task["agent"]
                            sanitized_agent = JSONHelper.sanitize_id(original_agent)
                            if original_agent != sanitized_agent:
                                logger.warning(f"Task agent 참조 자동 수정: '{original_agent}' → '{sanitized_agent}'")
                                task["agent"] = sanitized_agent

                        # context 참조 sanitization
                        if "context" in task and isinstance(task["context"], list):
                            task["context"] = [JSONHelper.sanitize_id(ctx) for ctx in task["context"]]

            # 수정된 데이터를 다시 YAML로 변환
            result = yaml.dump(
                data,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )

            logger.info("✅ YAML 검증 및 ID sanitization 완료")

        except yaml.YAMLError as e:
            logger.error(f"❌ LLM이 잘못된 YAML 생성: {e}")
            logger.error(f"생성된 내용:\n{result[:500]}...")
            raise ValueError(f"생성된 YAML 구문 오류: {e}")
        except Exception as e:
            logger.error(f"⚠️ YAML 검증 중 오류 (계속 진행): {e}")
            # 검증 실패 시에도 원본 반환 (하위 단계에서 재검증)

        return result


class SpecValidationChain:
    """스펙 검증 체인"""

    def __init__(self, llm_config: Optional["LLMConfig"] = None):
        check_langchain()
        from caas_framework.llm.client import get_langchain_llm
        self.llm = get_langchain_llm(**(llm_config.model_dump() if llm_config else {}))
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SPEC_VALIDATION_SYSTEM),
            ("human", SPEC_VALIDATION_USER),
        ])
        self.parser = JsonOutputParser(pydantic_object=ValidationResult)
        self.chain = self.prompt | self.llm | self.parser
    
    def validate(self, spec_yaml: str) -> ValidationResult:
        """
        CrewAI 스펙을 검증합니다.
        
        Args:
            spec_yaml: YAML 스펙 문자열
        
        Returns:
            ValidationResult: 검증 결과
        """
        logger.info("스펙 검증 시작")
        
        result = self.chain.invoke({"spec_yaml": spec_yaml})
        return ValidationResult(**result)


# =============================================================================
# Master Chain (Full Pipeline)
# =============================================================================

class AgentGenerationPipeline:
    """에이전트 생성 파이프라인 - 전체 워크플로우 통합"""

    def __init__(self, llm_config: Optional["LLMConfig"] = None):
        check_langchain()
        self.analysis_chain = RequirementAnalysisChain(llm_config)
        self.agent_design_chain = AgentDesignChain(llm_config)
        self.task_design_chain = TaskDesignChain(llm_config)
        self.spec_generation_chain = SpecGenerationChain(llm_config)
        self.validation_chain = SpecValidationChain(llm_config)

        # 사용 가능한 도구 목록 (Tool Manager에서 동적으로 로드)
        from caas_framework.models.tool_registry import get_enabled_tools_dict
        enabled_tools = get_enabled_tools_dict()
        self.available_tools = [
            {"id": tool_id, "description": tool_desc}
            for tool_id, tool_desc in enabled_tools.items()
        ]
    
    def run(self, requirement: str) -> Dict[str, Any]:
        """
        전체 파이프라인을 실행합니다.
        
        Args:
            requirement: 자연어 요구사항
        
        Returns:
            Dict: 생성 결과 (analysis, agents, tasks, spec, validation)
        """
        logger.info("=== 에이전트 생성 파이프라인 시작 ===")
        
        # 1. 요구사항 분석
        analysis = self.analysis_chain.analyze(requirement)
        logger.info(f"분석 완료: {len(analysis.agents)}개 에이전트, {len(analysis.tasks)}개 태스크")
        
        # 2. 에이전트 상세 설계
        designed_agents = []
        for agent_req in analysis.agents:
            related_tasks = [
                t.name for t in analysis.tasks 
                if t.assigned_agent == agent_req.role
            ]
            agent_spec = self.agent_design_chain.design(
                domain=analysis.domain,
                role=agent_req.role,
                goal=agent_req.goal,
                skills=agent_req.skills,
                tasks=related_tasks,
                available_tools=self.available_tools,
            )
            designed_agents.append(agent_spec)
        
        # 3. 태스크 상세 설계
        designed_tasks = []
        system_context = f"Domain: {analysis.domain}\nSummary: {analysis.summary}"
        
        for task_req in analysis.tasks:
            # 에이전트 ID 찾기
            agent_id = None
            for agent in designed_agents:
                if task_req.assigned_agent.lower() in agent.role.lower():
                    agent_id = agent.id
                    break
            
            if not agent_id:
                agent_id = designed_agents[0].id if designed_agents else "default_agent"
            
            task_spec = self.task_design_chain.design(
                task_name=task_req.name,
                description=task_req.description,
                agent_id=agent_id,
                dependencies=task_req.dependencies,
                output_type=task_req.output_type,
                system_context=system_context,
            )
            designed_tasks.append(task_spec)
        
        # 4. YAML 스펙 생성
        spec_yaml = self.spec_generation_chain.generate(
            domain=analysis.domain,
            summary=analysis.summary,
            agents=[a.model_dump() for a in designed_agents],
            tasks=[t.model_dump() for t in designed_tasks],
            workflow_type=analysis.workflow_type,
            tools=analysis.suggested_tools,
        )
        
        # 5. 스펙 검증
        validation = self.validation_chain.validate(spec_yaml)
        
        logger.info("=== 에이전트 생성 파이프라인 완료 ===")
        
        return {
            "analysis": analysis.model_dump(),
            "agents": [a.model_dump() for a in designed_agents],
            "tasks": [t.model_dump() for t in designed_tasks],
            "spec_yaml": spec_yaml,
            "validation": validation.model_dump(),
        }


# =============================================================================
# Domain Classification Chain
# =============================================================================

class DomainClassificationChain(BaseChainFactory):
    """도메인 타입 분류 체인"""

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return DOMAIN_CLASSIFICATION_SYSTEM

    def get_user_prompt(self) -> str:
        """사용자 프롬프트 템플릿 반환"""
        return DOMAIN_CLASSIFICATION_USER

    def get_output_model(self):
        """출력 모델 반환"""
        return DomainClassification

    def classify(
        self,
        requirement: str,
        use_korean: bool = False,
        llm_config: Optional["LLMConfig"] = None
    ) -> DomainClassification:
        """
        요구사항의 도메인 타입을 분류합니다.

        Args:
            requirement: 요구사항 텍스트
            use_korean: 한글 프롬프트 사용 여부 (기본: False)
            llm_config: LLM 설정 (선택사항)

        Returns:
            DomainClassification: 분류 결과
        """
        logger.info(f"도메인 분류 시작: {requirement[:100]}...")

        # 한글 프롬프트 선택
        user_prompt = DOMAIN_CLASSIFICATION_USER_KO if use_korean else DOMAIN_CLASSIFICATION_USER

        # 프롬프트 변수
        prompt_vars = {"requirement": requirement}

        # LangChain 사용 가능 시
        if LANGCHAIN_AVAILABLE:
            try:
                result_dict = self.invoke(prompt_vars)
                result = DomainClassification(**result_dict)
                logger.info(f"분류 완료: {result.domain_type} (confidence: {result.confidence})")
                return result
            except Exception as e:
                logger.error(f"LangChain 체인 실행 실패: {e}")
                raise

        # Fallback: 직접 LLM 호출
        else:
            from caas_framework.llm.client import create_llm_client

            client = create_llm_client(llm_config)

            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": user_prompt.format(**prompt_vars)},
            ]

            try:
                response = client.chat(messages, response_format={"type": "json_object"})
                result_dict = json.loads(response)
                result = DomainClassification(**result_dict)
                logger.info(f"분류 완료: {result.domain_type} (confidence: {result.confidence})")
                return result
            except Exception as e:
                logger.error(f"LLM 호출 실패: {e}")
                # 기본값 반환
                return DomainClassification(
                    domain_type=DomainType.CUSTOM,
                    confidence=0.0,
                    reasoning="분류 실패로 기본값 반환",
                    core_entities=[],
                    core_operations=[],
                    execution_pattern=ExecutionPattern.CRUD_APPLICATION,
                    keywords=[],
                    alternate_types=[],
                )


# =============================================================================
# System Architect Chain
# =============================================================================

class SystemArchitectChain(BaseChainFactory):
    """
    시스템 아키텍처 설계 체인
    
    RequirementAnalysis를 입력받아 ArchitectureDesign을 생성합니다.
    """

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        from caas_framework.llm.prompts.architecture import ARCHITECTURE_DESIGN_SYSTEM
        return ARCHITECTURE_DESIGN_SYSTEM

    def get_user_prompt(self) -> str:
        """사용자 프롬프트 반환"""
        from caas_framework.llm.prompts.architecture import ARCHITECTURE_DESIGN_USER
        return ARCHITECTURE_DESIGN_USER

    def get_output_model(self):
        """출력 모델 반환"""
        from caas_framework.models import ArchitectureDesign
        return ArchitectureDesign

    def design_architecture(
        self,
        requirement_analysis: RequirementAnalysis
    ) -> "ArchitectureDesign":
        """
        요구사항 분석 결과를 기반으로 시스템 아키텍처를 설계합니다.

        Args:
            requirement_analysis: 요구사항 분석 결과

        Returns:
            ArchitectureDesign: 아키텍처 설계 결과
        """
        from caas_framework.models import ArchitectureDesign

        logger.info("시스템 아키텍처 설계 시작")

        # 입력 준비
        inputs = {
            "requirement_analysis": self._format_requirement_analysis(requirement_analysis),
            "domain": requirement_analysis.domain,
            "workflow_type": requirement_analysis.workflow_type.value,
            "num_agents": len(requirement_analysis.agents),
            "num_tasks": len(requirement_analysis.tasks),
            "constraints": ", ".join(requirement_analysis.constraints) if requirement_analysis.constraints else "None",
            "success_criteria": ", ".join(requirement_analysis.success_criteria) if requirement_analysis.success_criteria else "None",
        }

        try:
            # LLM 체인 실행
            result = self.invoke(inputs)

            # Pydantic 모델로 변환
            architecture = ArchitectureDesign(**result)

            logger.info(
                f"✅ 아키텍처 설계 완료: {architecture.architectural_pattern.value}, "
                f"{len(architecture.components)} components, "
                f"confidence: {architecture.design_confidence:.2f}"
            )

            return architecture

        except Exception as e:
            logger.error(f"❌ 아키텍처 설계 실패: {e}", exc_info=True)
            raise

    def _format_requirement_analysis(self, analysis: RequirementAnalysis) -> str:
        """
        RequirementAnalysis를 읽기 쉬운 텍스트로 포맷팅합니다.

        Args:
            analysis: 요구사항 분석 결과

        Returns:
            str: 포맷팅된 텍스트
        """
        text = f"""
## Summary
{analysis.summary}

## Domain
- Main Domain: {analysis.domain}
- Subdomain: {analysis.subdomain or "N/A"}

## Agents ({len(analysis.agents)})
"""
        for agent in analysis.agents:
            text += f"- {agent.role}: {agent.goal}\n"
            text += f"  Skills: {', '.join(agent.skills)}\n"
            text += f"  Priority: {agent.priority}/5\n"

        text += f"\n## Tasks ({len(analysis.tasks)})\n"
        for task in analysis.tasks:
            text += f"- {task.name}: {task.description}\n"
            text += f"  Assigned to: {task.assigned_agent}\n"
            text += f"  Dependencies: {', '.join(task.dependencies) if task.dependencies else 'None'}\n"
            text += f"  Output Type: {task.output_type}\n"

        text += f"\n## Workflow Type\n{analysis.workflow_type.value}\n"

        text += f"\n## Suggested Tools\n"
        text += ", ".join(analysis.suggested_tools) if analysis.suggested_tools else "None specified"

        text += f"\n\n## Constraints\n"
        for constraint in analysis.constraints:
            text += f"- {constraint}\n"

        text += f"\n## Success Criteria\n"
        for criterion in analysis.success_criteria:
            text += f"- {criterion}\n"

        if analysis.project_template != ProjectTemplate.AGENT_ONLY:
            text += f"\n## Project Template\n{analysis.project_template.value}\n"

        if analysis.requires_ui:
            text += f"\n## UI Requirements\n"
            text += f"- Requires UI: Yes\n"
            text += f"- Pages: {len(analysis.ui_pages)}\n"

        if analysis.requires_backend:
            text += f"\n## Backend Requirements\n"
            text += f"- Requires Backend: Yes\n"
            text += f"- APIs: {len(analysis.backend_apis)}\n"

        if analysis.requires_database:
            text += f"\n## Database Requirements\n"
            text += f"- Requires Database: Yes\n"
            text += f"- Tables: {', '.join(analysis.database_tables)}\n"

        return text.strip()


# =============================================================================
# Requirement Concretization Chain (Golden Data Generation)
# =============================================================================

class RequirementConcretizationChain(BaseChainFactory):
    """
    요구사항 구체화 체인 (Golden Data 생성)

    사용자의 모호하고 불완전한 요구사항을 구체화된 Golden Data로 변환합니다.

    Purpose:
    - 모호한 입력을 명확하고 구체적인 요구사항으로 변환
    - 시스템 범위, 기능, 데이터 모델, UI, NFR을 명시적으로 정의
    - 모든 후속 단계의 Golden Reference로 활용
    """

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return CONCRETIZATION_SYSTEM

    def get_user_prompt(self) -> str:
        """사용자 프롬프트 반환"""
        return CONCRETIZATION_USER_TEMPLATE

    def get_output_model(self):
        """출력 모델 반환"""
        return ConcretizedRequirement

    def concretize(
        self,
        requirement_text: str,
        **kwargs
    ) -> ConcretizedRequirement:
        """
        요구사항을 구체화합니다.

        Args:
            requirement_text: 사용자의 원본 요구사항 (자연어)
            **kwargs: 추가 컨텍스트

        Returns:
            ConcretizedRequirement: 구체화된 요구사항 (Golden Data)
        """
        logger.info("🎯 Starting requirement concretization...")
        logger.debug(f"Input requirement length: {len(requirement_text)} characters")

        # 입력 딕셔너리 생성
        inputs = {
            "requirement_text": requirement_text,
            **kwargs
        }

        # 체인 실행 (부모 클래스의 invoke 호출)
        result = super().invoke(inputs)

        # 결과가 dict인 경우 ConcretizedRequirement로 변환
        if isinstance(result, dict):
            result = ConcretizedRequirement(**result)

        # 품질 메트릭 계산
        if isinstance(result, ConcretizedRequirement):
            result.concretization_quality = result.compute_concretization_quality()

            quality = result.concretization_quality
            logger.info(
                f"✅ Concretization completed - "
                f"Overall Quality: {quality.overall_quality:.2f}, "
                f"Completeness: {quality.completeness_score:.2f}, "
                f"Clarity: {quality.clarity_score:.2f}"
            )

            if quality.quality_issues:
                logger.warning(f"⚠️ Quality Issues: {', '.join(quality.quality_issues)}")

        return result

    @staticmethod
    def format_concretized_requirement(concretized: ConcretizedRequirement) -> str:
        """
        ConcretizedRequirement를 읽기 쉬운 텍스트로 변환

        Args:
            concretized: 구체화된 요구사항

        Returns:
            str: 포맷된 텍스트
        """
        text = "# Concretized Requirement (Golden Data)\n\n"

        # System Scope
        text += "## System Scope\n"
        text += f"**Project Name**: {concretized.system_scope.project_name}\n"
        text += f"**Purpose**: {concretized.system_scope.purpose}\n"
        text += f"**System Type**: {concretized.system_scope.system_type}\n"
        text += f"**Target Users**: {', '.join(concretized.system_scope.target_users)}\n"
        text += f"**Description**: {concretized.system_scope.scope_description}\n\n"

        # Features
        text += f"## Features ({len(concretized.features)})\n"
        for feature in concretized.features:
            text += f"\n### {feature.id}: {feature.name} (Priority: {feature.priority})\n"
            text += f"{feature.description}\n\n"

            if feature.acceptance_criteria:
                text += "**Acceptance Criteria**:\n"
                for criteria in feature.acceptance_criteria:
                    text += f"- {criteria}\n"

            if feature.functional_requirements:
                text += "\n**Functional Requirements**:\n"
                for req in feature.functional_requirements:
                    text += f"- {req}\n"

            if feature.user_stories:
                text += "\n**User Stories**:\n"
                for story in feature.user_stories:
                    text += f"- {story}\n"

        # Data Models
        if concretized.data_models:
            text += f"\n## Data Models ({len(concretized.data_models)})\n"
            for model in concretized.data_models:
                text += f"\n### {model.entity_name}\n"
                text += f"{model.description}\n\n"

                if model.attributes:
                    text += "**Attributes**:\n"
                    for attr in model.attributes:
                        text += f"- {attr.name}: {attr.type} (required: {attr.required})\n"

                if model.relationships:
                    text += "\n**Relationships**:\n"
                    for rel in model.relationships:
                        text += f"- {rel.type} → {rel.target}\n"

                if model.constraints:
                    text += "\n**Constraints**:\n"
                    for constraint in model.constraints:
                        text += f"- {constraint}\n"

        # UI Components
        if concretized.ui_components:
            text += f"\n## UI Components ({len(concretized.ui_components)})\n"
            for ui in concretized.ui_components:
                text += f"\n### {ui.id}: {ui.component_type}\n"
                text += f"**Page**: {ui.page_name}\n"
                text += f"**Purpose**: {ui.purpose}\n"

                if ui.data_source:
                    text += f"**Data Source**: {ui.data_source}\n"

                if ui.interactions:
                    text += f"**Interactions**: {', '.join(ui.interactions)}\n"

                if ui.related_features:
                    text += f"**Related Features**: {', '.join(ui.related_features)}\n"

        # Non-Functional Requirements
        text += "\n## Non-Functional Requirements\n"
        nfr = concretized.non_functional_requirements

        if nfr.performance:
            text += f"**Performance**: {nfr.performance}\n"
        if nfr.security:
            text += f"**Security**: {nfr.security}\n"
        if nfr.scalability:
            text += f"**Scalability**: {nfr.scalability}\n"
        if nfr.reliability:
            text += f"**Reliability**: {nfr.reliability}\n"
        if nfr.usability:
            text += f"**Usability**: {nfr.usability}\n"
        if nfr.maintainability:
            text += f"**Maintainability**: {nfr.maintainability}\n"
        if nfr.availability:
            text += f"**Availability**: {nfr.availability}\n"

        # Constraints & Assumptions
        if concretized.constraints:
            text += "\n## Constraints\n"
            for constraint in concretized.constraints:
                text += f"- {constraint}\n"

        if concretized.assumptions:
            text += "\n## Assumptions\n"
            for assumption in concretized.assumptions:
                text += f"- {assumption}\n"

        # Success Criteria
        if concretized.success_criteria:
            text += "\n## Success Criteria\n"
            for criterion in concretized.success_criteria:
                text += f"- {criterion}\n"

        # Quality Metrics
        if concretized.concretization_quality:
            quality = concretized.concretization_quality
            text += "\n## Quality Metrics\n"
            text += f"**Overall Quality**: {quality.overall_quality:.2f}\n"
            text += f"**Completeness**: {quality.completeness_score:.2f}\n"
            text += f"**Clarity**: {quality.clarity_score:.2f}\n"
            text += f"**Consistency**: {quality.consistency_score:.2f}\n"
            text += f"**Feasibility**: {quality.feasibility_score:.2f}\n"
            text += f"**Complexity**: {quality.complexity_score}/10\n"
            text += f"**Confidence**: {quality.confidence_score:.2f}\n"

            if quality.quality_issues:
                text += "\n**Quality Issues**:\n"
                for issue in quality.quality_issues:
                    text += f"- ⚠️ {issue}\n"

            if quality.improvement_suggestions:
                text += "\n**Improvement Suggestions**:\n"
                for suggestion in quality.improvement_suggestions:
                    text += f"- 💡 {suggestion}\n"

        return text.strip()
