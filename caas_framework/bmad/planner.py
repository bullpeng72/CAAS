"""
BMAD Sprint Planner

매핑된 에이전트와 태스크를 스프린트 단위로 계획합니다.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from caas_framework.bmad.models import AgentMapping, TaskMapping
from caas_framework.bmad.semantic_mapper import MappingResult

logger = logging.getLogger("caas_framework.bmad.planner")


class SprintStatus(str, Enum):
    """스프린트 상태"""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """태스크 우선순위"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlannedTask(BaseModel):
    """계획된 태스크"""

    task_id: str
    name: str
    description: str
    assigned_agent_id: str
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration: str = "1 iteration"
    dependencies: List[str] = Field(default_factory=list)
    order: int = 0


class Sprint(BaseModel):
    """스프린트"""

    id: str
    name: str
    goal: str
    status: SprintStatus = SprintStatus.PLANNED
    tasks: List[PlannedTask] = Field(default_factory=list)
    agents_involved: List[str] = Field(default_factory=list)
    estimated_iterations: int = 1
    notes: List[str] = Field(default_factory=list)


class SprintPlan(BaseModel):
    """스프린트 계획"""

    project_name: str
    total_sprints: int
    sprints: List[Sprint] = Field(default_factory=list)
    agents: List[AgentMapping] = Field(default_factory=list)
    workflow_type: str = "sequential"
    created_at: datetime = Field(default_factory=datetime.now)
    estimated_total_iterations: int = 0
    risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class SprintPlanner:
    """
    스프린트 플래너

    매핑 결과를 바탕으로 실행 가능한 스프린트 계획을 생성합니다.
    """

    def __init__(self, max_tasks_per_sprint: int = 5):
        self.logger = logger
        self.max_tasks_per_sprint = max_tasks_per_sprint

    def plan(
        self,
        mapping: MappingResult,
        project_name: str = "Generated Project",
    ) -> SprintPlan:
        """
        스프린트 계획을 생성합니다.

        Args:
            mapping: 역할 매핑 결과
            project_name: 프로젝트 이름

        Returns:
            SprintPlan: 스프린트 계획
        """
        self.logger.info(f"스프린트 계획 시작: {project_name}")

        # 태스크 정렬 (의존성 기반)
        sorted_tasks = self._topological_sort(mapping.tasks)

        # 태스크를 스프린트로 그룹화
        sprints = self._group_into_sprints(sorted_tasks, mapping.agents)

        # 전체 예상 iteration 계산
        total_iterations = sum(s.estimated_iterations for s in sprints)

        # 리스크 분석
        risks = self._analyze_risks(mapping, sprints)

        plan = SprintPlan(
            project_name=project_name,
            total_sprints=len(sprints),
            sprints=sprints,
            agents=mapping.agents,
            workflow_type=mapping.workflow_type,
            estimated_total_iterations=total_iterations,
            risks=risks,
            assumptions=self._generate_assumptions(mapping),
        )

        self.logger.info(f"계획 완료: {len(sprints)} sprints, {total_iterations} iterations")
        return plan

    def _topological_sort(self, tasks: List[TaskMapping]) -> List[TaskMapping]:
        """의존성 기반 태스크 정렬 (위상 정렬)"""
        # 인접 리스트 및 진입 차수 계산
        in_degree = {task.id: 0 for task in tasks}
        graph = {task.id: [] for task in tasks}
        task_map = {task.id: task for task in tasks}

        for task in tasks:
            for dep in task.dependencies:
                if dep in graph:
                    graph[dep].append(task.id)
                    in_degree[task.id] += 1

        # 진입 차수가 0인 태스크부터 시작
        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(task_map[current])

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 순환 의존성 체크
        if len(result) != len(tasks):
            self.logger.warning("순환 의존성이 감지되었습니다. 원본 순서 사용")
            return tasks

        return result

    def _group_into_sprints(
        self,
        sorted_tasks: List[TaskMapping],
        agents: List[AgentMapping],
    ) -> List[Sprint]:
        """태스크를 스프린트로 그룹화"""
        sprints = []
        current_tasks: List[PlannedTask] = []
        sprint_num = 1

        for i, task in enumerate(sorted_tasks):
            # 우선순위 결정
            if i == 0:
                priority = TaskPriority.CRITICAL
            elif i < len(sorted_tasks) // 3:
                priority = TaskPriority.HIGH
            elif i < 2 * len(sorted_tasks) // 3:
                priority = TaskPriority.MEDIUM
            else:
                priority = TaskPriority.LOW

            planned_task = PlannedTask(
                task_id=task.id,
                name=task.name,
                description=task.description,
                assigned_agent_id=task.assigned_agent_id,
                priority=priority,
                dependencies=task.dependencies,
                order=len(current_tasks) + 1,
            )
            current_tasks.append(planned_task)

            # 스프린트 최대 태스크 수에 도달하거나 마지막 태스크
            if len(current_tasks) >= self.max_tasks_per_sprint or i == len(sorted_tasks) - 1:
                # 관련 에이전트 수집
                agent_ids = list(
                    set(t.assigned_agent_id for t in current_tasks if t.assigned_agent_id)
                )

                sprint = Sprint(
                    id=f"sprint_{sprint_num}",
                    name=f"Sprint {sprint_num}",
                    goal=self._generate_sprint_goal(current_tasks),
                    tasks=current_tasks,
                    agents_involved=agent_ids,
                    estimated_iterations=len(current_tasks),
                )
                sprints.append(sprint)

                current_tasks = []
                sprint_num += 1

        return sprints

    def _generate_sprint_goal(self, tasks: List[PlannedTask]) -> str:
        """스프린트 목표 생성"""
        if not tasks:
            return "Complete planned tasks"

        # 첫 번째 태스크 기반 목표
        first_task = tasks[0]
        if len(tasks) == 1:
            return f"Complete: {first_task.name}"
        else:
            return f"Complete {len(tasks)} tasks starting with: {first_task.name}"

    def _analyze_risks(
        self,
        mapping: MappingResult,
        sprints: List[Sprint],
    ) -> List[str]:
        """리스크 분석"""
        risks = []

        # 에이전트 수 대비 태스크 수 체크
        total_tasks = sum(len(s.tasks) for s in sprints)
        if total_tasks > len(mapping.agents) * 5:
            risks.append("태스크 수가 에이전트 수 대비 많습니다. 병목 현상이 발생할 수 있습니다.")

        # 긴 의존성 체인 체크
        max_deps = max((len(t.dependencies) for s in sprints for t in s.tasks), default=0)
        if max_deps > 3:
            risks.append("의존성 체인이 깁니다. 순차 실행으로 인한 지연이 발생할 수 있습니다.")

        # 단일 에이전트 과부하 체크
        agent_tasks = {}
        for sprint in sprints:
            for task in sprint.tasks:
                agent_id = task.assigned_agent_id
                agent_tasks[agent_id] = agent_tasks.get(agent_id, 0) + 1

        if agent_tasks:
            avg_tasks = sum(agent_tasks.values()) / len(agent_tasks)
            for agent_id, count in agent_tasks.items():
                if count > avg_tasks * 2:
                    risks.append(f"에이전트 {agent_id}에 태스크가 집중되어 있습니다.")

        return risks

    def _generate_assumptions(self, mapping: MappingResult) -> List[str]:
        """가정 사항 생성"""
        assumptions = [
            "모든 외부 API와 도구가 정상적으로 작동합니다.",
            "LLM 응답이 적절한 품질을 유지합니다.",
        ]

        if "web_search" in mapping.tool_requirements:
            assumptions.append("웹 검색 결과가 관련성 있고 최신 정보를 제공합니다.")

        if mapping.workflow_type == "hierarchical":
            assumptions.append("에이전트 간 위계가 명확하게 정의되어 있습니다.")

        return assumptions

    def optimize_plan(self, plan: SprintPlan) -> SprintPlan:
        """
        계획을 최적화합니다.

        Args:
            plan: 원본 스프린트 계획

        Returns:
            SprintPlan: 최적화된 계획
        """
        # 병렬 실행 가능한 태스크 식별
        optimized_sprints = []

        for sprint in plan.sprints:
            # 의존성이 없거나 이전 스프린트에서 완료된 태스크는 병렬 실행 가능
            parallel_groups = self._identify_parallel_groups(sprint.tasks)

            # 최적화된 예상 iteration 계산
            optimized_iterations = len(parallel_groups)

            optimized_sprint = sprint.model_copy(
                update={
                    "estimated_iterations": optimized_iterations,
                    "notes": [f"병렬 실행 가능 그룹: {len(parallel_groups)}개"],
                }
            )
            optimized_sprints.append(optimized_sprint)

        return plan.model_copy(
            update={
                "sprints": optimized_sprints,
                "estimated_total_iterations": sum(
                    s.estimated_iterations for s in optimized_sprints
                ),
            }
        )

    def _identify_parallel_groups(self, tasks: List[PlannedTask]) -> List[List[PlannedTask]]:
        """병렬 실행 가능한 태스크 그룹 식별"""
        completed = set()
        groups = []
        remaining = list(tasks)

        while remaining:
            # 현재 실행 가능한 태스크 (의존성이 모두 완료된 태스크)
            executable = [t for t in remaining if all(dep in completed for dep in t.dependencies)]

            if not executable:
                # 순환 의존성이나 오류 - 나머지 태스크를 하나씩 처리
                executable = [remaining[0]]

            groups.append(executable)

            for task in executable:
                completed.add(task.task_id)
                remaining.remove(task)

        return groups
