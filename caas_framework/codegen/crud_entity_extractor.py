"""
CRUD Entity Extractor

Task description과 domain classification에서 엔티티 정보를 추출합니다.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from caas_framework.bmad.code_analyzer import AnalysisResult
from caas_framework.bmad.models import TaskMapping
from caas_framework.utils.logger import LoggerMixin, get_logger

logger = get_logger("codegen.crud_extractor")


class FieldDefinition(BaseModel):
    """필드 정의"""

    name: str
    type: str  # Integer, String, Text, Boolean, DateTime, Float, Enum, ForeignKey
    primary_key: bool = False
    auto_generated: bool = False
    nullable: bool = False
    optional: bool = False
    index: bool = False
    default: Optional[Any] = None
    max_length: Optional[int] = None
    enum_values: Optional[List[str]] = None
    foreign_table: Optional[str] = None
    description: Optional[str] = None
    python_type: str = "str"  # For type hints


class EntityDefinition(BaseModel):
    """엔티티 정의"""

    name: str
    table_name: str
    description: Optional[str] = None
    fields: List[FieldDefinition]
    relationships: List[Dict[str, str]] = []
    has_enum_fields: bool = False
    filterable_fields: List[FieldDefinition] = []


class CRUDEntityExtractor(LoggerMixin):
    """
    CRUD 엔티티 추출기

    Task description과 domain classification에서 엔티티와 필드를 추출합니다.
    """

    # 타입 키워드 매핑
    TYPE_KEYWORDS = {
        # String 타입
        "title": ("String", False),
        "name": ("String", False),
        "email": ("String", False),
        "username": ("String", False),
        "password": ("String", False),
        "url": ("String", False),
        "address": ("String", True),  # Nullable
        "phone": ("String", True),
        # Text 타입 (긴 텍스트)
        "description": ("Text", True),
        "content": ("Text", True),
        "body": ("Text", True),
        "note": ("Text", True),
        "comment": ("Text", True),
        # Integer 타입
        "priority": ("Integer", True),
        "age": ("Integer", True),
        "count": ("Integer", False),
        "quantity": ("Integer", False),
        "amount": ("Integer", False),
        "id": ("Integer", False),
        # DateTime 타입
        "date": ("DateTime", True),
        "due_date": ("DateTime", True),
        "deadline": ("DateTime", True),
        "created_at": ("DateTime", False),
        "updated_at": ("DateTime", False),
        "deleted_at": ("DateTime", True),
        "timestamp": ("DateTime", False),
        # Boolean 타입
        "is_active": ("Boolean", False),
        "is_completed": ("Boolean", False),
        "is_deleted": ("Boolean", False),
        "enabled": ("Boolean", False),
        "completed": ("Boolean", False),
        # Float 타입
        "price": ("Float", False),
        "rating": ("Float", True),
        "score": ("Float", True),
        "percentage": ("Float", True),
        # Enum 타입 (상태)
        "status": ("Enum", False),
        "state": ("Enum", False),
        "type": ("Enum", False),
        "category": ("Enum", True),
        "role": ("Enum", False),
    }

    # 상태 enum 값 추론
    STATUS_ENUM_VALUES = {
        "status": ["pending", "in_progress", "completed", "cancelled"],
        "state": ["active", "inactive", "archived"],
        "type": ["task", "event", "note"],
        "role": ["admin", "user", "guest"],
    }

    def extract_entities(
        self, analysis_result: AnalysisResult, tasks: List[TaskMapping]
    ) -> List[EntityDefinition]:
        """
        분석 결과에서 엔티티 추출

        Args:
            analysis_result: 요구사항 분석 결과
            tasks: Task 목록 (정제된 Task)

        Returns:
            엔티티 정의 목록
        """
        self.logger.info("CRUD 엔티티 추출 시작")

        # 1. Core entities from domain classification
        core_entities = []
        if analysis_result.domain_classification:
            core_entities = analysis_result.domain_classification.core_entities
            self.logger.info(f"Core entities: {core_entities}")

        if not core_entities:
            self.logger.warning("Core entities가 없습니다. 기본 엔티티 사용")
            core_entities = ["Item"]  # Fallback

        # 2. 각 엔티티에 대해 필드 추출
        entities = []
        for entity_name in core_entities:
            # 기본 엔티티 정의
            entity = EntityDefinition(
                name=entity_name,
                table_name=self._to_table_name(entity_name),
                description=f"{entity_name} model",
                fields=[],
            )

            # 3. 필드 추출
            entity.fields = self._extract_fields(entity_name, tasks)

            # 4. 기본 필드 추가 (id, created_at, updated_at)
            entity.fields = self._add_default_fields(entity.fields)

            # 5. Enum 필드 감지
            entity.has_enum_fields = any(f.type == "Enum" for f in entity.fields)

            # 6. Filterable 필드 결정 (status, priority, type 등)
            entity.filterable_fields = [
                f
                for f in entity.fields
                if f.name in ["status", "priority", "type", "category", "role"]
            ]

            entities.append(entity)

        self.logger.info(f"추출된 엔티티: {len(entities)}개")
        for entity in entities:
            self.logger.info(f"  - {entity.name}: {len(entity.fields)}개 필드")

        return entities

    def _extract_fields(
        self, entity_name: str, tasks: List[TaskMapping]
    ) -> List[FieldDefinition]:
        """
        Task description에서 필드 추출

        Args:
            entity_name: 엔티티 이름
            tasks: Task 목록

        Returns:
            필드 정의 목록
        """
        fields = {}  # field_name -> FieldDefinition

        # Task description에서 필드 추출
        for task in tasks:
            # "Create a new Task with required fields (title, description, due_date, priority)"
            # "Retrieve Task(s) from database. Support filtering by status, priority, due_date"

            description = task.description.lower()

            # 필드 언급 패턴
            # 1. "with fields (title, description, ...)"
            fields_pattern = r"fields?\s*\(([^)]+)\)"
            matches = re.findall(fields_pattern, description)
            for match in matches:
                field_names = [f.strip() for f in match.split(",")]
                for field_name in field_names:
                    if field_name not in fields:
                        fields[field_name] = self._create_field_definition(field_name)

            # 2. "filtering by status, priority, due_date"
            filter_pattern = r"filtering by ([^.]+)"
            matches = re.findall(filter_pattern, description)
            for match in matches:
                field_names = [f.strip() for f in match.split(",")]
                for field_name in field_names:
                    if field_name not in fields:
                        fields[field_name] = self._create_field_definition(field_name)

            # 3. Task description에 직접 언급된 필드 (title, name, email 등)
            for keyword in self.TYPE_KEYWORDS.keys():
                if keyword in description and keyword not in fields:
                    # 확인: 실제 필드 언급인지 (예: "title"은 Task의 제목을 의미할 수도 있음)
                    if re.search(rf"\b{keyword}\b", description):
                        fields[keyword] = self._create_field_definition(keyword)

        return list(fields.values())

    def _create_field_definition(self, field_name: str) -> FieldDefinition:
        """
        필드 이름에서 필드 정의 생성 (타입 추론)

        Args:
            field_name: 필드 이름

        Returns:
            필드 정의
        """
        # 타입 추론
        field_type, nullable = self.TYPE_KEYWORDS.get(field_name, ("String", True))

        # Python 타입 힌트
        python_type_map = {
            "String": "str",
            "Text": "str",
            "Integer": "int",
            "Float": "float",
            "Boolean": "bool",
            "DateTime": "datetime",
            "Enum": "str",
        }
        python_type = python_type_map.get(field_type, "str")

        # Enum 값 추론
        enum_values = None
        if field_type == "Enum":
            enum_values = self.STATUS_ENUM_VALUES.get(field_name)

        # 필드 정의 생성
        field = FieldDefinition(
            name=field_name,
            type=field_type,
            nullable=nullable,
            optional=nullable,  # Create schema에서 optional
            python_type=python_type,
            enum_values=enum_values,
            description=f"{field_name} field",
        )

        # 인덱스 필드 (자주 조회되는 필드)
        if field_name in ["title", "name", "email", "username"]:
            field.index = True

        # 기본값
        if field_name == "priority":
            field.default = 0
        elif field_name in ["is_active", "enabled"]:
            field.default = True
        elif field_name in ["is_completed", "is_deleted"]:
            field.default = False

        return field

    def _add_default_fields(
        self, fields: List[FieldDefinition]
    ) -> List[FieldDefinition]:
        """
        기본 필드 추가 (id, created_at, updated_at)

        Args:
            fields: 기존 필드 목록

        Returns:
            기본 필드가 추가된 필드 목록
        """
        field_names = {f.name for f in fields}

        # id 필드 (항상 첫 번째)
        if "id" not in field_names:
            id_field = FieldDefinition(
                name="id",
                type="Integer",
                primary_key=True,
                auto_generated=True,
                index=True,
                python_type="int",
                description="Primary key",
            )
            fields.insert(0, id_field)

        # created_at 필드
        if "created_at" not in field_names:
            created_at_field = FieldDefinition(
                name="created_at",
                type="DateTime",
                auto_generated=True,
                default="now",
                python_type="datetime",
                description="Creation timestamp",
            )
            fields.append(created_at_field)

        # updated_at 필드
        if "updated_at" not in field_names:
            updated_at_field = FieldDefinition(
                name="updated_at",
                type="DateTime",
                auto_generated=True,
                default="now",
                nullable=True,
                python_type="datetime",
                description="Last update timestamp",
            )
            fields.append(updated_at_field)

        return fields

    def _to_table_name(self, entity_name: str) -> str:
        """
        엔티티 이름을 테이블 이름으로 변환

        Args:
            entity_name: 엔티티 이름 (예: "Task", "UserProfile")

        Returns:
            테이블 이름 (예: "tasks", "user_profiles")
        """
        # CamelCase → snake_case
        table_name = re.sub(r"(?<!^)(?=[A-Z])", "_", entity_name).lower()

        # 복수형 (간단한 규칙)
        if not table_name.endswith("s"):
            table_name += "s"

        return table_name
