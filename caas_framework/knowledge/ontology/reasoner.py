"""
CAAS Ontology Reasoner

온톨로지 기반 추론 기능을 제공합니다.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from caas_framework.utils.logger import get_logger, LoggerMixin
from caas_app.knowledge.ontology.manager import OntologyManager, AgentRole, TaskType

logger = get_logger("knowledge.reasoner")


class InferenceType(str, Enum):
    """추론 유형"""
    ROLE_RECOMMENDATION = "role_recommendation"
    TOOL_RECOMMENDATION = "tool_recommendation"
    TASK_ASSIGNMENT = "task_assignment"
    WORKFLOW_SUGGESTION = "workflow_suggestion"
    DOMAIN_CLASSIFICATION = "domain_classification"


class InferenceResult(BaseModel):
    """추론 결과"""
    inference_type: InferenceType
    confidence: float = Field(ge=0.0, le=1.0)
    recommendations: List[str] = Field(default_factory=list)
    reasoning_path: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReasoningRule(BaseModel):
    """추론 규칙"""
    name: str
    description: str
    conditions: List[str] = Field(default_factory=list)
    conclusions: List[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0.0)


class OntologyReasoner(LoggerMixin):
    """
    온톨로지 추론기
    
    온톨로지 지식을 기반으로 추론을 수행합니다.
    """
    
    def __init__(self, ontology_manager: Optional[OntologyManager] = None):
        self.ontology = ontology_manager or OntologyManager()
        self.rules = self._load_default_rules()
    
    def _load_default_rules(self) -> List[ReasoningRule]:
        """기본 추론 규칙 로드"""
        return [
            # 역할 추천 규칙
            ReasoningRule(
                name="research_requires_researcher",
                description="Research tasks require Researcher role",
                conditions=["task_type == RESEARCH"],
                conclusions=["recommend_role(RESEARCHER)"],
                weight=0.9,
            ),
            ReasoningRule(
                name="analysis_requires_analyst",
                description="Analysis tasks require Analyst role",
                conditions=["task_type == ANALYSIS"],
                conclusions=["recommend_role(ANALYST)"],
                weight=0.9,
            ),
            ReasoningRule(
                name="writing_requires_writer",
                description="Writing tasks require Writer role",
                conditions=["task_type == WRITING"],
                conclusions=["recommend_role(WRITER)"],
                weight=0.9,
            ),
            ReasoningRule(
                name="coding_requires_developer",
                description="Coding tasks require Developer role",
                conditions=["task_type == CODING"],
                conclusions=["recommend_role(DEVELOPER)"],
                weight=0.9,
            ),
            ReasoningRule(
                name="review_requires_reviewer",
                description="Review tasks require Reviewer role",
                conditions=["task_type == REVIEW"],
                conclusions=["recommend_role(REVIEWER)"],
                weight=0.9,
            ),
            
            # 도구 추천 규칙
            ReasoningRule(
                name="research_needs_search",
                description="Research tasks need search tools",
                conditions=["task_type == RESEARCH"],
                conclusions=["recommend_tool(web_search)"],
                weight=0.8,
            ),
            ReasoningRule(
                name="writing_needs_file",
                description="Writing tasks need file tools",
                conditions=["task_type == WRITING"],
                conclusions=["recommend_tool(file_write)"],
                weight=0.8,
            ),
            ReasoningRule(
                name="coding_needs_interpreter",
                description="Coding tasks need code interpreter",
                conditions=["task_type == CODING"],
                conclusions=["recommend_tool(code_interpreter)"],
                weight=0.9,
            ),
            
            # 워크플로우 규칙
            ReasoningRule(
                name="sequential_for_dependent",
                description="Use sequential workflow for dependent tasks",
                conditions=["has_dependencies == True"],
                conclusions=["recommend_workflow(sequential)"],
                weight=0.7,
            ),
            ReasoningRule(
                name="hierarchical_for_complex",
                description="Use hierarchical workflow for complex projects",
                conditions=["task_count > 5", "agent_count > 3"],
                conclusions=["recommend_workflow(hierarchical)"],
                weight=0.6,
            ),
        ]
    
    def infer_roles(
        self,
        task_types: List[TaskType],
        domain: Optional[str] = None,
    ) -> InferenceResult:
        """
        태스크 유형에 적합한 역할을 추론합니다.
        
        Args:
            task_types: 태스크 유형 목록
            domain: 도메인 (옵션)
        
        Returns:
            InferenceResult: 추론 결과
        """
        self.logger.info(f"역할 추론: tasks={task_types}, domain={domain}")
        
        recommendations = []
        reasoning_path = []
        total_weight = 0.0
        
        for task_type in task_types:
            # 온톨로지에서 적합한 역할 조회
            suitable_roles = self.ontology.get_suitable_roles(task_type)
            
            if suitable_roles:
                for role in suitable_roles:
                    if role.value not in recommendations:
                        recommendations.append(role.value)
                        reasoning_path.append(
                            f"Task type '{task_type.value}' → Role '{role.value}'"
                        )
                        total_weight += 0.9
        
        # 도메인 기반 추가 추천
        if domain:
            domain_roles = self._get_domain_roles(domain)
            for role in domain_roles:
                if role not in recommendations:
                    recommendations.append(role)
                    reasoning_path.append(f"Domain '{domain}' → Role '{role}'")
                    total_weight += 0.5
        
        confidence = min(1.0, total_weight / max(len(task_types), 1))
        
        return InferenceResult(
            inference_type=InferenceType.ROLE_RECOMMENDATION,
            confidence=confidence,
            recommendations=recommendations,
            reasoning_path=reasoning_path,
            metadata={"domain": domain, "task_types": [t.value for t in task_types]},
        )
    
    def infer_tools(
        self,
        task_types: List[TaskType],
        roles: Optional[List[AgentRole]] = None,
    ) -> InferenceResult:
        """
        태스크와 역할에 적합한 도구를 추론합니다.

        Args:
            task_types: 태스크 유형 목록
            roles: 에이전트 역할 목록 (옵션)

        Returns:
            InferenceResult: 추론 결과
        """
        self.logger.info(f"도구 추론: tasks={task_types}")

        recommendations = []
        reasoning_path = []

        # Try using new Tool Ontology Manager first
        try:
            from caas_framework.knowledge.ontology import get_tool_ontology_manager
            tool_manager = get_tool_ontology_manager()
            all_tools = tool_manager.get_all_tools(enabled_only=True)

            # Match tools based on task types
            for task_type in task_types:
                task_name = task_type.value.lower()

                for tool in all_tools:
                    # Check if this tool is compatible with the task
                    if task_name in [t.lower() for t in tool.compatible_tasks]:
                        if tool.name not in recommendations:
                            recommendations.append(tool.name)
                            reasoning_path.append(
                                f"Task type '{task_type.value}' → Tool '{tool.name}' (from Ontology)"
                            )
                    # Also check tags and description
                    elif (task_name in " ".join(tool.tags).lower() or
                          task_name in tool.description.lower()):
                        if tool.name not in recommendations:
                            recommendations.append(tool.name)
                            reasoning_path.append(
                                f"Task type '{task_type.value}' → Tool '{tool.name}' (keyword match)"
                            )
        except Exception as e:
            self.logger.warning(f"Failed to use Tool Ontology Manager: {e}, falling back to legacy")

            # Fallback to old method
            for task_type in task_types:
                # 온톨로지에서 적합한 도구 조회
                suitable_tools = self.ontology.get_suitable_tools(task_type)

                for tool in suitable_tools:
                    if tool not in recommendations:
                        recommendations.append(tool)
                        reasoning_path.append(
                            f"Task type '{task_type.value}' → Tool '{tool}' (legacy)"
                        )

        confidence = 0.8 if recommendations else 0.3

        return InferenceResult(
            inference_type=InferenceType.TOOL_RECOMMENDATION,
            confidence=confidence,
            recommendations=recommendations,
            reasoning_path=reasoning_path,
        )
    
    def infer_workflow(
        self,
        task_count: int,
        agent_count: int,
        has_dependencies: bool,
    ) -> InferenceResult:
        """
        적합한 워크플로우 유형을 추론합니다.
        
        Args:
            task_count: 태스크 수
            agent_count: 에이전트 수
            has_dependencies: 의존성 존재 여부
        
        Returns:
            InferenceResult: 추론 결과
        """
        self.logger.info(
            f"워크플로우 추론: tasks={task_count}, agents={agent_count}, deps={has_dependencies}"
        )
        
        recommendations = []
        reasoning_path = []
        confidence = 0.7
        
        # 규칙 기반 추론
        if has_dependencies:
            recommendations.append("sequential")
            reasoning_path.append("Tasks have dependencies → Sequential workflow")
            confidence = 0.8
        
        if task_count > 5 and agent_count > 3:
            if "hierarchical" not in recommendations:
                recommendations.append("hierarchical")
            reasoning_path.append(
                f"Complex project ({task_count} tasks, {agent_count} agents) → Hierarchical workflow"
            )
            confidence = 0.75
        
        if not recommendations:
            recommendations.append("sequential")
            reasoning_path.append("Default → Sequential workflow")
        
        return InferenceResult(
            inference_type=InferenceType.WORKFLOW_SUGGESTION,
            confidence=confidence,
            recommendations=recommendations,
            reasoning_path=reasoning_path,
            metadata={
                "task_count": task_count,
                "agent_count": agent_count,
                "has_dependencies": has_dependencies,
            },
        )
    
    def infer_domain(
        self,
        keywords: List[str],
        description: str = "",
    ) -> InferenceResult:
        """
        키워드와 설명에서 도메인을 추론합니다.
        
        Args:
            keywords: 키워드 목록
            description: 설명 텍스트
        
        Returns:
            InferenceResult: 추론 결과
        """
        self.logger.info(f"도메인 추론: keywords={keywords[:5]}")
        
        # 도메인별 키워드 매핑
        domain_keywords = {
            "finance": ["finance", "financial", "stock", "investment", "trading", "money", "bank", "금융", "투자", "주식"],
            "technology": ["tech", "software", "code", "programming", "developer", "api", "기술", "개발", "코드"],
            "healthcare": ["health", "medical", "patient", "hospital", "doctor", "의료", "건강", "병원"],
            "education": ["education", "learning", "teaching", "student", "course", "교육", "학습"],
            "marketing": ["marketing", "advertisement", "campaign", "brand", "마케팅", "광고"],
            "legal": ["legal", "law", "compliance", "regulation", "contract", "법률", "규정"],
            "research": ["research", "study", "analysis", "experiment", "연구", "분석"],
        }
        
        # 텍스트 결합
        text = " ".join(keywords).lower() + " " + description.lower()
        
        # 도메인 점수 계산
        scores: Dict[str, float] = {}
        reasoning_path = []
        
        for domain, domain_kws in domain_keywords.items():
            score = 0
            matched = []
            for kw in domain_kws:
                if kw in text:
                    score += 1
                    matched.append(kw)
            
            if score > 0:
                scores[domain] = score
                reasoning_path.append(f"Matched '{domain}': {matched}")
        
        # 결과 정렬
        sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        recommendations = [d[0] for d in sorted_domains[:3]]
        
        if not recommendations:
            recommendations = ["general"]
            reasoning_path.append("No specific domain matched → General")
        
        confidence = min(1.0, (sorted_domains[0][1] / 3) if sorted_domains else 0.3)
        
        return InferenceResult(
            inference_type=InferenceType.DOMAIN_CLASSIFICATION,
            confidence=confidence,
            recommendations=recommendations,
            reasoning_path=reasoning_path,
            metadata={"scores": scores},
        )
    
    def infer_task_assignment(
        self,
        tasks: List[Dict[str, Any]],
        agents: List[Dict[str, Any]],
    ) -> InferenceResult:
        """
        태스크를 에이전트에 할당합니다.
        
        Args:
            tasks: 태스크 목록
            agents: 에이전트 목록
        
        Returns:
            InferenceResult: 추론 결과 (할당 정보)
        """
        self.logger.info(f"태스크 할당 추론: {len(tasks)} tasks, {len(agents)} agents")
        
        assignments = []
        reasoning_path = []
        
        for task in tasks:
            task_id = task.get("id", "unknown")
            task_type = task.get("type", "general")
            
            # 가장 적합한 에이전트 찾기
            best_agent = None
            best_score = 0
            
            for agent in agents:
                agent_id = agent.get("id", "")
                agent_role = agent.get("role", "").lower()
                
                # 역할-태스크 매칭 점수 계산
                score = self._calculate_assignment_score(task_type, agent_role)
                
                if score > best_score:
                    best_score = score
                    best_agent = agent_id
            
            if best_agent:
                assignments.append(f"{task_id} → {best_agent}")
                reasoning_path.append(
                    f"Task '{task_id}' (type: {task_type}) assigned to agent '{best_agent}'"
                )
        
        confidence = len(assignments) / max(len(tasks), 1) if tasks else 0.0
        
        return InferenceResult(
            inference_type=InferenceType.TASK_ASSIGNMENT,
            confidence=confidence,
            recommendations=assignments,
            reasoning_path=reasoning_path,
        )
    
    def _get_domain_roles(self, domain: str) -> List[str]:
        """도메인에 권장되는 역할 반환"""
        domain_roles = {
            "finance": ["analyst", "researcher", "writer"],
            "technology": ["developer", "researcher", "reviewer"],
            "healthcare": ["researcher", "analyst", "writer"],
            "education": ["writer", "researcher", "reviewer"],
            "marketing": ["writer", "analyst", "researcher"],
            "legal": ["researcher", "analyst", "reviewer"],
            "research": ["researcher", "analyst", "writer"],
            "general": ["researcher", "writer"],
        }
        return domain_roles.get(domain.lower(), ["researcher"])
    
    def _calculate_assignment_score(self, task_type: str, agent_role: str) -> float:
        """태스크-에이전트 할당 점수 계산"""
        # 역할-태스크 적합도 매트릭스
        compatibility = {
            ("research", "researcher"): 1.0,
            ("analysis", "analyst"): 1.0,
            ("writing", "writer"): 1.0,
            ("coding", "developer"): 1.0,
            ("review", "reviewer"): 1.0,
            ("planning", "planner"): 1.0,
            # 부분 적합
            ("research", "analyst"): 0.6,
            ("analysis", "researcher"): 0.6,
            ("writing", "analyst"): 0.4,
            ("summarization", "writer"): 0.8,
            ("summarization", "analyst"): 0.6,
        }
        
        key = (task_type.lower(), agent_role.lower())
        return compatibility.get(key, 0.3)
    
    def add_rule(self, rule: ReasoningRule) -> None:
        """추론 규칙 추가"""
        self.rules.append(rule)
        self.logger.info(f"추론 규칙 추가: {rule.name}")
    
    def get_rules(self) -> List[ReasoningRule]:
        """모든 추론 규칙 반환"""
        return self.rules.copy()
