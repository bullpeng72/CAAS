"""
Task Description Refiner

모호한 Task description을 실행 가능한 형태로 변환합니다.

핵심 개념:
- 기능 요구사항 → 실행 가능한 Task 명령
- CRUD 동사 감지 및 정제
- 도메인별 Task 패턴 적용
"""

from typing import List, Optional
from app.models.domain_types import DomainType
from app.core.bmad.models import TaskMapping
from app.utils.logger import get_logger

logger = get_logger("bmad.task_refiner")


class TaskRefiner:
    """
    Task description 정제기

    모호한 기능 요구사항을 구체적이고 실행 가능한 Task description으로 변환합니다.
    """

    # CRUD 동사 매핑 (한글 → 영어)
    CRUD_VERBS = {
        # Create
        "추가": "create",
        "생성": "create",
        "만들": "create",
        "등록": "create",
        "작성": "create",

        # Read
        "조회": "read",
        "확인": "read",
        "보기": "read",
        "검색": "read",
        "조사": "read",
        "찾": "read",

        # Update
        "수정": "update",
        "변경": "update",
        "업데이트": "update",
        "편집": "update",

        # Delete
        "삭제": "delete",
        "제거": "delete",
        "지우": "delete",
    }

    # 영어 CRUD 동사
    CRUD_VERBS_EN = {
        "add": "create",
        "create": "create",
        "make": "create",
        "register": "create",
        "insert": "create",

        "get": "read",
        "read": "read",
        "view": "read",
        "list": "read",
        "search": "read",
        "find": "read",
        "retrieve": "read",

        "edit": "update",
        "modify": "update",
        "change": "update",
        "update": "update",

        "remove": "delete",
        "delete": "delete",
        "drop": "delete",
    }

    def __init__(self):
        pass

    def refine_task(
        self,
        task: TaskMapping,
        domain_type: DomainType,
        entities: List[str]
    ) -> TaskMapping:
        """
        Task description을 실행 가능한 형태로 정제

        Args:
            task: 원본 Task
            domain_type: 도메인 타입
            entities: 핵심 엔티티 목록

        Returns:
            정제된 Task
        """
        description_lower = task.description.lower()

        # CRUD 동사 감지
        detected_operation = self._detect_operation(description_lower)

        # 엔티티 감지
        detected_entity = self._detect_entity(description_lower, entities)

        logger.info(
            f"Task 정제: operation={detected_operation}, entity={detected_entity}, "
            f"domain={domain_type}"
        )

        # 도메인별 정제 패턴 적용
        if domain_type == DomainType.TASK_MANAGEMENT:
            return self._refine_task_management(
                task, detected_operation, detected_entity
            )
        elif domain_type == DomainType.E_COMMERCE:
            return self._refine_e_commerce(
                task, detected_operation, detected_entity
            )
        elif domain_type == DomainType.DASHBOARD:
            return self._refine_dashboard(
                task, detected_operation, detected_entity
            )
        elif domain_type == DomainType.CONVERSATIONAL_AI:
            return self._refine_conversational_ai(task)
        elif domain_type == DomainType.DATA_ANALYSIS:
            return self._refine_data_analysis(task)
        else:
            # 기본 정제 (operation이 감지된 경우)
            if detected_operation and detected_entity:
                return self._refine_generic(task, detected_operation, detected_entity)

        return task

    def _detect_operation(self, description: str) -> Optional[str]:
        """CRUD 동작 감지"""
        # 한글 동사 체크
        for korean, english in self.CRUD_VERBS.items():
            if korean in description:
                return english

        # 영어 동사 체크
        for english_verb, crud_op in self.CRUD_VERBS_EN.items():
            if english_verb in description:
                return crud_op

        return None

    def _detect_entity(self, description: str, entities: List[str]) -> Optional[str]:
        """엔티티 감지"""
        for entity in entities:
            if entity.lower() in description:
                return entity

        return None

    def _refine_task_management(
        self,
        task: TaskMapping,
        operation: Optional[str],
        entity: Optional[str]
    ) -> TaskMapping:
        """Task Management 도메인 특화 정제"""

        entity = entity or "Task"  # 기본 엔티티

        if operation == "create":
            task.description = (
                f"Create a new {entity} with required fields "
                f"(title, description, due_date, priority). "
                f"Validate input data, save to database, and return {entity} ID."
            )
            task.expected_output = f"{entity} ID and creation timestamp in JSON format"
            task.required_tools = ["database_write", "input_validation"]

        elif operation == "read":
            task.description = (
                f"Retrieve {entity}(s) from database. "
                f"Support filtering by status, priority, due_date, and user. "
                f"Return paginated results if needed."
            )
            task.expected_output = f"List of {entity} objects in JSON format"
            task.required_tools = ["database_read"]

        elif operation == "update":
            task.description = (
                f"Update an existing {entity} with new field values. "
                f"Validate {entity} ID exists, validate new data, "
                f"update database record, and return updated {entity}."
            )
            task.expected_output = f"Updated {entity} object in JSON format"
            task.required_tools = ["database_write", "input_validation"]

        elif operation == "delete":
            task.description = (
                f"Delete a {entity} from the database. "
                f"Validate {entity} ID exists, check for dependencies, "
                f"perform soft or hard delete, and return confirmation."
            )
            task.expected_output = f"Deletion confirmation with {entity} ID"
            task.required_tools = ["database_write"]

        else:
            # Operation 없으면 generic task management
            task.description = (
                f"Manage {entity} operations. "
                f"Handle task lifecycle including creation, updates, status changes, and notifications."
            )
            task.expected_output = f"{entity} operation result"
            task.required_tools = ["database_read", "database_write"]

        return task

    def _refine_e_commerce(
        self,
        task: TaskMapping,
        operation: Optional[str],
        entity: Optional[str]
    ) -> TaskMapping:
        """E-commerce 도메인 특화 정제"""

        entity = entity or "Product"

        if operation == "create":
            task.description = (
                f"Create a new {entity} with details "
                f"(name, description, price, stock, category, images). "
                f"Validate business rules, save to database, and return {entity} ID."
            )
            task.expected_output = f"{entity} ID and creation details in JSON format"
            task.required_tools = ["database_write", "input_validation", "file_upload"]

        elif operation == "read":
            task.description = (
                f"Retrieve {entity}(s) from catalog. "
                f"Support search, filtering by category/price, sorting, and pagination. "
                f"Return product details with availability."
            )
            task.expected_output = f"List of {entity} objects with pricing and availability"
            task.required_tools = ["database_read"]

        elif operation == "update":
            task.description = (
                f"Update {entity} information (price, stock, description). "
                f"Validate {entity} ID, update inventory, log price changes, "
                f"and return updated {entity}."
            )
            task.expected_output = f"Updated {entity} with change history"
            task.required_tools = ["database_write", "input_validation"]

        elif operation == "delete":
            task.description = (
                f"Archive or delete {entity} from catalog. "
                f"Check for active orders, handle soft delete, "
                f"update inventory, and return confirmation."
            )
            task.expected_output = f"Archival confirmation with {entity} ID"
            task.required_tools = ["database_write"]

        return task

    def _refine_dashboard(
        self,
        task: TaskMapping,
        operation: Optional[str],
        entity: Optional[str]
    ) -> TaskMapping:
        """Dashboard 도메인 특화 정제"""

        # Dashboard는 주로 Read 작업
        task.description = (
            "Fetch and aggregate data for dashboard visualization. "
            "Calculate KPIs, metrics, and trends. "
            "Format data for charts and graphs."
        )
        task.expected_output = "Dashboard data in JSON format with metrics and trends"
        task.required_tools = ["database_read", "data_aggregation"]

        return task

    def _refine_conversational_ai(self, task: TaskMapping) -> TaskMapping:
        """Conversational AI 도메인 특화 정제"""

        description_lower = task.description.lower()

        if "intent" in description_lower or "의도" in description_lower:
            task.description = (
                "Analyze user message to identify intent and entities. "
                "Use NLP to classify message type (question, command, statement). "
                "Extract key entities (person, location, time) for context."
            )
            task.expected_output = "Intent classification with confidence score and entities"
            task.required_tools = ["nlp", "intent_classifier"]

        elif "respond" in description_lower or "응답" in description_lower:
            task.description = (
                "Generate appropriate response based on user intent and context. "
                "Maintain conversation history and tone consistency. "
                "Personalize response based on user profile."
            )
            task.expected_output = "Response text with emotion indicators"
            task.required_tools = ["llm", "context_manager"]

        elif "context" in description_lower or "컨텍스트" in description_lower:
            task.description = (
                "Manage conversation context and history. "
                "Track mentioned entities, topics, and user preferences. "
                "Maintain session state for multi-turn conversations."
            )
            task.expected_output = "Updated context with relevant history"
            task.required_tools = ["memory", "context_store"]

        return task

    def _refine_data_analysis(self, task: TaskMapping) -> TaskMapping:
        """Data Analysis 도메인 특화 정제"""

        description_lower = task.description.lower()

        if "analyze" in description_lower or "분석" in description_lower:
            task.description = (
                "Analyze dataset to identify patterns, trends, and anomalies. "
                "Perform statistical analysis (mean, median, correlation). "
                "Generate insights and recommendations based on findings."
            )
            task.expected_output = "Analysis report with statistics and visualizations"
            task.required_tools = ["data_analysis", "statistics"]

        elif "visualize" in description_lower or "시각화" in description_lower:
            task.description = (
                "Create visualizations (charts, graphs, heatmaps) from analyzed data. "
                "Choose appropriate chart types for data characteristics. "
                "Apply consistent styling and labeling."
            )
            task.expected_output = "Visualization files (PNG, SVG) with data insights"
            task.required_tools = ["visualization", "charting"]

        return task

    def _refine_generic(
        self,
        task: TaskMapping,
        operation: str,
        entity: str
    ) -> TaskMapping:
        """범용 정제 (도메인 특화가 없는 경우)"""

        operation_templates = {
            "create": f"Create a new {entity} with required attributes. Validate and persist to storage.",
            "read": f"Retrieve {entity} data from storage. Support filtering and pagination.",
            "update": f"Update existing {entity} with new values. Validate and save changes.",
            "delete": f"Delete {entity} from storage. Validate and confirm deletion.",
        }

        output_templates = {
            "create": f"{entity} ID and creation status",
            "read": f"List of {entity} objects",
            "update": f"Updated {entity} object",
            "delete": f"Deletion confirmation",
        }

        task.description = operation_templates.get(operation, task.description)
        task.expected_output = output_templates.get(operation, task.expected_output)

        return task
