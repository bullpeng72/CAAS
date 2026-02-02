"""
Requirement Traceability Matrix

요구사항 추적성 매트릭스 - Requirement → Feature → Agent → Task → Code 추적
"""

import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from ..models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    FeatureSpec,
    TaskSpecModel,
)
from ..utils import ObjectAccessor, TextNormalizer


class TraceabilityLink(BaseModel):
    """추적성 링크"""

    source_type: str  # "requirement", "feature", "agent", "task", "code"
    source_id: str
    target_type: str
    target_id: str
    link_type: str = "implements"  # "implements", "tests", "depends_on", "derives_from"
    confidence: float = 1.0  # 0.0 ~ 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CoverageReport(BaseModel):
    """커버리지 리포트"""

    total_requirements: int
    implemented_requirements: int
    total_features: int
    implemented_features: int
    total_tasks: int
    total_code_elements: int
    coverage_percentage: float
    gaps: List[str] = Field(default_factory=list)


class TraceabilityMatrix:
    """추적성 매트릭스"""

    def __init__(self):
        self.links: List[TraceabilityLink] = []
        self._link_index: Dict[str, List[TraceabilityLink]] = {}

    def add_link(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        link_type: str = "implements",
        confidence: float = 1.0,
        metadata: Optional[Dict] = None,
    ):
        """추적성 링크 추가"""
        link = TraceabilityLink(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            link_type=link_type,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.links.append(link)

        # 인덱스 업데이트
        key = f"{source_type}:{source_id}"
        if key not in self._link_index:
            self._link_index[key] = []
        self._link_index[key].append(link)

    def get_trace_forward(self, source_type: str, source_id: str) -> List[TraceabilityLink]:
        """전방 추적 (Requirement → Code)"""
        key = f"{source_type}:{source_id}"
        return self._link_index.get(key, [])

    def get_trace_backward(self, target_type: str, target_id: str) -> List[TraceabilityLink]:
        """후방 추적 (Code → Requirement)"""
        return [
            link
            for link in self.links
            if link.target_type == target_type and link.target_id == target_id
        ]

    def get_full_trace_path(self, source_type: str, source_id: str) -> List[List[TraceabilityLink]]:
        """전체 추적 경로 (모든 경로)"""
        paths = []
        self._find_paths(source_type, source_id, [], paths)
        return paths

    def _find_paths(
        self,
        current_type: str,
        current_id: str,
        current_path: List[TraceabilityLink],
        all_paths: List[List[TraceabilityLink]],
    ):
        """재귀적으로 모든 경로 찾기"""
        forward_links = self.get_trace_forward(current_type, current_id)

        if not forward_links:
            # 리프 노드 도달
            if current_path:
                all_paths.append(current_path.copy())
            return

        for link in forward_links:
            current_path.append(link)
            self._find_paths(link.target_type, link.target_id, current_path, all_paths)
            current_path.pop()

    def validate_completeness(self) -> CoverageReport:
        """추적성 완전성 검증"""

        # 모든 소스 타입별 집계
        requirements = self._get_unique_items("requirement")
        features = self._get_unique_items("feature")
        agents = self._get_unique_items("agent")
        tasks = self._get_unique_items("task")
        code_elements = self._get_unique_items("code")

        # 구현된 항목 (타겟이 있는 소스)
        implemented_reqs = set()
        implemented_features = set()

        # Build ID to name mapping from metadata
        req_id_to_text = {}
        feature_id_to_name = {}

        for link in self.links:
            if link.source_type == "requirement":
                implemented_reqs.add(link.source_id)
                if "requirement_text" in link.metadata:
                    req_id_to_text[link.source_id] = link.metadata["requirement_text"][:50]
            elif link.source_type == "feature":
                implemented_features.add(link.source_id)
                if "feature_name" in link.metadata:
                    feature_id_to_name[link.source_id] = link.metadata["feature_name"]

            # Also collect from target
            if link.target_type == "feature" and "feature_name" in link.metadata:
                feature_id_to_name[link.target_id] = link.metadata["feature_name"]

        # 갭 식별 - use meaningful names from metadata
        gaps = []
        for req in requirements:
            if req not in implemented_reqs:
                display_name = req_id_to_text.get(req, req)
                gaps.append(f"요구사항 '{display_name}'가 구현되지 않았습니다")

        for feat in features:
            if feat not in implemented_features:
                display_name = feature_id_to_name.get(feat, feat)
                gaps.append(f"기능 '{display_name}'이 구현되지 않았습니다")

        # 커버리지 계산
        total_reqs = len(requirements)
        total_feats = len(features)

        if total_reqs > 0:
            req_coverage = len(implemented_reqs) / total_reqs
        else:
            req_coverage = 1.0

        if total_feats > 0:
            feat_coverage = len(implemented_features) / total_feats
        else:
            feat_coverage = 1.0

        overall_coverage = (req_coverage + feat_coverage) / 2

        return CoverageReport(
            total_requirements=total_reqs,
            implemented_requirements=len(implemented_reqs),
            total_features=total_feats,
            implemented_features=len(implemented_features),
            total_tasks=len(tasks),
            total_code_elements=len(code_elements),
            coverage_percentage=overall_coverage * 100,
            gaps=gaps,
        )

    def _get_unique_items(self, item_type: str) -> Set[str]:
        """특정 타입의 고유 아이템 집합"""
        items = set()
        for link in self.links:
            if link.source_type == item_type:
                items.add(link.source_id)
            if link.target_type == item_type:
                items.add(link.target_id)
        return items

    def export_to_dict(self) -> Dict:
        """딕셔너리로 내보내기"""
        return {
            "links": [link.model_dump() for link in self.links],
            "summary": {
                "total_links": len(self.links),
                "link_types": self._count_by_link_type(),
            },
        }

    def _count_by_link_type(self) -> Dict[str, int]:
        """링크 타입별 개수"""
        counts = {}
        for link in self.links:
            key = f"{link.source_type} → {link.target_type}"
            counts[key] = counts.get(key, 0) + 1
        return counts


class TraceabilityManager:
    """추적성 관리자"""

    def __init__(self):
        self.matrix = TraceabilityMatrix()

    def build_from_workflow(
        self,
        requirement: str,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        generated_code: Optional[Dict[str, str]] = None,
    ):
        """
        워크플로우에서 추적성 매트릭스 구축

        Args:
            requirement: 원본 요구사항
            golden_data: Golden Data
            agents: 에이전트 목록
            tasks: 태스크 목록
            generated_code: 생성된 코드 (파일명 → 코드)
        """

        # 1. Requirement → Feature
        req_id = TextNormalizer.normalize_id(requirement[:50], ascii_only=True, max_length=64)
        features = golden_data.features if golden_data.features else []
        for feature in features:
            feature_id = ObjectAccessor.get_value(feature, "id", "")
            feature_name = ObjectAccessor.get_value(feature, "name", "")
            self.matrix.add_link(
                "requirement",
                req_id,
                "feature",
                feature_id,
                link_type="derives_from",
                metadata={
                    "requirement_text": requirement[:100],  # 요구사항 텍스트 저장
                    "feature_name": feature_name,  # Feature 이름 저장
                },
            )

        # 2. Feature → Task (description 기반 매칭)
        for task in tasks:
            matched_features = self._match_task_to_features(task, features)
            task_id = ObjectAccessor.get_value(task, "id", "")
            task_description = ObjectAccessor.get_value(task, "description", "")

            # matched_features is now Dict[str, float] (feature_id -> confidence)
            for feature_id, confidence in matched_features.items():
                # Find feature name
                feature_name = ""
                for f in features:
                    if ObjectAccessor.get_value(f, "id", "") == feature_id:
                        feature_name = ObjectAccessor.get_value(f, "name", "")
                        break

                self.matrix.add_link(
                    "feature",
                    feature_id,
                    "task",
                    task_id,
                    confidence=confidence,
                    metadata={
                        "feature_name": feature_name,
                        "task_description": task_description[:100],
                    },
                )

        # 3. Agent → Task
        for task in tasks:
            task_agent = ObjectAccessor.get_value(task, "agent", "")
            task_id = ObjectAccessor.get_value(task, "id", "")
            task_description = ObjectAccessor.get_value(task, "description", "")

            # Find agent role
            agent_role = ""
            for agent in agents:
                agent_id = ObjectAccessor.get_value(agent, "id", "")
                if agent_id == task_agent:
                    agent_role = ObjectAccessor.get_value(agent, "role", "")
                    break

            self.matrix.add_link(
                "agent",
                task_agent,
                "task",
                task_id,
                metadata={"agent_role": agent_role, "task_description": task_description[:100]},
            )

        # 4. Task → Code (generated_code가 있으면)
        if generated_code:
            for task in tasks:
                task_id = ObjectAccessor.get_value(task, "id", "")
                code_elements = self._extract_code_elements(generated_code, task)
                for element in code_elements:
                    self.matrix.add_link("task", task_id, "code", element)

    def _match_task_to_features(
        self, task: TaskSpecModel, features: List[FeatureSpec]
    ) -> Dict[str, float]:
        """
        Task를 Feature에 매칭 (키워드 기반)

        Returns:
            Dict[str, float]: Feature ID → 신뢰도
        """
        matches = {}
        # Handle both dict and object
        task_description = ObjectAccessor.get_value(task, "description", "")
        task_expected_output = ObjectAccessor.get_value(task, "expected_output", "")
        task_text = f"{task_description} {task_expected_output}".lower()

        for feature in features:
            # Handle both dict and object for features
            feature_id = ObjectAccessor.get_value(feature, "id", "")
            feature_name = ObjectAccessor.get_value(feature, "name", "")
            feature_description = ObjectAccessor.get_value(feature, "description", "")
            feature_keywords = self._extract_keywords(f"{feature_name} {feature_description}")

            # 키워드 매칭 개수
            match_count = sum(1 for keyword in feature_keywords if keyword in task_text)

            if match_count > 0:
                confidence = min(1.0, match_count / max(len(feature_keywords), 1))
                # Use feature ID as key instead of feature object
                matches[feature_id] = confidence

        return matches

    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 단순한 토큰화 (실제로는 NLP 라이브러리 사용 가능)
        text = text.lower()
        # 영어/한글 단어 추출
        words = re.findall(r"[a-z가-힣]{3,}", text)
        # 불용어 제거 (간단한 예시)
        stopwords = {"the", "is", "and", "or", "을", "를", "이", "가", "에"}
        return [w for w in words if w not in stopwords]

    def _extract_code_elements(
        self, generated_code: Dict[str, str], task: TaskSpecModel
    ) -> List[str]:
        """
        생성된 코드에서 Task와 관련된 요소 추출

        Returns:
            List[str]: 함수명/클래스명 목록
        """
        elements = []
        # Handle both dict and object
        task_description = ObjectAccessor.get_value(task, "description", "")
        task_keywords = self._extract_keywords(task_description)

        for filepath, code in generated_code.items():
            # 함수 정의 찾기 (Python)
            functions = re.findall(r"def\s+(\w+)\s*\(", code)
            # 클래스 정의 찾기
            classes = re.findall(r"class\s+(\w+)\s*[(:|\(]", code)

            all_names = functions + classes

            # Task 키워드와 매칭되는 이름만
            for name in all_names:
                name_lower = name.lower()
                if any(keyword in name_lower for keyword in task_keywords):
                    elements.append(f"{filepath}::{name}")

        return elements

    def generate_report(self) -> str:
        """추적성 리포트 생성"""
        coverage = self.matrix.validate_completeness()

        report = f"""
# 요구사항 추적성 매트릭스 (RTM)

## 📊 요약
- 전체 요구사항: {coverage.total_requirements}개
- 구현된 요구사항: {coverage.implemented_requirements}개
- 전체 기능: {coverage.total_features}개
- 구현된 기능: {coverage.implemented_features}개
- 태스크 수: {coverage.total_tasks}개
- 코드 요소 수: {coverage.total_code_elements}개
- **커버리지: {coverage.coverage_percentage:.1f}%**

## 🔗 추적성 맵

### 링크 통계
"""

        link_counts = self.matrix._count_by_link_type()
        for link_type, count in link_counts.items():
            report += f"- {link_type}: {count}개\n"

        # 갭 리포트
        if coverage.gaps:
            report += "\n## ⚠️ 갭 (미구현 항목)\n\n"
            for gap in coverage.gaps:
                report += f"- {gap}\n"
        else:
            report += "\n## ✅ 갭 없음 - 모든 요구사항이 구현되었습니다!\n"

        return report

    def generate_visual_map(self) -> str:
        """
        시각적 추적 맵 (Mermaid)을 생성합니다.

        Returns:
            str: Mermaid flowchart 코드
        """
        # Use flowchart instead of graph for better stability
        mermaid_lines = ["flowchart TD"]

        # 빈 링크 처리
        if not self.matrix.links:
            mermaid_lines.append('    Empty["No traceability links found"]')
            return "\n".join(mermaid_lines)

        # Track nodes and edges
        nodes = {}  # {node_id: label}
        edges = []  # [(source_id, target_id)]

        for link in self.matrix.links[:50]:  # 최대 50개 링크만 표시
            # Skip if source or target ID is empty
            if not link.source_id or not link.target_id:
                continue

            # Create Mermaid-compatible node IDs
            source_node_id = TextNormalizer.sanitize_mermaid_id(
                f"{link.source_type}_{link.source_id}",
                allow_korean=False,  # ASCII only for node IDs
            )
            target_node_id = TextNormalizer.sanitize_mermaid_id(
                f"{link.target_type}_{link.target_id}", allow_korean=False
            )

            # Skip if sanitized IDs are empty or invalid
            if not source_node_id or not target_node_id:
                continue

            # Skip self-loops
            if source_node_id == target_node_id:
                continue

            # Create labels (can include Korean) - use metadata for better labels
            if source_node_id not in nodes:
                # Try to get meaningful name from metadata
                source_display_name = link.source_id

                if link.source_type == "requirement" and "requirement_text" in link.metadata:
                    source_display_name = link.metadata["requirement_text"][:30] + "..."
                elif link.source_type == "feature" and "feature_name" in link.metadata:
                    source_display_name = link.metadata["feature_name"]
                elif link.source_type == "agent" and "agent_role" in link.metadata:
                    source_display_name = link.metadata["agent_role"]

                source_label = TextNormalizer.clean_mermaid_label(
                    f"{link.source_type}: {source_display_name}", max_length=40
                )
                nodes[source_node_id] = source_label or link.source_type

            if target_node_id not in nodes:
                # Try to get meaningful name from metadata
                target_display_name = link.target_id

                if link.target_type == "feature" and "feature_name" in link.metadata:
                    target_display_name = link.metadata["feature_name"]
                elif link.target_type == "task" and "task_description" in link.metadata:
                    target_display_name = link.metadata["task_description"][:30] + "..."
                elif link.target_type == "agent" and "agent_role" in link.metadata:
                    target_display_name = link.metadata["agent_role"]

                target_label = TextNormalizer.clean_mermaid_label(
                    f"{link.target_type}: {target_display_name}", max_length=40
                )
                nodes[target_node_id] = target_label or link.target_type

            edges.append((source_node_id, target_node_id))

        # If no valid nodes/edges, return placeholder
        if not nodes or not edges:
            mermaid_lines.append('    Empty["No valid traceability links"]')
            return "\n".join(mermaid_lines)

        # Define all nodes first (better Mermaid practice)
        for node_id, label in sorted(nodes.items()):
            mermaid_lines.append(f'    {node_id}["{label}"]')

        # Add all edges
        for source_id, target_id in edges:
            mermaid_lines.append(f"    {source_id} --> {target_id}")

        return "\n".join(mermaid_lines)

    def export_to_json(self) -> Dict:
        """JSON으로 내보내기"""
        return self.matrix.export_to_dict()


def build_traceability(
    requirement: str,
    golden_data: ConcretizedRequirement,
    agents: List[AgentSpecModel],
    tasks: List[TaskSpecModel],
    generated_code: Optional[Dict[str, str]] = None,
) -> TraceabilityManager:
    """
    Helper function - 추적성 매트릭스 구축

    Args:
        requirement: 원본 요구사항
        golden_data: Golden Data
        agents: 에이전트 목록
        tasks: 태스크 목록
        generated_code: 생성된 코드

    Returns:
        TraceabilityManager
    """
    manager = TraceabilityManager()
    manager.build_from_workflow(requirement, golden_data, agents, tasks, generated_code)
    return manager
