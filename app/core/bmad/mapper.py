"""
BMAD Role Mapper

분석된 요구사항을 에이전트 역할에 매핑합니다.
온톨로지를 활용하여 최적의 역할-태스크-도구 조합을 결정합니다.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum

from app.utils.logger import get_logger, LoggerMixin
from app.knowledge.ontology import (
    OntologyManager,
    AgentRole,
    TaskType,
)
from app.core.bmad.analyzer import AnalysisResult, ExtractedFeature
from app.models.domain_types import DomainType
from app.knowledge.agent_patterns import get_agent_pattern, is_build_agent
from app.core.bmad.models import AgentMapping, TaskMapping, MappingResult
from app.core.bmad.task_refiner import TaskRefiner

logger = get_logger("bmad.mapper")


class RoleMapper(LoggerMixin):
    """
    역할 매퍼
    
    분석 결과를 바탕으로 에이전트 역할과 태스크를 매핑합니다.
    온톨로지를 활용하여 최적의 조합을 결정합니다.
    """
    
    def __init__(self):
        self.ontology = OntologyManager()
        self.task_refiner = TaskRefiner()

        # 역할별 기본 backstory 템플릿
        self.backstory_templates = {
            AgentRole.RESEARCHER: """You are a seasoned researcher with extensive experience 
in gathering and synthesizing information from various sources. Your expertise lies 
in identifying key insights and presenting them clearly and accurately.""",
            
            AgentRole.ANALYST: """You are an expert analyst with strong skills in data 
interpretation and pattern recognition. You excel at transforming complex information 
into actionable insights and clear recommendations.""",
            
            AgentRole.WRITER: """You are a skilled writer with years of experience creating 
engaging and informative content. You have a talent for explaining complex topics 
in accessible language and structuring information effectively.""",
            
            AgentRole.DEVELOPER: """You are an experienced software developer proficient 
in multiple programming languages and frameworks. You write clean, efficient, and 
well-documented code.""",
            
            AgentRole.REVIEWER: """You are a meticulous reviewer with a keen eye for detail. 
Your expertise includes identifying errors, inconsistencies, and areas for improvement 
in various types of content and code.""",
            
            AgentRole.PLANNER: """You are a strategic planner with expertise in project 
management and resource allocation. You excel at breaking down complex projects into 
manageable tasks and creating effective execution plans.""",
            
            AgentRole.COORDINATOR: """You are an experienced coordinator skilled at managing 
