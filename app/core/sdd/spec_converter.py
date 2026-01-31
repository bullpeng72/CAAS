"""
Spec Converter

RequirementAnalysis를 MultiProjectSpec으로 변환합니다.
"""

import re
from typing import List, Optional, Dict, Any
from app.llm.chains import (
    RequirementAnalysis,
    AgentRequirement,
    TaskRequirement,
    UIPageRequirement,
    UIComponentRequirement,
    BackendAPIRequirement,
)
from app.core.sdd.engine import (
    ProjectSpec,
    CrewAISpec,
    AgentSpecModel,
    TaskSpecModel,
    CrewConfigSpec,
)
from app.core.sdd.multi_spec import (
    MultiProjectSpec,
    ProjectTemplate,
    FrontendSpec,
    FrontendFramework,
    BackendSpec,
    BackendFramework,
    DatabaseSpec,
    DatabaseType,
    UIPage,
    UIComponent,
    UIComponentType,
    APIEndpoint,
    HTTPMethod,
    DataModel,
    DataField,
    FieldType,
)
from app.utils.logger import get_logger
from app.models.domain_types import DomainType, DomainClassification
from app.knowledge.agent_patterns import get_agent_pattern

logger = get_logger("sdd.spec_converter")


def clean_name(text: str) -> str:
    """
    텍스트를 유효한 snake_case 이름으로 변환

    Args:
        text: 원본 텍스트

    Returns:
        snake_case 문자열
    """
    # 소문자로 변환하고 공백을 언더스코어로
    name = text.lower().strip()
    name = re.sub(r'\s+', '_', name)

    # 특수문자 제거 (알파벳, 숫자, 언더스코어만 유지)
    name = re.sub(r'[^a-z0-9_]', '', name)

    # 연속된 언더스코어 제거
    name = re.sub(r'_+', '_', name)

    # 앞뒤 언더스코어 제거
    name = name.strip('_')

    # 빈 문자열이거나 숫자로 시작하면 prefix 추가
    if not name:
        name = "project"
    elif name[0].isdigit():
        name = f"project_{name}"

    return name


def clean_id(text: str, prefix: str = "item") -> str:
    """
    텍스트를 유효한 ID로 변환

    Args:
        text: 원본 텍스트
        prefix: 기본 prefix

    Returns:
        유효한 ID 문자열
    """
    id_str = clean_name(text)

    if not id_str:
        id_str = prefix

    return id_str


def map_ui_component_type(component_type_str: str) -> UIComponentType:
    """
    문자열 컴포넌트 타입을 UIComponentType enum으로 매핑

    Args:
        component_type_str: 컴포넌트 타입 문자열

    Returns:
        UIComponentType enum 값
    """
    # 문자열 정규화
    normalized = component_type_str.upper().replace('-', '_').replace(' ', '_')

    # 직접 매칭 시도
    try:
        return UIComponentType[normalized]
    except KeyError:
        pass

    # 부분 매칭
    mapping = {
        'TEXT': UIComponentType.TEXT_INPUT,
        'INPUT': UIComponentType.TEXT_INPUT,
        'AREA': UIComponentType.TEXT_AREA,
        'BUTTON': UIComponentType.BUTTON,
        'BTN': UIComponentType.BUTTON,
        'SELECT': UIComponentType.SELECT,
        'DROPDOWN': UIComponentType.SELECT,
        'TABLE': UIComponentType.TABLE,
        'CHART': UIComponentType.CHART,
        'GRAPH': UIComponentType.CHART,
        'FILE': UIComponentType.FILE_UPLOAD,
        'UPLOAD': UIComponentType.FILE_UPLOAD,
        'MARKDOWN': UIComponentType.MARKDOWN,
        'MD': UIComponentType.MARKDOWN,
    }

    for key, value in mapping.items():
        if key in normalized:
            return value

    # 기본값
    return UIComponentType.TEXT_INPUT


def convert_ui_component(comp: UIComponentRequirement) -> UIComponent:
    """
    UIComponentRequirement를 UIComponent로 변환

    Args:
        comp: UIComponentRequirement 객체

    Returns:
        UIComponent 객체
    """
    component_type = map_ui_component_type(comp.component_type)
    component_id = clean_id(comp.label, "component")

    return UIComponent(
        component_id=component_id,
        component_type=component_type,
        label=comp.label,
        description=comp.description,
        props={}
    )


def convert_ui_page(page: UIPageRequirement) -> UIPage:
    """
    UIPageRequirement를 UIPage로 변환

    Args:
        page: UIPageRequirement 객체

    Returns:
        UIPage 객체
    """
    components = [convert_ui_component(comp) for comp in page.components]

    return UIPage(
        name=clean_name(page.name),
        title=page.title,
        description=page.description,
        components=components,
        layout="single_column"
    )


