"""
LangGraph Workflow Engine

복잡한 AI Agent 워크플로우를 관리하는 LangGraph 기반 엔진
"""

from typing import Dict, Any, List, Optional, Callable, TypedDict, Annotated
import operator
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.utils.logger import get_logger

logger = get_logger("langgraph_engine")


# ========== State Definitions ==========

class WorkflowState(TypedDict):
    """기본 워크플로우 상태"""
    messages: Annotated[List[Dict[str, Any]], operator.add]
    current_phase: str
    phase_results: Dict[str, Any]
    errors: List[str]
    iteration: int
    metadata: Dict[str, Any]


class BMADWorkflowState(TypedDict):
    """BMAD 파이프라인 워크플로우 상태"""
    # Input
    user_request: str

    # Discovery Phase
    requirement_analysis: Optional[Dict[str, Any]]
    discovery_quality_gate: Optional[Dict[str, Any]]

    # Architecture Phase
    architecture_design: Optional[Dict[str, Any]]
    architecture_quality_gate: Optional[Dict[str, Any]]

    # Design Phase
    agent_specs: Optional[List[Dict[str, Any]]]
    task_specs: Optional[List[Dict[str, Any]]]
    design_quality_gate: Optional[Dict[str, Any]]

    # Development Phase
    yaml_spec: Optional[str]
    development_quality_gate: Optional[Dict[str, Any]]

    # Execution Phase (optional)
    execution_result: Optional[Dict[str, Any]]
    validation_report: Optional[Dict[str, Any]]
    reflection_result: Optional[Dict[str, Any]]

    # Control flow
    current_phase: str
    should_regenerate: bool
    regeneration_count: int
    max_regenerations: int
    errors: Annotated[List[str], operator.add]

    # Metadata
    session_id: str
    start_time: datetime
    metadata: Dict[str, Any]


# ========== Node Functions ==========

class NodeFunction:
    """워크플로우 노드 함수 래퍼"""

    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Executing node: {self.name}")
        try:
            result = self.func(state)
            return result
        except Exception as e:
            logger.error(f"Error in node {self.name}: {e}")
            return {**state, "errors": state.get("errors", []) + [str(e)]}


# ========== Workflow Engine ==========