multiple stakeholders and ensuring smooth collaboration. You excel at communication 
and keeping projects on track.""",
        }
    
    def map(self, analysis: AnalysisResult) -> MappingResult:
        """
        분석 결과를 에이전트-태스크 매핑으로 변환합니다.

        Args:
            analysis: 요구사항 분석 결과 (domain_classification 포함)

        Returns:
            MappingResult: 매핑 결과
        """
        self.logger.info(f"역할 매핑 시작: {len(analysis.features)} features")

        # 1. 기능별 태스크 유형 결정 (도메인 분류 및 엔티티 정보 전달)
        core_entities = (
            analysis.domain_classification.core_entities
            if analysis.domain_classification
            else []
        )
        task_mappings = self._create_task_mappings(
            analysis.features,
            domain_classification=analysis.domain_classification,
            core_entities=core_entities
        )

        # 2. 필요한 에이전트 역할 결정 (도메인 분류 정보 전달)
        agent_mappings = self._create_agent_mappings(
            task_mappings,
            analysis.domain_context.domain,
            domain_classification=analysis.domain_classification
        )

        # 3. 태스크-에이전트 할당
        self._assign_tasks_to_agents(task_mappings, agent_mappings)

        # 4. 도구 요구사항 수집
        all_tools = set()
        for agent in agent_mappings:
            all_tools.update(agent.recommended_tools)

        result = MappingResult(
            agents=agent_mappings,
            tasks=task_mappings,
            workflow_type=analysis.suggested_workflow,
            tool_requirements=list(all_tools),
            confidence_score=self._calculate_confidence(agent_mappings, task_mappings),
        )

        self.logger.info(f"매핑 완료: {len(agent_mappings)} agents, {len(task_mappings)} tasks")
        return result
    
    def _create_task_mappings(
        self,
        features: List[ExtractedFeature],
        domain_classification=None,
        core_entities: List[str] = None
    ) -> List[TaskMapping]:
        """
        기능에서 태스크 매핑 생성

        Args:
            features: 추출된 기능 목록
            domain_classification: 도메인 분류 정보
            core_entities: 핵심 엔티티 목록

        Returns:
            정제된 태스크 매핑 목록
        """
        task_mappings = []
        entities = core_entities or []

        for feature in features:
            # 태스크 유형 추론
            task_type = self._infer_task_type(feature.name, feature.description)

            # 필요한 도구 결정
            tools = self.ontology.get_suitable_tools(task_type)

            mapping = TaskMapping(
                id=f"task_{feature.id}",
                name=feature.name,
                description=feature.description,
                task_type=task_type,
                assigned_agent_id="",  # 나중에 할당
                dependencies=[f"task_{dep}" for dep in feature.dependencies],
                expected_output=f"Output of {feature.name}",
                required_tools=tools,
            )

            # Task Refiner로 정제 (도메인 분류 정보가 있는 경우)
            if domain_classification and hasattr(domain_classification, 'domain_type'):
                refined_mapping = self.task_refiner.refine_task(
                    task=mapping,
                    domain_type=domain_classification.domain_type,
                    entities=entities
                )
                task_mappings.append(refined_mapping)

                self.logger.debug(
                    f"Task 정제됨: {mapping.name} → "
                    f"description_length={len(refined_mapping.description)} chars"
                )
            else:
                task_mappings.append(mapping)

        return task_mappings
    
    def _create_agent_mappings(
        self,
        task_mappings: List[TaskMapping],
        domain: str,
        domain_classification=None,
    ) -> List[AgentMapping]:
        """
        태스크에 필요한 에이전트 매핑 생성

        도메인 분류 정보가 있으면 도메인별 agent pattern의 execution_agents를 우선 사용합니다.
        """
        # 도메인 분류 정보 활용 (우선)
        if domain_classification and hasattr(domain_classification, 'domain_type'):
            self.logger.info(
                f"도메인 패턴 사용: {domain_classification.domain_type} "
                f"(confidence: {domain_classification.confidence:.2%})"
            )
            return self._create_domain_specific_agents(
                task_mappings,
                domain_classification,
                domain
            )

        # Fallback: 온톨로지 기반 범용 매핑
        self.logger.info("온톨로지 기반 범용 매핑 사용")
        return self._create_ontology_based_agents(task_mappings, domain)

    def _create_domain_specific_agents(
        self,
        task_mappings: List[TaskMapping],
        domain_classification,
        domain: str,
    ) -> List[AgentMapping]:
        """도메인별 실행 Agent 패턴 사용"""
        # 도메인 패턴 가져오기
        pattern = get_agent_pattern(domain_classification.domain_type)

        agent_mappings = []
        execution_agents = pattern.execution_agents

        if not execution_agents:
            self.logger.warning(f"도메인 {domain_classification.domain_type}에 실행 Agent 없음. Fallback 사용.")
            return self._create_ontology_based_agents(task_mappings, domain)

        # 실행 Agent 생성
        for i, agent_spec in enumerate(execution_agents, 1):
            # 관련 태스크 할당 (간단한 매칭: 첫 N개 태스크)
            tasks_per_agent = len(task_mappings) // len(execution_agents) + 1
            start_idx = (i - 1) * tasks_per_agent
            end_idx = min(start_idx + tasks_per_agent, len(task_mappings))
            assigned_tasks = task_mappings[start_idx:end_idx]

            # 도구 수집
            tools = set()
            for task in assigned_tasks:
                tools.update(task.required_tools)

            # Agent 매핑 생성
            mapping = AgentMapping(
                id=f"agent_{i}",
                role=agent_spec["role"].replace("_", " ").title(),
                role_type=AgentRole.EXECUTOR,  # 실행 Agent는 EXECUTOR로 분류
                goal=agent_spec["goal"],
                backstory=self._generate_domain_backstory(agent_spec),
                assigned_tasks=[task.id for task in assigned_tasks],
                recommended_tools=list(tools),
                priority=i,
            )
            agent_mappings.append(mapping)

        self.logger.info(f"도메인 특화 Agent {len(agent_mappings)}개 생성됨")
        return agent_mappings

    def _create_ontology_based_agents(
        self,
        task_mappings: List[TaskMapping],
        domain: str,
    ) -> List[AgentMapping]:
        """온톨로지 기반 범용 Agent 생성 (기존 로직)"""
        # 필요한 역할 수집
        required_roles: Dict[AgentRole, List[TaskMapping]] = {}

        for task in task_mappings:
            # 태스크 유형에 적합한 역할 찾기
            suitable_roles = self._get_suitable_roles_for_task(task.task_type)

            # 첫 번째 적합한 역할 사용
            if suitable_roles:
                role = suitable_roles[0]

                # Build Agent 필터링
                if is_build_agent(role.value):
                    self.logger.debug(f"Build agent 필터링됨: {role.value}")
                    continue

                if role not in required_roles:
                    required_roles[role] = []
                required_roles[role].append(task)

        # 에이전트 매핑 생성
        agent_mappings = []
        for i, (role, tasks) in enumerate(required_roles.items(), 1):
            # 역할에 맞는 도구 추천
            tools = set()
            for task in tasks:
                tools.update(task.required_tools)

            mapping = AgentMapping(
                id=f"agent_{i}",
                role=self._format_role_name(role, domain),
                role_type=role,
                goal=self._generate_goal(role, tasks),
                backstory=self._get_backstory(role),
                assigned_tasks=[task.id for task in tasks],
                recommended_tools=list(tools),
                priority=i,
            )
            agent_mappings.append(mapping)

        return agent_mappings

    def _generate_domain_backstory(self, agent_spec: Dict) -> str:
        """도메인 특화 Agent backstory 생성"""
        role = agent_spec["role"]
        skills = ", ".join(agent_spec.get("skills", []))

        return f"""You are an expert {role.replace('_', ' ')} with specialized skills in {skills}.