def convert_backend_api(api: BackendAPIRequirement) -> APIEndpoint:
    """
    BackendAPIRequirement를 APIEndpoint로 변환

    Args:
        api: BackendAPIRequirement 객체

    Returns:
        APIEndpoint 객체
    """
    # HTTPMethod enum으로 변환
    try:
        method = HTTPMethod[api.method.upper()]
    except (KeyError, AttributeError):
        method = HTTPMethod.POST  # 기본값

    return APIEndpoint(
        path=api.path,
        method=method,
        description=api.description,
        summary=api.description,
        tags=["agent"]
    )


def generate_execution_agents_from_domain(
    domain_classification: Dict[str, Any],
    tools: List[str] = None
) -> List[AgentRequirement]:
    """
    Domain Classification 결과로부터 Execution Agents를 생성합니다.

    Build agents (frontend_developer, backend_developer) 대신
    실제로 시스템이 실행할 때 필요한 domain-specific agents를 생성합니다.

    Args:
        domain_classification: Domain classification 결과 dict
        tools: 도구 목록 (선택사항)

    Returns:
        List[AgentRequirement]: Execution agent 목록
    """
    try:
        domain_type = DomainType(domain_classification.get('domain_type'))
        pattern = get_agent_pattern(domain_type)

        logger.info(f"🤖 Generating execution agents for domain: {domain_type}")

        execution_agents = []
        for agent_info in pattern.execution_agents:
            agent_req = AgentRequirement(
                role=agent_info['role'],
                goal=agent_info['goal'],
                skills=agent_info.get('skills', []),
                priority=3  # 기본 우선순위
            )
            execution_agents.append(agent_req)
            logger.info(f"   ✅ Created execution agent: {agent_info['role']}")

        logger.info(f"   Total: {len(execution_agents)} execution agents created")
        return execution_agents

    except Exception as e:
        logger.warning(f"⚠️ Failed to generate execution agents: {e}")
        logger.warning(f"   Falling back to build agents")
        return []


def generate_execution_tasks_from_domain(
    domain_classification: Dict[str, Any],
    execution_agents: List[AgentRequirement]
) -> List[TaskRequirement]:
    """
    Domain Classification과 Execution Agents로부터 적절한 Tasks를 생성합니다.

    Args:
        domain_classification: Domain classification 결과 dict
        execution_agents: Execution agent 목록

    Returns:
        List[TaskRequirement]: Execution task 목록
    """
    try:
        domain_type = DomainType(domain_classification.get('domain_type'))
        core_operations = domain_classification.get('core_operations', [])

        logger.info(f"⚙️ Generating execution tasks for domain: {domain_type}")

        execution_tasks = []

        # 각 agent에 대해 core operations 기반 태스크 생성
        for i, agent in enumerate(execution_agents):
            # 첫 번째 agent는 주요 작업 수행
            if i == 0:
                task = TaskRequirement(
                    name=f"execute_{domain_type.value}_operations",
                    description=f"Execute main {domain_type.value} operations: {', '.join(core_operations[:3])}",
                    assigned_agent=agent.role,
                    dependencies=[],
                    output_type="structured_data"
                )
            else:
                # 나머지 agent는 보조 작업
                task = TaskRequirement(
                    name=f"{agent.role}_task",
                    description=f"{agent.goal}",
                    assigned_agent=agent.role,
                    dependencies=[execution_tasks[0].name] if execution_tasks else [],
                    output_type="text"
                )

            execution_tasks.append(task)
            logger.info(f"   ✅ Created execution task: {task.name} → {agent.role}")

        logger.info(f"   Total: {len(execution_tasks)} execution tasks created")
        return execution_tasks

    except Exception as e:
        logger.warning(f"⚠️ Failed to generate execution tasks: {e}")
        return []


def convert_agent_to_spec(
    agent: AgentRequirement,
    tools: List[str] = None
) -> AgentSpecModel:
    """
    AgentRequirement를 AgentSpecModel로 변환

    Args:
        agent: AgentRequirement 객체
        tools: 도구 목록

    Returns:
        AgentSpecModel 객체
    """
    agent_id = clean_id(agent.role, "agent")

    # 간단한 backstory 생성
    backstory = f"""You are a specialized {agent.role} with the following skills: {', '.join(agent.skills)}.
Your primary goal is to {agent.goal}.
You work efficiently and deliver high-quality results."""

    return AgentSpecModel(
        id=agent_id,
        role=agent.role,
        goal=agent.goal,
        backstory=backstory,
        tools=tools or [],
        verbose=True,
        allow_delegation=False,
        memory=True
    )


