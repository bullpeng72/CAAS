"""
CAAS Embedded Graph Backend

Neo4j 없이도 동작하는 임베디드 그래프 데이터베이스입니다.
개발 환경이나 빠른 시작을 위해 사용됩니다.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from caas_framework.utils.logger import LoggerMixin, get_logger

logger = get_logger("knowledge.embedded_graph")


class EmbeddedGraphNode:
    """임베디드 그래프 노드"""

    def __init__(self, node_id: str, labels: List[str], properties: Dict[str, Any]):
        self.id = node_id
        self.labels = labels
        self.properties = properties
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """노드를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "labels": self.labels,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddedGraphNode":
        """딕셔너리에서 노드 생성"""
        node = cls(data["id"], data["labels"], data["properties"])
        node.created_at = datetime.fromisoformat(data["created_at"])
        node.updated_at = datetime.fromisoformat(data["updated_at"])
        return node


class EmbeddedGraphRelationship:
    """임베디드 그래프 관계"""

    def __init__(
        self,
        rel_id: str,
        rel_type: str,
        start_node_id: str,
        end_node_id: str,
        properties: Dict[str, Any],
    ):
        self.id = rel_id
        self.type = rel_type
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.properties = properties
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """관계를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "type": self.type,
            "start_node_id": self.start_node_id,
            "end_node_id": self.end_node_id,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddedGraphRelationship":
        """딕셔너리에서 관계 생성"""
        rel = cls(
            data["id"],
            data["type"],
            data["start_node_id"],
            data["end_node_id"],
            data["properties"],
        )
        rel.created_at = datetime.fromisoformat(data["created_at"])
        return rel


class EmbeddedGraphClient(LoggerMixin):
    """
    임베디드 그래프 클라이언트

    Neo4j와 호환되는 인터페이스를 제공하지만
    인메모리 데이터 구조를 사용합니다.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        임베디드 그래프 클라이언트 초기화

        Args:
            storage_path: 데이터 저장 경로 (None이면 인메모리만 사용)
        """
        self.storage_path = storage_path
        self.nodes: Dict[str, EmbeddedGraphNode] = {}
        self.relationships: Dict[str, EmbeddedGraphRelationship] = {}
        self._node_counter = 0
        self._rel_counter = 0

        # 인덱스: label -> node_ids
        self._label_index: Dict[str, Set[str]] = {}

        # 인덱스: (start_node_id, rel_type) -> rel_ids
        self._outgoing_index: Dict[tuple, Set[str]] = {}

        # 인덱스: (end_node_id, rel_type) -> rel_ids
        self._incoming_index: Dict[tuple, Set[str]] = {}

        if storage_path and storage_path.exists():
            self.load()

        self.logger.info(
            f"Embedded graph initialized (storage: {storage_path or 'memory-only'})"
        )

    def verify_connectivity(self) -> bool:
        """연결성 검증 (항상 True)"""
        return True

    def close(self):
        """연결 종료 (저장)"""
        if self.storage_path:
            self.save()

    def save(self):
        """데이터를 파일에 저장"""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "relationships": {
                rid: rel.to_dict() for rid, rel in self.relationships.items()
            },
            "counters": {
                "node": self._node_counter,
                "rel": self._rel_counter,
            },
        }

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

        self.logger.debug(
            f"Saved {len(self.nodes)} nodes, {len(self.relationships)} relationships"
        )

    def load(self):
        """파일에서 데이터 로드"""
        if not self.storage_path or not self.storage_path.exists():
            return

        with open(self.storage_path, "r") as f:
            data = json.load(f)

        # 노드 로드
        self.nodes = {
            nid: EmbeddedGraphNode.from_dict(ndata)
            for nid, ndata in data["nodes"].items()
        }

        # 관계 로드
        self.relationships = {
            rid: EmbeddedGraphRelationship.from_dict(rdata)
            for rid, rdata in data["relationships"].items()
        }

        # 카운터 로드
        counters = data.get("counters", {})
        self._node_counter = counters.get("node", 0)
        self._rel_counter = counters.get("rel", 0)

        # 인덱스 재구축
        self._rebuild_indexes()

        self.logger.info(
            f"Loaded {len(self.nodes)} nodes, {len(self.relationships)} relationships"
        )

    def _rebuild_indexes(self):
        """인덱스 재구축"""
        self._label_index.clear()
        self._outgoing_index.clear()
        self._incoming_index.clear()

        for node_id, node in self.nodes.items():
            for label in node.labels:
                if label not in self._label_index:
                    self._label_index[label] = set()
                self._label_index[label].add(node_id)

        for rel_id, rel in self.relationships.items():
            # Outgoing
            key = (rel.start_node_id, rel.type)
            if key not in self._outgoing_index:
                self._outgoing_index[key] = set()
            self._outgoing_index[key].add(rel_id)

            # Incoming
            key = (rel.end_node_id, rel.type)
            if key not in self._incoming_index:
                self._incoming_index[key] = set()
            self._incoming_index[key].add(rel_id)

    def create_node(self, labels: List[str], properties: Dict[str, Any]) -> str:
        """
        노드 생성

        Args:
            labels: 노드 레이블 리스트
            properties: 노드 속성

        Returns:
            str: 생성된 노드 ID
        """
        node_id = f"n{self._node_counter}"
        self._node_counter += 1

        node = EmbeddedGraphNode(node_id, labels, properties)
        self.nodes[node_id] = node

        # 인덱스 업데이트
        for label in labels:
            if label not in self._label_index:
                self._label_index[label] = set()
            self._label_index[label].add(node_id)

        return node_id

    def create_relationship(
        self,
        start_node_id: str,
        end_node_id: str,
        rel_type: str,
        properties: Dict[str, Any] = None,
    ) -> str:
        """
        관계 생성

        Args:
            start_node_id: 시작 노드 ID
            end_node_id: 종료 노드 ID
            rel_type: 관계 타입
            properties: 관계 속성

        Returns:
            str: 생성된 관계 ID
        """
        if start_node_id not in self.nodes or end_node_id not in self.nodes:
            raise ValueError("Start or end node does not exist")

        rel_id = f"r{self._rel_counter}"
        self._rel_counter += 1

        rel = EmbeddedGraphRelationship(
            rel_id, rel_type, start_node_id, end_node_id, properties or {}
        )
        self.relationships[rel_id] = rel

        # 인덱스 업데이트
        out_key = (start_node_id, rel_type)
        if out_key not in self._outgoing_index:
            self._outgoing_index[out_key] = set()
        self._outgoing_index[out_key].add(rel_id)

        in_key = (end_node_id, rel_type)
        if in_key not in self._incoming_index:
            self._incoming_index[in_key] = set()
        self._incoming_index[in_key].add(rel_id)

        return rel_id

    def run_query(
        self, query: str, parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        쿼리 실행 (제한된 Cypher 지원)

        Args:
            query: Cypher 쿼리
            parameters: 쿼리 파라미터

        Returns:
            List[Dict[str, Any]]: 쿼리 결과
        """
        query_upper = query.upper().strip()

        # 노드 수 카운트
        if "MATCH (N) RETURN COUNT(N)" in query_upper:
            return [{"count": len(self.nodes)}]

        # 관계 수 카운트
        if "MATCH ()-[R]->() RETURN COUNT(R)" in query_upper:
            return [{"count": len(self.relationships)}]

        # 모든 노드 반환
        if "MATCH (N) RETURN N" in query_upper:
            limit = 10
            if "LIMIT" in query_upper:
                try:
                    limit = int(query_upper.split("LIMIT")[-1].strip())
                except (ValueError, IndexError):
                    pass

            results = []
            for node_id, node in list(self.nodes.items())[:limit]:
                results.append({"n": node.to_dict()})
            return results

        # Pattern 노드 조회
        if "MATCH (P:PATTERN)" in query_upper:
            pattern_nodes = self._label_index.get("Pattern", set())
            results = []
            for node_id in list(pattern_nodes)[:20]:
                node = self.nodes[node_id]
                results.append({"p": node.to_dict()})
            return results

        # 기본: 빈 결과
        self.logger.warning(f"Unsupported query: {query[:100]}")
        return []

    def find_nodes_by_label(
        self, label: str, limit: int = 100
    ) -> List[EmbeddedGraphNode]:
        """
        레이블로 노드 검색

        Args:
            label: 노드 레이블
            limit: 최대 결과 수

        Returns:
            List[EmbeddedGraphNode]: 노드 리스트
        """
        node_ids = self._label_index.get(label, set())
        return [self.nodes[nid] for nid in list(node_ids)[:limit]]

    def find_patterns(
        self,
        domain: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        패턴 검색

        Args:
            domain: 도메인 필터
            keywords: 키워드 리스트
            limit: 최대 결과 수

        Returns:
            List[Dict[str, Any]]: 패턴 리스트
        """
        pattern_nodes = self.find_nodes_by_label("Pattern", limit=100)

        results = []
        for node in pattern_nodes:
            props = node.properties

            # 도메인 필터
            if domain and props.get("domain") != domain:
                continue

            # 키워드 필터
            if keywords:
                pattern_keywords = props.get("keywords", [])
                if not any(kw in pattern_keywords for kw in keywords):
                    continue

            results.append(
                {
                    "id": props.get("id"),
                    "name": props.get("name"),
                    "description": props.get("description"),
                    "domain": props.get("domain"),
                    "keywords": props.get("keywords", []),
                    "success_rate": props.get("success_rate", 0.0),
                    "usage_count": props.get("usage_count", 0),
                }
            )

            if len(results) >= limit:
                break

        return results

    def clear_all(self):
        """모든 데이터 삭제"""
        self.nodes.clear()
        self.relationships.clear()
        self._label_index.clear()
        self._outgoing_index.clear()
        self._incoming_index.clear()
        self._node_counter = 0
        self._rel_counter = 0

        self.logger.info("All data cleared")