You excel at {agent_spec['goal'].lower()} and deliver high-quality results consistently."""
    
    def _assign_tasks_to_agents(
        self,
        task_mappings: List[TaskMapping],
        agent_mappings: List[AgentMapping],
    ) -> None:
        """태스크를 에이전트에 할당"""
        for agent in agent_mappings:
            for task_id in agent.assigned_tasks:
                for task in task_mappings:
                    if task.id == task_id:
                        task.assigned_agent_id = agent.id
                        break
    
    def _infer_task_type(self, name: str, description: str) -> TaskType:
        """태스크 이름과 설명에서 유형 추론"""
        text = f"{name} {description}".lower()
        
        # 키워드 기반 추론
        if any(kw in text for kw in ["search", "collect", "gather", "find", "수집", "검색"]):
            return TaskType.RESEARCH
        elif any(kw in text for kw in ["analyze", "analyse", "분석", "파악", "평가"]):
            return TaskType.ANALYSIS
        elif any(kw in text for kw in ["write", "create", "generate", "작성", "생성", "만들"]):
            return TaskType.WRITING
        elif any(kw in text for kw in ["code", "develop", "implement", "코딩", "개발", "구현"]):
            return TaskType.CODING
        elif any(kw in text for kw in ["review", "check", "verify", "검토", "확인", "검증"]):
            return TaskType.REVIEW
        elif any(kw in text for kw in ["plan", "organize", "schedule", "계획", "조직"]):
            return TaskType.PLANNING
        elif any(kw in text for kw in ["summarize", "summary", "요약"]):
            return TaskType.SUMMARIZATION
        elif any(kw in text for kw in ["translate", "convert", "번역", "변환"]):
            return TaskType.TRANSLATION
        else:
            return TaskType.GENERAL
    
    def _get_suitable_roles_for_task(self, task_type: TaskType) -> List[AgentRole]:
        """태스크 유형에 적합한 역할 목록 반환"""
        mapping = {
            TaskType.RESEARCH: [AgentRole.RESEARCHER],
            TaskType.ANALYSIS: [AgentRole.ANALYST, AgentRole.RESEARCHER],
            TaskType.WRITING: [AgentRole.WRITER],
            TaskType.CODING: [AgentRole.DEVELOPER],
            TaskType.REVIEW: [AgentRole.REVIEWER],
            TaskType.PLANNING: [AgentRole.PLANNER],
            TaskType.SUMMARIZATION: [AgentRole.WRITER, AgentRole.ANALYST],
            TaskType.TRANSLATION: [AgentRole.WRITER],
            TaskType.DATA_PROCESSING: [AgentRole.ANALYST, AgentRole.DEVELOPER],
            TaskType.GENERAL: [AgentRole.RESEARCHER],
        }
        return mapping.get(task_type, [AgentRole.RESEARCHER])
    
    def _format_role_name(self, role: AgentRole, domain: str) -> str:
        """역할 이름 포맷팅"""
        domain_prefix = domain.title() if domain else ""
        role_name = role.value.replace("_", " ").title()
        return f"Senior {domain_prefix} {role_name}".strip()
    
    def _generate_goal(self, role: AgentRole, tasks: List[TaskMapping]) -> str:
        """역할과 태스크 기반 목표 생성"""
        task_descriptions = [task.description for task in tasks[:3]]  # 최대 3개
        tasks_text = "; ".join(task_descriptions)
        
        goal_templates = {
            AgentRole.RESEARCHER: f"Research and gather comprehensive information. Tasks: {tasks_text}",
            AgentRole.ANALYST: f"Analyze data and extract actionable insights. Tasks: {tasks_text}",
            AgentRole.WRITER: f"Create high-quality written content. Tasks: {tasks_text}",
            AgentRole.DEVELOPER: f"Develop efficient and well-structured code. Tasks: {tasks_text}",
            AgentRole.REVIEWER: f"Review and ensure quality and accuracy. Tasks: {tasks_text}",
            AgentRole.PLANNER: f"Create and manage execution plans. Tasks: {tasks_text}",
            AgentRole.COORDINATOR: f"Coordinate activities and ensure smooth collaboration. Tasks: {tasks_text}",
        }
        
        return goal_templates.get(role, f"Complete assigned tasks effectively. Tasks: {tasks_text}")
    
    def _get_backstory(self, role: AgentRole) -> str:
        """역할별 backstory 반환"""
        return self.backstory_templates.get(
            role,
            "You are an experienced professional with expertise in your field."
        )
    
    def _calculate_confidence(
        self,
        agents: List[AgentMapping],
        tasks: List[TaskMapping],
    ) -> float:
        """매핑 신뢰도 계산"""
        if not agents or not tasks:
            return 0.0
        
        # 모든 태스크가 할당되었는지 확인
        assigned_count = sum(1 for task in tasks if task.assigned_agent_id)
        assignment_ratio = assigned_count / len(tasks) if tasks else 0
        
        # 에이전트당 태스크 수 균형
        tasks_per_agent = [len(a.assigned_tasks) for a in agents]
        if tasks_per_agent:
            avg_tasks = sum(tasks_per_agent) / len(tasks_per_agent)
            variance = sum((t - avg_tasks) ** 2 for t in tasks_per_agent) / len(tasks_per_agent)
            balance_score = 1.0 / (1.0 + variance * 0.1)
        else:
            balance_score = 0.5
        
        # 최종 신뢰도
        confidence = (assignment_ratio * 0.6 + balance_score * 0.4)
        return round(confidence, 2)