def convert_task_to_spec(
    task: TaskRequirement,
    agent_map: Dict[str, str]
) -> TaskSpecModel:
    """
    TaskRequirement를 TaskSpecModel로 변환

    Args:
        task: TaskRequirement 객체
        agent_map: role/id → agent_id 매핑

    Returns:
        TaskSpecModel 객체
    """
    task_id = clean_id(task.name, "task")

    # Agent ID 찾기 (다양한 방법으로 시도)
    agent_id = None

    # 1. 직접 매핑 (가장 일반적)
    if task.assigned_agent in agent_map:
        agent_id = agent_map[task.assigned_agent]
    # 2. 소문자 매핑 시도
    elif task.assigned_agent.lower() in agent_map:
        agent_id = agent_map[task.assigned_agent.lower()]
    # 3. clean_id 후 매핑 시도
    elif clean_id(task.assigned_agent, "") in agent_map:
        agent_id = agent_map[clean_id(task.assigned_agent, "")]
    # 4. 부분 문자열 매칭 (최후의 수단)
    else:
        for key, value in agent_map.items():
            if task.assigned_agent.lower() in key.lower() or key.lower() in task.assigned_agent.lower():
                agent_id = value
                logger.info(f"Task '{task_id}': Fuzzy matched agent '{task.assigned_agent}' → '{agent_id}' via '{key}'")
                break

    # 5. 폴백: agent_map에서 첫 번째 agent 사용
    if not agent_id:
        # agent_map에서 ID → ID 매핑이 아닌 첫 번째 값 찾기
        for key, value in agent_map.items():
            if key != value:  # Role → ID 매핑인 경우
                agent_id = value
                break
        if not agent_id and agent_map:
            agent_id = list(agent_map.values())[0]
        else:
            agent_id = "agent_1"

        logger.warning(f"Task '{task_id}': Could not find agent for '{task.assigned_agent}', using fallback '{agent_id}'")

    logger.info(f"Task '{task_id}' assigned to agent '{agent_id}'")

    return TaskSpecModel(
        id=task_id,
        description=task.description,
        expected_output=task.output_type,
        agent=agent_id,
        dependencies=[clean_id(dep, "task") for dep in task.dependencies],
        async_execution=False,
        human_input=False
    )


