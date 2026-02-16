"""
Agent Designer Agent

Expert agent responsible for Phase 3 (Design):
- Designs CrewAI agents and tasks
- Maps features to agent roles
- Defines task dependencies and workflows
- Selects appropriate tools for each agent
"""

from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, BaseExpertAgent, ValidationIssue
from caas_framework.agents.executors import GoldenDataEnhancer, RefinementExecutor
from caas_framework.agents.registry import register_agent
from caas_framework.agents.utils import AgentOutputParser
from caas_framework.config.settings import LLMConstants
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import ObjectAccessor
from caas_framework.utils.logger import get_logger


@register_agent(phase=AgentPhase.DESIGN)
class AgentDesignerAgent(BaseExpertAgent):
    """
    Agent Designer Agent

    Specializes in designing CrewAI multi-agent systems
    that implement the architecture and fulfill requirements.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
    ):
        super().__init__(llm_plugin, golden_data, AgentPhase.DESIGN)

    @property
    def agent_name(self) -> str:
        return "AgentDesigner"

    @property
    def agent_role(self) -> str:
        return "Expert Multi-Agent System Designer"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "CrewAI agent design",
            "Task decomposition",
            "Agent role definition",
            "Workflow orchestration",
            "Tool selection and integration",
            "Agent collaboration patterns",
            "Task dependency management",
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
    ) -> Dict[str, Any]:
        """
        Design agents and tasks.

        Returns:
            Dict with:
            - agents: List[AgentSpecModel]
            - tasks: List[TaskSpecModel]
            - workflow_type: str
            - agent_collaboration_pattern: str
        """
        context_summary = self._build_context_summary(context, previous_outputs)

        # Get previous phase outputs
        req_analysis = (
            previous_outputs.get(AgentPhase.DISCOVERY) if previous_outputs else None
        )
        architecture = (
            previous_outputs.get(AgentPhase.ARCHITECTURE) if previous_outputs else None
        )

        prompt = self._build_design_prompt(
            requirement, req_analysis, architecture, context_summary
        )

        # Call LLM with retry logic from base class
        response = await self._execute_with_retry(
            lambda: self.llm.ainvoke(
                messages=[{"role": "user", "content": prompt}],
                response_format=LLMConstants.RESPONSE_FORMAT_JSON,
                temperature=LLMConstants.TEMPERATURE_BALANCED,
            ),
            operation="agent/task design",
        )

        # Debug logging
        logger = get_logger()
        raw_response = str(response)[:500]
        logger.info(f"[{self.agent_name}] Raw LLM response (first 500 chars): {raw_response}")

        # Parse response using helper
        design = await AgentOutputParser.parse_llm_json(
            response,
            expected_fields=[
                "agents",
                "tasks",
                "workflow_type",
                "agent_collaboration_pattern",
            ],
            fallback_factory=self._create_fallback_design,
            agent_name=self.agent_name,
        )

        logger.info(
            f"Parsed design: agents={len(design.get('agents', []))}, tasks={len(design.get('tasks', []))}, keys={list(design.keys())}"
        )

        # Convert to Pydantic models
        # Safety checks: ensure agents and tasks are lists
        agents_data = design.get("agents")
        if agents_data is None or not isinstance(agents_data, list):
            logger.warning(f"Invalid agents_data: {type(agents_data)}, using fallback")
            agents_data = self._create_fallback_design()["agents"]

        tasks_data = design.get("tasks")
        if tasks_data is None or not isinstance(tasks_data, list):
            logger.warning(f"Invalid tasks_data: {type(tasks_data)}, using fallback")
            tasks_data = self._create_fallback_design()["tasks"]

        # Normalize IDs to snake_case before creating models
        from caas_framework.utils import TextNormalizer

        TextNormalizer.normalize_agent_task_ids(agents_data, tasks_data)

        agents = [AgentSpecModel(**agent) for agent in agents_data]
        tasks = [TaskSpecModel(**task) for task in tasks_data]

        result = {
            "agents": agents,
            "tasks": tasks,
            "workflow_type": design.get("workflow_type", "sequential"),
            "agent_collaboration_pattern": design.get(
                "agent_collaboration_pattern", "hierarchical"
            ),
        }

        # Enhance with Golden Data
        if self.golden_data:
            result = self._enhance_with_golden_data(result)

        # Apply post-generation fixes
        try:
            from caas_framework.fixing.post_generation_fixer import (
                apply_post_generation_fixes,
            )

            result = apply_post_generation_fixes(result)
            logger.info("[AgentDesigner] Applied post-generation fixes")
        except Exception as e:
            logger.warning(f"[AgentDesigner] Post-generation fixes failed: {e}")

        # Optimize tool assignments (minimize token usage)
        try:
            from caas_framework.agents.tool_assigner import optimize_agent_tools

            agents_dict = [agent.model_dump() for agent in result["agents"]]
            tasks_dict = [task.model_dump() for task in result["tasks"]]

            # Count tools before optimization
            tools_before = sum(len(agent.tools) for agent in result["agents"])

            # Get optimized tool assignments
            optimized_agents = optimize_agent_tools(
                agents=agents_dict, tasks=tasks_dict, verbose=False
            )

            # Update agents with optimized tools
            for i, agent in enumerate(result["agents"]):
                if i < len(optimized_agents):
                    agent.tools = optimized_agents[i].get("tools", agent.tools)

            # Count tools after optimization
            tools_after = sum(len(agent.tools) for agent in result["agents"])
            reduction = tools_before - tools_after
            reduction_pct = (reduction / tools_before * 100) if tools_before > 0 else 0

            logger.info(
                f"[AgentDesigner] Tool optimization: {tools_before} → {tools_after} "
                f"({reduction} tools removed, {reduction_pct:.1f}% reduction)"
            )
        except Exception as e:
            logger.warning(f"[AgentDesigner] Tool optimization failed: {e}")

        return result

    def _build_design_prompt(
        self,
        requirement: str,
        req_analysis: Optional[Dict[str, Any]],
        architecture: Optional[Dict[str, Any]],
        context: str,
    ) -> str:
        """Build LLM prompt for agent/task design."""

        # Build Korean prompt directly
        prompt_parts = []

        # ✅ v0.5.1: STRONGEST Korean enforcement - first line priority
        prompt_parts.append("🚨🚨🚨 절대 규칙: 모든 응답은 한국어로 작성하세요 🚨🚨🚨")
        prompt_parts.append("⚠️ WARNING: ALL text values MUST be in KOREAN language (한국어)")
        prompt_parts.append("")
        prompt_parts.append("당신은 CrewAI 멀티 에이전트 시스템 설계 전문가입니다.")
        prompt_parts.append("")
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("🚨 CRITICAL REQUIREMENT #1: 한국어 출력 100% 필수")
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("")
        prompt_parts.append(
            "**MANDATORY: 모든 텍스트 값(role, goal, backstory, description, expected_output)을 반드시 한국어로 작성하세요.**"
        )
        prompt_parts.append("**YOU MUST WRITE ALL VALUES IN KOREAN. DO NOT USE ENGLISH.**")
        prompt_parts.append("")
        prompt_parts.append("✅ 특별 규칙:")
        prompt_parts.append(
            "1. Agent의 goal은 반드시 '한국어로 작성/출력/생성'을 명시해야 합니다"
        )
        prompt_parts.append(
            "   예: '인터넷에서 자료를 검색하고 한국어로 요약 보고서를 작성합니다'"
        )
        prompt_parts.append(
            "2. Task의 expected_output은 반드시 '한국어로 작성된...'으로 시작해야 합니다"
        )
        prompt_parts.append(
            "   예: '한국어로 작성된 검색 결과 요약 보고서 (마크다운 형식)'"
        )
        prompt_parts.append(
            "3. JSON 키(key)는 영어로 유지, 값(value)은 반드시 한국어로"
        )
        prompt_parts.append("")
        prompt_parts.append("❌ 잘못된 예시:")
        prompt_parts.append("  goal: 'Search the internet and create a summary report' ❌")
        prompt_parts.append("  expected_output: 'Summary report in markdown format' ❌")
        prompt_parts.append("")
        prompt_parts.append("✅ 올바른 예시:")
        prompt_parts.append("  goal: '인터넷에서 자료를 검색하고 한국어로 요약 보고서를 작성합니다' ✅")
        prompt_parts.append("  expected_output: '한국어로 작성된 요약 보고서 (마크다운 형식)' ✅")
        prompt_parts.append("")
        prompt_parts.append("## 요구사항")
        prompt_parts.append(f"{requirement}")
        prompt_parts.append("")

        # Add golden data if available
        if self.golden_data:
            if self.golden_data.features:
                prompt_parts.append("## Golden Data 기능")
                for feat in self.golden_data.features[:5]:  # Limit to 5
                    prompt_parts.append(f"- {feat.name}: {feat.description}")
                prompt_parts.append("")

            if self.golden_data.workflow_type:
                prompt_parts.append(
                    f"## 워크플로우 타입: {self.golden_data.workflow_type}"
                )
                prompt_parts.append("")

        # Add previous outputs
        if req_analysis:
            prompt_parts.append("## 요구사항 분석 결과")
            prompt_parts.append(str(req_analysis)[:500])  # Limit length
            prompt_parts.append("")

        if architecture:
            prompt_parts.append("## 아키텍처 설계")
            prompt_parts.append(str(architecture)[:500])  # Limit length
            prompt_parts.append("")

        # Add context if provided
        if context:
            prompt_parts.append("## 추가 컨텍스트")
            prompt_parts.append(context)
            prompt_parts.append("")

        # Add available tools information
        prompt_parts.append("## 사용 가능한 도구 (CrewAI Tools)")
        prompt_parts.append("에이전트에 할당할 수 있는 도구 목록:")
        prompt_parts.append("")
        prompt_parts.append("**파일 도구:**")
        prompt_parts.append("- file_read: 파일 읽기")
        prompt_parts.append("- file_write: 파일 쓰기 (code_interpreter 사용)")
        prompt_parts.append("- directory_read: 디렉토리 구조 읽기")
        prompt_parts.append("")
        prompt_parts.append("**웹 검색 도구:**")
        prompt_parts.append("- web_search: 인터넷 검색 (Serper API)")
        prompt_parts.append("- scrape_website: 웹사이트 크롤링")
        prompt_parts.append("- brave_search: Brave 검색 엔진")
        prompt_parts.append("")
        prompt_parts.append("**코드 실행 도구:**")
        prompt_parts.append("- code_interpreter: Python 코드 실행 및 데이터 분석")
        prompt_parts.append("- calculator: 수학 계산 (커스텀)")
        prompt_parts.append("")
        prompt_parts.append("**문서 검색 도구:**")
        prompt_parts.append("- pdf_search: PDF 문서 검색")
        prompt_parts.append("- csv_search: CSV 데이터 검색")
        prompt_parts.append("- json_search: JSON 파일 검색")
        prompt_parts.append("")
        prompt_parts.append("**기타:**")
        prompt_parts.append("- vision: 이미지 분석")
        prompt_parts.append("- youtube_search: 유튜브 동영상 검색")
        prompt_parts.append("")
        prompt_parts.append(
            "**중요:** 에이전트의 역할과 목표에 맞는 도구를 선택하세요."
        )
        prompt_parts.append('예: 웹 검색 에이전트 → ["web_search", "scrape_website"]')
        prompt_parts.append(
            '예: 데이터 분석 에이전트 → ["code_interpreter", "csv_search"]'
        )
        prompt_parts.append(
            '예: 파일 관리 에이전트 → ["file_read", "file_write", "directory_read"]'
        )
        prompt_parts.append("")

        # Add output format
        prompt_parts.append("")
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("🚨 다시 강조: 아래 JSON의 모든 텍스트 값은 한국어로 작성 🚨")
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("")
        prompt_parts.append("## 출력 형식")
        prompt_parts.append(
            "다음 JSON 형식으로 멀티 에이전트 시스템을 설계하세요:"
        )
        prompt_parts.append("⚠️ CRITICAL: role, goal, backstory, description, expected_output 값은 모두 한국어로 작성하세요")
        prompt_parts.append("")
        prompt_parts.append(
            """{
    "agents": [
        {
            "id": "고유_에이전트_id",
            "role": "역할 이름",
            "goal": "이 에이전트의 구체적인 목표",
            "backstory": "에이전트의 배경과 전문성",
            "tools": ["tool1", "tool2"],
            "allow_delegation": true,
            "verbose": true
        }
    ],
    "tasks": [
        {
            "id": "고유_작업_id",
            "description": "상세한 작업 설명 (사용자 입력 필요 시: '키워드 {keyword}를 사용하여...')",
            "expected_output": "기대되는 출력 (예: '한국어로 작성된 {keyword}에 대한 요약 보고서')",
            "agent": "이_작업을_수행할_에이전트_id",
            "context": ["작업_id_1", "작업_id_2"],
            "async_execution": false,
            "human_input": false
        }
    ],
    "workflow_type": "sequential|hierarchical|parallel",
    "agent_collaboration_pattern": "에이전트들이 협업하는 방식에 대한 설명"
}"""
        )
        prompt_parts.append("")

        # ✅ v0.5.1: Add critical guideline for user input systems
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("🚨 CRITICAL: 사용자 입력이 필요한 시스템 설계 규칙")
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("")
        prompt_parts.append("**요구사항에 '입력받', '키워드', 'input', 'keyword' 등이 포함된 경우:**")
        prompt_parts.append("")
        prompt_parts.append("1. Task description에 반드시 '{input_name}' 플레이스홀더를 포함하세요!")
        prompt_parts.append("   - 예: \"키워드 '{keyword}'를 사용하여 인터넷에서 자료를 검색합니다\"")
        prompt_parts.append("   - 예: \"입력받은 텍스트 '{text}'를 분석하고 요약합니다\"")
        prompt_parts.append("")
        prompt_parts.append("2. 입력 변수명 규칙:")
        prompt_parts.append("   - 검색어/키워드 → {keyword}")
        prompt_parts.append("   - 텍스트 → {text}")
        prompt_parts.append("   - 파일 → {file}")
        prompt_parts.append("   - URL → {url}")
        prompt_parts.append("")
        prompt_parts.append("3. 첫 번째 Task부터 플레이스홀더를 사용하세요:")
        prompt_parts.append("   - ❌ \"사용자가 입력한 키워드를 수집합니다\"")
        prompt_parts.append("   - ✅ \"사용자가 입력한 키워드 '{keyword}'의 유효성을 검증합니다\"")
        prompt_parts.append("")
        prompt_parts.append("4. 모든 관련 Task에 플레이스홀더 전파:")
        prompt_parts.append("   - ✅ \"검증된 키워드 '{keyword}'를 사용하여 인터넷 검색을 수행합니다\"")
        prompt_parts.append("   - ✅ \"검색된 자료를 바탕으로 키워드 '{keyword}'에 대한 한국어 보고서를 작성합니다\"")
        prompt_parts.append("")
        prompt_parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        prompt_parts.append("")

        # Add guidelines
        prompt_parts.append("## 가이드라인")
        prompt_parts.append("- 각 기능은 하나 이상의 작업에 매핑되어야 합니다")
        prompt_parts.append("- 에이전트는 명확하고 구별되는 역할을 가져야 합니다")
        prompt_parts.append("- 작업은 적절한 의존성(context)을 가져야 합니다")
        prompt_parts.append("- 계층적 워크플로우의 경우 관리자 에이전트를 포함하세요")
        prompt_parts.append(
            "- **각 에이전트에 반드시 적절한 도구를 선택하세요** (빈 리스트 금지)"
        )
        prompt_parts.append("- 도구는 에이전트의 역할과 목표에 정확히 맞아야 합니다")
        prompt_parts.append(
            "- 웹 검색이 필요하면 web_search 또는 scrape_website 도구를 추가하세요"
        )
        prompt_parts.append(
            "- 데이터 분석이 필요하면 code_interpreter 도구를 추가하세요"
        )
        prompt_parts.append("- 작업이 모든 기능 요구사항을 다루는지 확인하세요")
        prompt_parts.append("")
        prompt_parts.append("**중요: 사용자 입력 처리 방법**")
        prompt_parts.append(
            "- ❌ human_input을 사용자 입력 수집 용도로 사용하지 마세요"
        )
        prompt_parts.append(
            "- ✅ human_input=true는 태스크 완료 후 '피드백'을 받을 때만 사용"
        )
        prompt_parts.append(
            "- ✅ 사용자 입력이 필요하면 태스크 설명에서 '입력'을 빼고 '처리/분석/검증'만 명시"
        )
        prompt_parts.append(
            "- 예: '키워드를 입력받고 검증' → '키워드의 유효성을 검증' (입력은 crew.kickoff로 전달)"
        )
        prompt_parts.append("")
        prompt_parts.append("## 최종 체크리스트 - 제출 전 필수 확인")
        prompt_parts.append("")
        prompt_parts.append("❌ 절대 금지 사항:")
        prompt_parts.append("- ❌ role, goal, backstory를 영어로 작성하는 것")
        prompt_parts.append("- ❌ description, expected_output을 영어로 작성하는 것")
        prompt_parts.append("- ❌ 'To...', 'A comprehensive...', 'Search...' 같은 영어 문장")
        prompt_parts.append("- ❌ 사용자 입력이 필요한데 Task description에 플레이스홀더가 없는 것")
        prompt_parts.append("")
        prompt_parts.append("✅ 필수 확인 사항:")
        prompt_parts.append(
            "- 🔴 모든 role, goal, backstory, description, expected_output 값이 한국어인가?"
        )
        prompt_parts.append(
            "- 🔴 Agent의 goal에 '한국어로 작성/출력/생성'이 명시되어 있는가?"
        )
        prompt_parts.append(
            "- 🔴 Task의 expected_output이 '한국어로 작성된...'으로 시작하는가?"
        )
        prompt_parts.append(
            "- 🔴 사용자 입력이 필요하면 Task description에 '{keyword}' 같은 플레이스홀더가 있는가?"
        )
        prompt_parts.append("- ✅ JSON 형식이 올바른가?")
        prompt_parts.append("")
        prompt_parts.append("🚨 마지막 경고:")
        prompt_parts.append("  1. 한국어가 아닌 값이 하나라도 있으면 잘못된 응답입니다!")
        prompt_parts.append("  2. 사용자 입력이 필요한데 플레이스홀더가 없으면 잘못된 응답입니다!")
        prompt_parts.append("✅ 오직 유효한 JSON만 반환하세요 (설명 없이)")

        return "\n".join(prompt_parts)

    def _create_fallback_design(self) -> Dict[str, Any]:
        """Create design based on Golden Data features when LLM fails."""
        # ✅ Week 2-1: Use base helper for consistent fallback logging
        self._log_fallback_usage(
            reason="LLM generation failed - using golden data or basic design",
            fallback_type="agent_task_design_fallback"
        )

        # Try to create meaningful agents and tasks from Golden Data
        if self.golden_data and self.golden_data.features:
            return self._generate_design_from_features()

        # Last resort: basic fallback (Korean)
        agents = [
            {
                "id": "manager",
                "role": "매니저",
                "goal": "프로젝트 실행을 조율합니다",
                "backstory": "경험 많은 프로젝트 관리자로서 여러 팀원들의 작업을 효과적으로 조율하고 관리합니다",
                "tools": ["file_read", "directory_read"],
                "allow_delegation": True,
                "verbose": True,
            },
            {
                "id": "executor",
                "role": "실행자",
                "goal": "할당된 작업을 수행합니다",
                "backstory": "숙련된 실행자로서 주어진 작업을 정확하고 효율적으로 완수합니다",
                "tools": ["code_interpreter", "file_read", "file_write"],
                "allow_delegation": False,
                "verbose": True,
            },
        ]

        tasks = [
            {
                "id": "task_1",
                "description": "주요 작업을 실행합니다",
                "expected_output": "작업이 완료되었습니다",
                "agent": "executor",
                "context": [],
                "async_execution": False,
                "human_input": False,
            }
        ]

        return {
            "agents": agents,
            "tasks": tasks,
            "workflow_type": "sequential",
            "agent_collaboration_pattern": "계층적 협업 패턴",
        }

    def _generate_design_from_features(self) -> Dict[str, Any]:
        """Generate agents and tasks directly from Golden Data features."""
        features = self.golden_data.features if self.golden_data.features else []

        # Determine agent types based on project type
        has_ui = bool(
            self.golden_data.ui_components if self.golden_data.ui_components else []
        )
        has_api = (
            "api" in self.golden_data.project_name.lower()
            or "rest" in self.golden_data.project_name.lower()
        )

        agents = []
        tasks = []

        # Create manager agent (Korean)
        agents.append(
            {
                "id": "project_manager",
                "role": "프로젝트 매니저",
                "goal": f"{self.golden_data.project_name}의 개발을 조율합니다",
                "backstory": "애자일 개발과 팀 조율에 전문성을 갖춘 경험 많은 프로젝트 관리자입니다",
                "tools": ["file_read", "directory_read"],
                "allow_delegation": True,
                "verbose": True,
            }
        )

        # Create developer agent (Korean)
        agents.append(
            {
                "id": "senior_developer",
                "role": "시니어 개발자",
                "goal": f"{self.golden_data.project_name}의 핵심 기능을 구현합니다",
                "backstory": "풀스택 개발 분야에서 10년 이상의 경험을 가진 시니어 개발자입니다",
                "tools": ["code_interpreter", "file_read", "file_write", "web_search"],
                "allow_delegation": False,
                "verbose": True,
            }
        )

        # Create UI developer if UI components exist (Korean)
        if has_ui:
            agents.append(
                {
                    "id": "ui_developer",
                    "role": "UI 개발자",
                    "goal": "직관적이고 반응형인 사용자 인터페이스를 만듭니다",
                    "backstory": "최신 UI 프레임워크에 전문성을 갖춘 프론트엔드 전문가입니다",
                    "tools": ["file_read", "file_write", "web_search"],
                    "allow_delegation": False,
                    "verbose": True,
                }
            )

        # Create API developer if it's an API project (Korean)
        if has_api:
            agents.append(
                {
                    "id": "api_developer",
                    "role": "API 개발자",
                    "goal": "RESTful API 엔드포인트를 설계하고 구현합니다",
                    "backstory": "API 설계 및 개발에 전문성을 갖춘 백엔드 전문가입니다",
                    "tools": ["code_interpreter", "web_search", "file_read"],
                    "allow_delegation": False,
                    "verbose": True,
                }
            )

        # Create QA agent (Korean)
        agents.append(
            {
                "id": "qa_engineer",
                "role": "QA 엔지니어",
                "goal": "코드 품질과 테스트 커버리지를 보장합니다",
                "backstory": "테스팅과 검증에 전문성을 갖춘 품질 보증 전문가입니다",
                "tools": ["code_interpreter", "file_read"],
                "allow_delegation": False,
                "verbose": True,
            }
        )

        # Create tasks from features
        for i, feature in enumerate(features):
            task_id = f"task_{feature.id.lower()}"

            # Determine which agent should handle this task
            if has_ui and "ui" in feature.name.lower():
                agent_id = "ui_developer"
            elif has_api and (
                "api" in feature.name.lower() or "endpoint" in feature.name.lower()
            ):
                agent_id = "api_developer"
            else:
                agent_id = "senior_developer"

            # Create implementation task (Korean)
            tasks.append(
                {
                    "id": task_id,
                    "description": f"{feature.name} 구현: {feature.description}",
                    "expected_output": f"테스트를 포함한 완전히 기능하는 {feature.name}",
                    "agent": agent_id,
                    "context": [],
                    "async_execution": False,
                    "human_input": False,
                }
            )

        # Add testing task (Korean)
        tasks.append(
            {
                "id": "task_testing",
                "description": f"모든 기능에 대한 포괄적인 테스트 작성: {', '.join(f.name for f in features[:3])}",
                "expected_output": "높은 커버리지를 갖춘 완전한 테스트 스위트",
                "agent": "qa_engineer",
                "context": [f"task_{f.id.lower()}" for f in features],
                "async_execution": False,
                "human_input": False,
            }
        )

        # Add documentation task (Korean)
        tasks.append(
            {
                "id": "task_documentation",
                "description": f"{self.golden_data.project_name}에 대한 문서 작성",
                "expected_output": "완전한 README 및 API 문서",
                "agent": "senior_developer",
                "context": ["task_testing"],
                "async_execution": False,
                "human_input": False,
            }
        )

        return {
            "agents": agents,
            "tasks": tasks,
            "workflow_type": "sequential",
            "agent_collaboration_pattern": "계층적 협업 패턴",
        }

    def _enhance_with_golden_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance design with Golden Data traceability."""
        enhancer = GoldenDataEnhancer(self.golden_data)
        return enhancer.enhance_with_feature_task_mapping(
            output=result,
            agents_key="agents",
            tasks_key="tasks",
            alignment_key="golden_data_coverage",
        )

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine agent/task design based on validation feedback.

        Uses RefinementExecutor for standardized refinement workflow.
        """
        executor = RefinementExecutor.create_for_agent(
            agent=self,
            agent_role="CrewAI Multi-Agent System Designer",
            output_type="agent/task design",
        )

        refined_output = await executor.refine_output(
            output=output,
            issues=issues,
            iteration=iteration,
            guidelines=[
                "Fix ontology violations (role/task type mismatches)",
                "Ensure all tasks have assigned agents",
                "Fix dependency cycles in task context",
                "Verify tool selections are valid",
                "Ensure Golden Data feature coverage",
            ],
        )

        # Convert agents/tasks back to Pydantic models
        try:
            from caas_framework.utils import TextNormalizer

            agents_dict = ObjectAccessor.to_dict_list(refined_output.get("agents", []))
            tasks_dict = ObjectAccessor.to_dict_list(refined_output.get("tasks", []))

            TextNormalizer.normalize_agent_task_ids(agents_dict, tasks_dict)

            agents = [AgentSpecModel(**agent) for agent in agents_dict]
            tasks = [TaskSpecModel(**task) for task in tasks_dict]

            result = {
                "agents": agents,
                "tasks": tasks,
                "workflow_type": refined_output.get(
                    "workflow_type", output.get("workflow_type", "sequential")
                ),
                "agent_collaboration_pattern": refined_output.get(
                    "agent_collaboration_pattern",
                    output.get("agent_collaboration_pattern", "hierarchical"),
                ),
            }

            # Preserve metadata
            for key in output:
                if key not in result and key not in ["agents", "tasks"]:
                    result[key] = output[key]

            return result

        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"[{self.agent_name}] Refinement failed: {e}, returning original output")
            return output