class WorkflowEngine:
    """
    LangGraph 기반 워크플로우 엔진

    복잡한 워크플로우를 정의하고 실행합니다.
    - 조건부 실행
    - 병렬 실행
    - 체크포인트 및 재개
    - 동적 라우팅
    """

    def __init__(self, checkpointer: Optional[Any] = None):
        """
        Args:
            checkpointer: 체크포인트 저장소 (기본: MemorySaver)
        """
        self.checkpointer = checkpointer or MemorySaver()
        self.logger = logger
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None

    def create_graph(self, state_schema: type) -> StateGraph:
        """
        새로운 그래프를 생성합니다.

        Args:
            state_schema: 상태 스키마 (TypedDict)

        Returns:
            StateGraph: 생성된 그래프
        """
        self.graph = StateGraph(state_schema)
        return self.graph

    def add_node(self, name: str, func: Callable):
        """노드 추가"""
        if self.graph is None:
            raise ValueError("Create graph first using create_graph()")

        wrapped_func = NodeFunction(name, func)
        self.graph.add_node(name, wrapped_func)
        self.logger.info(f"Node added: {name}")

    def add_edge(self, from_node: str, to_node: str):
        """엣지 추가 (무조건 실행)"""
        if self.graph is None:
            raise ValueError("Create graph first")

        self.graph.add_edge(from_node, to_node)
        self.logger.info(f"Edge added: {from_node} -> {to_node}")

    def add_conditional_edge(
        self,
        from_node: str,
        condition: Callable,
        edge_mapping: Dict[str, str],
    ):
        """조건부 엣지 추가"""
        if self.graph is None:
            raise ValueError("Create graph first")

        self.graph.add_conditional_edges(from_node, condition, edge_mapping)
        self.logger.info(f"Conditional edge added from: {from_node}")

    def set_entry_point(self, node: str):
        """시작 노드 설정"""
        if self.graph is None:
            raise ValueError("Create graph first")

        self.graph.set_entry_point(node)
        self.logger.info(f"Entry point set: {node}")

    def set_finish_point(self, node: str):
        """종료 노드 설정"""
        if self.graph is None:
            raise ValueError("Create graph first")

        self.graph.add_edge(node, END)
        self.logger.info(f"Finish point set: {node}")

    def compile(self):
        """그래프 컴파일"""
        if self.graph is None:
            raise ValueError("Create graph first")

        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
        self.logger.info("Graph compiled")

    def run(
        self,
        initial_state: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        워크플로우 실행

        Args:
            initial_state: 초기 상태
            config: 실행 설정 (thread_id 등)

        Returns:
            Dict[str, Any]: 최종 상태
        """
        if self.compiled_graph is None:
            raise ValueError("Compile graph first using compile()")

        self.logger.info("Running workflow")

        if config is None:
            config = {"configurable": {"thread_id": "default"}}

        final_state = None
        for state in self.compiled_graph.stream(initial_state, config):
            final_state = state
            self.logger.debug(f"State update: {list(state.keys())}")

        self.logger.info("Workflow completed")
        return final_state

    def get_state(self, config: Dict[str, Any]) -> Any:
        """현재 상태 조회"""
        if self.compiled_graph is None:
            raise ValueError("Compile graph first")

        return self.compiled_graph.get_state(config)

    def update_state(
        self,
        config: Dict[str, Any],
        values: Dict[str, Any],
        as_node: Optional[str] = None,
    ):
        """상태 업데이트"""
        if self.compiled_graph is None:
            raise ValueError("Compile graph first")

        self.compiled_graph.update_state(config, values, as_node=as_node)


# ========== BMAD Workflow Builder ==========

class BMADWorkflowBuilder:
    """
    BMAD 파이프라인을 위한 워크플로우 빌더

    자동 재생성, Quality Gate 체크, Reflection 등을 포함한
    완전한 BMAD 워크플로우를 구성합니다.
    """

    def __init__(self, llm_chains: Dict[str, Any]):
        """
        Args:
            llm_chains: LLM Chain 인스턴스들
                - requirement_chain
                - architecture_chain
                - agent_chain
                - task_chain
                - spec_chain
        """
        self.chains = llm_chains
        self.engine = WorkflowEngine()
        self.logger = logger

    def build(self) -> WorkflowEngine:
        """BMAD 워크플로우 구축"""
        self.logger.info("Building BMAD workflow")

        # 그래프 생성
        self.engine.create_graph(BMADWorkflowState)

        # 노드 추가
        self.engine.add_node("discovery", self._discovery_node)
        self.engine.add_node("discovery_gate", self._discovery_gate_node)
        self.engine.add_node("architecture", self._architecture_node)
        self.engine.add_node("architecture_gate", self._architecture_gate_node)
        self.engine.add_node("design", self._design_node)
        self.engine.add_node("design_gate", self._design_gate_node)
        self.engine.add_node("development", self._development_node)
        self.engine.add_node("development_gate", self._development_gate_node)

        # 시작점
        self.engine.set_entry_point("discovery")

        # 엣지 연결
        self.engine.add_edge("discovery", "discovery_gate")
        self.engine.add_conditional_edge(
            "discovery_gate",
            self._should_continue_after_discovery,
            {
                "continue": "architecture",
                "regenerate": "discovery",
                "end": END,
            }
        )

        self.engine.add_edge("architecture", "architecture_gate")
        self.engine.add_conditional_edge(
            "architecture_gate",
            self._should_continue_after_architecture,
            {
                "continue": "design",
                "regenerate": "architecture",
                "end": END,
            }
        )

        self.engine.add_edge("design", "design_gate")
        self.engine.add_conditional_edge(
            "design_gate",
            self._should_continue_after_design,
            {
                "continue": "development",
                "regenerate": "design",
                "end": END,
            }
        )

        self.engine.add_edge("development", "development_gate")
        self.engine.add_conditional_edge(
            "development_gate",
            self._should_continue_after_development,
            {
                "end": END,
                "regenerate": "development",
            }
        )

        # 컴파일
        self.engine.compile()

        self.logger.info("BMAD workflow built successfully")
        return self.engine

    # ========== Node Implementations ==========

    def _discovery_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Discovery 단계 노드"""
        from app.llm.chains import RequirementAnalysisChain

        chain = RequirementAnalysisChain()
        result = chain.analyze(state["user_request"])

        return {
            "requirement_analysis": result.model_dump(),
            "current_phase": "discovery",
        }

    def _discovery_gate_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Discovery Quality Gate 노드"""
        from app.core.quality_gate import QualityGate

        gate_result = QualityGate.check_discovery_phase(state["requirement_analysis"])

        return {
            "discovery_quality_gate": gate_result.model_dump(),
            "should_regenerate": not gate_result.can_proceed,
        }

    def _architecture_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Architecture 단계 노드"""
        from app.llm.chains import SystemArchitectChain
        from app.models.schemas import RequirementAnalysis

        chain = SystemArchitectChain()
        # dict를 RequirementAnalysis 객체로 변환
        requirement = RequirementAnalysis(**state["requirement_analysis"])
        result = chain.design_architecture(requirement)

        return {
            "architecture_design": result.model_dump(),
            "current_phase": "architecture",
        }

    def _architecture_gate_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Architecture Quality Gate 노드"""
        from app.core.quality_gate import QualityGate

        gate_result = QualityGate.check_architecture_phase(state["architecture_design"])

        return {
            "architecture_quality_gate": gate_result.model_dump(),
            "should_regenerate": not gate_result.can_proceed,
        }

    def _design_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Design 단계 노드"""
        from app.llm.chains import AgentDesignChain, TaskDesignChain
        from app.models.schemas import RequirementAnalysis

        # dict를 RequirementAnalysis 객체로 변환
        requirement = RequirementAnalysis(**state["requirement_analysis"])

        # Agent 스펙 생성
        agent_chain = AgentDesignChain()
        agent_specs = []
        for agent_req in requirement.agents:
            related_tasks = [
                task.description
                for task in requirement.tasks
                if hasattr(task, 'assigned_agent') and task.assigned_agent == agent_req.role
            ]
            spec = agent_chain.design(
                domain=requirement.domain,
                role=agent_req.role,
                goal=agent_req.goal,
                skills=agent_req.skills,
                tasks=related_tasks if related_tasks else [task.description for task in requirement.tasks[:2]],
                available_tools=[],
            )
            agent_specs.append(spec)

        # Task 스펙 생성
        task_chain = TaskDesignChain()
        task_specs = []
        for task_req in requirement.tasks:
            agent_id = None
            if hasattr(task_req, 'assigned_agent'):
                for agent_spec in agent_specs:
                    if agent_spec.role == task_req.assigned_agent:
                        agent_id = agent_spec.id
                        break
            if not agent_id and agent_specs:
                agent_id = agent_specs[0].id

            spec = task_chain.design(
                task_name=task_req.name if hasattr(task_req, 'name') else f"task_{len(task_specs)}",
                description=task_req.description,
                agent_id=agent_id or "default_agent",
                dependencies=task_req.dependencies if hasattr(task_req, 'dependencies') else [],
                output_type=task_req.output_type if hasattr(task_req, 'output_type') else "report",
                system_context=requirement.summary,
            )
            task_specs.append(spec)

        return {
            "agent_specs": [a.model_dump() for a in agent_specs],
            "task_specs": [t.model_dump() for t in task_specs],
            "current_phase": "design",
        }

    def _design_gate_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Design Quality Gate 노드"""
        from app.core.quality_gate import QualityGate

        gate_result = QualityGate.check_design_phase(
            state["agent_specs"],
            state["task_specs"],
        )

        return {
            "design_quality_gate": gate_result.model_dump(),
            "should_regenerate": not gate_result.can_proceed,
        }

    def _development_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Development 단계 노드"""
        from app.llm.chains import SpecGenerationChain

        chain = SpecGenerationChain()
        yaml_spec = chain.generate(
            agent_specs=state["agent_specs"],
            task_specs=state["task_specs"],
            project_name=state["architecture_design"]["project_name"],
        )

        return {
            "yaml_spec": yaml_spec,
            "current_phase": "development",
        }

    def _development_gate_node(self, state: BMADWorkflowState) -> Dict[str, Any]:
        """Development Quality Gate 노드"""
        from app.core.quality_gate import QualityGate

        gate_result = QualityGate.check_development_phase(state["yaml_spec"])

        return {
            "development_quality_gate": gate_result.model_dump(),
            "should_regenerate": not gate_result.can_proceed,
        }

    # ========== Conditional Functions ==========

    def _should_continue_after_discovery(self, state: BMADWorkflowState) -> str:
        """Discovery 이후 진행 여부 결정"""
        if state.get("should_regenerate") and state.get("regeneration_count", 0) < state.get("max_regenerations", 2):
            return "regenerate"
        elif state.get("should_regenerate"):
            return "end"
        else:
            return "continue"

    def _should_continue_after_architecture(self, state: BMADWorkflowState) -> str:
        """Architecture 이후 진행 여부 결정"""
        if state.get("should_regenerate") and state.get("regeneration_count", 0) < state.get("max_regenerations", 2):
            return "regenerate"
        elif state.get("should_regenerate"):
            return "end"
        else:
            return "continue"

    def _should_continue_after_design(self, state: BMADWorkflowState) -> str:
        """Design 이후 진행 여부 결정"""
        if state.get("should_regenerate") and state.get("regeneration_count", 0) < state.get("max_regenerations", 2):
            return "regenerate"
        elif state.get("should_regenerate"):
            return "end"
        else:
            return "continue"

    def _should_continue_after_development(self, state: BMADWorkflowState) -> str:
        """Development 이후 진행 여부 결정"""
        if state.get("should_regenerate") and state.get("regeneration_count", 0) < state.get("max_regenerations", 2):
            return "regenerate"
        else:
            return "end"


# ========== Parallel Execution Support ==========

class ParallelNode:
    """
    병렬 실행을 위한 노드 래퍼

    여러 작업을 병렬로 실행하고 결과를 수집합니다.
    """

    def __init__(self, name: str, functions: List[Callable]):
        self.name = name
        self.functions = functions

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """병렬 실행 (간단한 버전 - 실제로는 순차 실행)"""
        logger.info(f"Executing parallel node: {self.name}")

        results = []
        for func in self.functions:
            try:
                result = func(state)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in parallel execution: {e}")
                results.append({"error": str(e)})

        # 결과 병합
        merged_state = {**state}
        for result in results:
            merged_state.update(result)

        return merged_state