def convert_analysis_to_multi_spec(
    analysis: RequirementAnalysis,
    project_name: Optional[str] = None
) -> MultiProjectSpec:
    """
    RequirementAnalysis를 MultiProjectSpec으로 변환

    Args:
        analysis: RequirementAnalysis 객체
        project_name: 프로젝트 이름 (선택사항)

    Returns:
        MultiProjectSpec 객체
    """
    logger.info(f"Converting RequirementAnalysis to MultiProjectSpec")
    logger.info(f"  Template: {analysis.project_template}")
    logger.info(f"  Requires UI: {analysis.requires_ui}")
    logger.info(f"  Requires Backend: {analysis.requires_backend}")
    logger.info(f"  Requires Database: {analysis.requires_database}")

    # 1. ProjectSpec 생성
    if not project_name:
        project_name = clean_name(analysis.domain)
    else:
        project_name = clean_name(project_name)

    project = ProjectSpec(
        name=project_name,
        description=analysis.summary,
        domain=analysis.domain
    )

    # 2. Agent와 Task 변환
    # Domain Classification이 있으면 Execution Agents 생성
    agents_to_use = analysis.agents
    tasks_to_use = analysis.tasks

    if analysis.domain_classification:
        logger.info(f"🎯 Domain Classification detected: {analysis.domain_classification.get('domain_type')}")

        # Execution Agents 생성
        execution_agents = generate_execution_agents_from_domain(
            domain_classification=analysis.domain_classification,
            tools=analysis.suggested_tools
        )

        if execution_agents:
            logger.info(f"✅ Using {len(execution_agents)} execution agents instead of {len(analysis.agents)} build agents")
            agents_to_use = execution_agents

            # Execution Tasks 생성
            execution_tasks = generate_execution_tasks_from_domain(
                domain_classification=analysis.domain_classification,
                execution_agents=execution_agents
            )

            if execution_tasks:
                logger.info(f"✅ Using {len(execution_tasks)} execution tasks instead of {len(analysis.tasks)} build tasks")
                tasks_to_use = execution_tasks
        else:
            logger.warning("⚠️ Execution agents generation failed, using original build agents")
    else:
        logger.info("ℹ️ No domain classification found, using original agents")

    # Agent role → id 매핑 생성 (role과 id 모두 지원)
    agent_map = {}
    agent_specs = []

    for agent_req in agents_to_use:
        agent_spec = convert_agent_to_spec(agent_req, analysis.suggested_tools)
        agent_specs.append(agent_spec)

        # Role → ID 매핑 (LLM이 role로 참조하는 경우)
        agent_map[agent_req.role] = agent_spec.id

        # ID → ID 매핑 (Agent Designer가 이미 ID로 참조하는 경우)
        agent_map[agent_spec.id] = agent_spec.id

        # 소문자 role → ID 매핑 (유연한 매칭)
        agent_map[agent_req.role.lower()] = agent_spec.id

    # Task 변환
    task_specs = []
    for task_req in tasks_to_use:
        task_spec = convert_task_to_spec(task_req, agent_map)
        task_specs.append(task_spec)

    # 3. CrewAISpec 생성
    agent_spec = CrewAISpec(
        project=project,
        agents=agent_specs,
        tasks=task_specs,
        crew=CrewConfigSpec(
            process=analysis.workflow_type,
            verbose=True,
            memory=True
        )
    )

    # 4. FrontendSpec 생성 (UI 필요한 경우)
    frontend_spec = None
    if analysis.requires_ui:
        logger.info(f"  Creating FrontendSpec with {len(analysis.ui_pages)} pages")

        pages = []
        for page_req in analysis.ui_pages:
            page = convert_ui_page(page_req)
            pages.append(page)

        # 페이지가 없으면 기본 페이지 추가
        if not pages:
            pages.append(UIPage(
                name="main",
                title="Main Page",
                description="Main application page",
                components=[
                    UIComponent(
                        component_id="input_text",
                        component_type=UIComponentType.TEXT_AREA,
                        label="Input",
                        description="Enter your input here"
                    ),
                    UIComponent(
                        component_id="submit_button",
                        component_type=UIComponentType.BUTTON,
                        label="Submit"
                    )
                ]
            ))

        frontend_spec = FrontendSpec(
            framework=FrontendFramework.STREAMLIT,
            pages=pages,
            theme={},
            api_client={
                "base_url": "http://localhost:8000",
                "timeout": "30"
            }
        )

    # 5. BackendSpec 생성 (Backend 필요한 경우)
    backend_spec = None
    if analysis.requires_backend:
        logger.info(f"  Creating BackendSpec with {len(analysis.backend_apis)} endpoints")

        endpoints = []
        for api_req in analysis.backend_apis:
            endpoint = convert_backend_api(api_req)
            endpoints.append(endpoint)

        # 엔드포인트가 없으면 기본 엔드포인트 추가
        if not endpoints:
            endpoints.append(APIEndpoint(
                path="/api/run",
                method=HTTPMethod.POST,
                description="Run agent",
                summary="Execute the agent with provided input",
                tags=["agent"]
            ))

        backend_spec = BackendSpec(
            framework=BackendFramework.FASTAPI,
            api_endpoints=endpoints,
            middlewares=["cors", "logging"],
            dependencies=[],
            agent_integration={
                "import_path": "agents.crew",
                "run_function": "run_crew"
            },
            database_url="sqlite:///./app.db",
            use_async=True
        )

    # 6. DatabaseSpec 생성 (Database 필요한 경우)
    database_spec = None
    if analysis.requires_database:
        logger.info(f"  Creating DatabaseSpec with {len(analysis.database_tables)} tables")

        models = []
        for table_name in analysis.database_tables:
            # 기본 필드를 가진 간단한 모델 생성
            model = DataModel(
                model_name=table_name.title().replace('_', ''),
                table_name=table_name,
                fields=[
                    DataField(
                        name="id",
                        field_type=FieldType.INTEGER,
                        nullable=False,
                        unique=True,
                        description="Primary key"
                    ),
                    DataField(
                        name="created_at",
                        field_type=FieldType.DATETIME,
                        nullable=False,
                        description="Creation timestamp"
                    )
                ],
                relationships=[],
                indexes=[]
            )
            models.append(model)

        database_spec = DatabaseSpec(
            db_type=DatabaseType.SQLITE,
            database_url="sqlite:///./app.db",
            models=models,
            use_alembic=True
        )

    # 7. ProjectTemplate 결정
    try:
        template = ProjectTemplate(analysis.project_template)
    except ValueError:
        # 기본값 결정
        if analysis.requires_backend and analysis.requires_ui:
            template = ProjectTemplate.FULL_STACK
        elif analysis.requires_ui:
            template = ProjectTemplate.AGENT_WITH_STREAMLIT
        else:
            template = ProjectTemplate.AGENT_ONLY

    logger.info(f"  Final template: {template}")

    # 8. MultiProjectSpec 생성
    multi_spec = MultiProjectSpec(
        project=project,
        template=template,
        agent_spec=agent_spec,
        frontend_spec=frontend_spec,
        backend_spec=backend_spec,
        database_spec=database_spec,
        integration_points=[],
        deployment_config=None,
        additional_files={},
        domain_classification=analysis.domain_classification  # Add domain classification
    )

    logger.info("Conversion completed successfully")

    return multi_spec
