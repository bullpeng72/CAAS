"""
Knowledge Graph Pattern Matching

패턴 검색 및 매칭 기능을 제공합니다.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum

from caas_framework.utils.logger import get_logger, LoggerMixin
from app.knowledge.graph.neo4j_client import Neo4jClient
from app.knowledge.graph.queries import (
    FIND_PATTERNS_BY_DOMAIN,
    FIND_SIMILAR_PATTERNS,
    CREATE_PATTERN,
    INCREMENT_PATTERN_USAGE,
    FIND_TEMPLATES_FOR_PATTERN,
    # Advanced pattern queries
    CREATE_PATTERN_WITH_TEMPLATE,
    UPDATE_PATTERN_VERSION,
    FIND_LATEST_PATTERN,
    RECORD_PATTERN_SUCCESS,
    GET_PATTERN_RECOMMENDATIONS,
    FIND_PATTERNS_BY_ONTOLOGY,
    # Template queries
    CREATE_CODE_TEMPLATE,
    LINK_TEMPLATE_TO_PATTERN,
    GET_PATTERN_WITH_TEMPLATES,
    # Lifecycle queries
    GET_PATTERN_HISTORY,
    GET_PATTERN_USAGE_STATS,
    DEPRECATE_PATTERN,
)

logger = get_logger("knowledge.patterns")


class PatternType(str, Enum):
    """패턴 유형"""
    WORKFLOW = "workflow"
    AGENT_COMPOSITION = "agent_composition"
    TASK_SEQUENCE = "task_sequence"
    TOOL_INTEGRATION = "tool_integration"
    ERROR_HANDLING = "error_handling"


class PatternMatch(BaseModel):
    """패턴 매칭 결과"""
    pattern_id: str
    pattern_name: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    matched_features: List[str] = Field(default_factory=list)
    suggested_adaptations: List[str] = Field(default_factory=list)


class AgentPattern(BaseModel):
    """에이전트 패턴"""
    id: str
    name: str
    description: str
    pattern_type: PatternType = PatternType.AGENT_COMPOSITION
    agent_roles: List[str] = Field(default_factory=list)
    task_types: List[str] = Field(default_factory=list)
    recommended_tools: List[str] = Field(default_factory=list)
    workflow_type: str = "sequential"
    use_case: str = ""
    usage_count: int = 0
    success_rate: float = 0.0
    domain: str = "general"
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    version: str = "1.0.0"
    is_builtin: bool = True


class TemplateInfo(BaseModel):
    """템플릿 정보"""
    id: str
    name: str
    category: str
    code_template: str = ""
    config_template: str = ""
    description: str = ""
    parameters: List[str] = Field(default_factory=list)


class PatternMatcher(LoggerMixin):
    """
    패턴 매칭 엔진
    
    요구사항이나 스펙에 맞는 패턴을 검색하고 매칭합니다.
    """
    
    def __init__(self, client: Optional[Neo4jClient] = None):
        self.client = client or Neo4jClient()
        
        # 미리 정의된 패턴 (Neo4j 없이도 사용 가능)
        self.builtin_patterns = self._load_builtin_patterns()
    
    def find_patterns(
        self,
        domain: str,
        task_types: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[AgentPattern]:
        """
        조건에 맞는 패턴을 검색합니다.
        
        Args:
            domain: 도메인
            task_types: 태스크 유형 목록
            keywords: 검색 키워드
            limit: 최대 결과 수
        
        Returns:
            List[AgentPattern]: 매칭된 패턴 목록
        """
        self.logger.info(f"패턴 검색: domain={domain}, tasks={task_types}")
        
        patterns = []
        
        # 1. Neo4j에서 검색 시도
        if self.client.verify_connectivity():
            try:
                # 도메인 기반 검색
                result = self.client.run_query(
                    FIND_PATTERNS_BY_DOMAIN.query,
                    {"domain": domain, "limit": limit}
                )
                for record in result:
                    pattern_data = dict(record["p"])
                    patterns.append(self._record_to_pattern(pattern_data))
                
                # 키워드 기반 추가 검색
                if keywords:
                    for keyword in keywords[:3]:  # 최대 3개 키워드
                        result = self.client.run_query(
                            FIND_SIMILAR_PATTERNS.query,
                            {"keyword": keyword, "limit": 5}
                        )
                        for record in result:
                            pattern_data = dict(record["p"])
                            pattern = self._record_to_pattern(pattern_data)
                            if pattern.id not in [p.id for p in patterns]:
                                patterns.append(pattern)
                
            except Exception as e:
                self.logger.warning(f"Neo4j 패턴 검색 실패: {e}")
        
        # 2. 내장 패턴에서 검색
        builtin_matches = self._search_builtin_patterns(domain, task_types, keywords)
        
        # 중복 제거하며 병합
        existing_ids = {p.id for p in patterns}
        for pattern in builtin_matches:
            if pattern.id not in existing_ids:
                patterns.append(pattern)
        
        # 정렬 (usage_count 기준)
        patterns.sort(key=lambda p: p.usage_count, reverse=True)
        
        return patterns[:limit]
    
    def match_pattern(
        self,
        requirement_features: List[str],
        domain: str,
    ) -> List[PatternMatch]:
        """
        요구사항 특성에 맞는 패턴을 매칭합니다.
        
        Args:
            requirement_features: 요구사항에서 추출된 특성
            domain: 도메인
        
        Returns:
            List[PatternMatch]: 매칭 결과 목록
        """
        self.logger.info(f"패턴 매칭: {len(requirement_features)} features")
        
        # 패턴 검색
        patterns = self.find_patterns(
            domain=domain,
            keywords=requirement_features[:5],
            limit=20,
        )
        
        # 유사도 계산
        matches = []
        for pattern in patterns:
            score, matched_features = self._calculate_similarity(
                requirement_features,
                pattern,
            )
            
            if score > 0.3:  # 최소 유사도 임계값
                match = PatternMatch(
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    similarity_score=score,
                    matched_features=matched_features,
                    suggested_adaptations=self._suggest_adaptations(
                        requirement_features,
                        matched_features,
                        pattern,
                    ),
                )
                matches.append(match)
        
        # 유사도 순 정렬
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        
        return matches[:10]
    
    def get_templates_for_pattern(
        self,
        pattern_id: str,
    ) -> List[TemplateInfo]:
        """
        패턴에 대한 템플릿을 조회합니다.
        
        Args:
            pattern_id: 패턴 ID
        
        Returns:
            List[TemplateInfo]: 템플릿 목록
        """
        templates = []
        
        # Neo4j에서 검색
        if self.client.verify_connectivity():
            try:
                result = self.client.run_query(
                    FIND_TEMPLATES_FOR_PATTERN.query,
                    {"pattern_id": pattern_id}
                )
                for record in result:
                    template_data = dict(record["t"])
                    templates.append(TemplateInfo(
                        id=template_data.get("id", ""),
                        name=template_data.get("name", ""),
                        category=template_data.get("category", ""),
                        code_template=template_data.get("code", ""),
                        description=template_data.get("description", ""),
                    ))
            except Exception as e:
                self.logger.warning(f"템플릿 검색 실패: {e}")
        
        # 내장 템플릿 추가
        builtin_templates = self._get_builtin_templates(pattern_id)
        templates.extend(builtin_templates)
        
        return templates
    
    def record_pattern_usage(self, pattern_id: str) -> bool:
        """
        패턴 사용을 기록합니다.

        Args:
            pattern_id: 패턴 ID

        Returns:
            bool: 성공 여부
        """
        if not self.client.verify_connectivity():
            return False

        try:
            self.client.run_query(
                INCREMENT_PATTERN_USAGE.query,
                {"pattern_id": pattern_id}
            )
            return True
        except Exception as e:
            self.logger.error(f"패턴 사용 기록 실패: {e}")
            return False

    def save_pattern_with_template(
        self,
        pattern_id: str,
        name: str,
        description: str,
        use_case: str,
        version: str,
        template_id: str,
        language: str,
        code: str,
        variables: Optional[List[str]] = None,
    ) -> bool:
        """
        패턴과 코드 템플릿을 함께 생성합니다.

        Args:
            pattern_id: 패턴 ID
            name: 패턴 이름
            description: 설명
            use_case: 사용 사례
            version: 버전 (예: "1.0.0")
            template_id: 템플릿 ID
            language: 프로그래밍 언어
            code: 템플릿 코드
            variables: 템플릿 변수 목록

        Returns:
            bool: 성공 여부
        """
        if not self.client.verify_connectivity():
            self.logger.warning("Neo4j 연결 불가, 패턴 저장 실패")
            return False

        try:
            self.client.run_query(
                CREATE_PATTERN_WITH_TEMPLATE.query,
                {
                    "pattern_id": pattern_id,
                    "name": name,
                    "description": description,
                    "use_case": use_case,
                    "version": version,
                    "template_id": template_id,
                    "language": language,
                    "code": code,
                    "variables": variables or [],
                }
            )
            self.logger.info(f"패턴 및 템플릿 저장 성공: {pattern_id}")
            return True
        except Exception as e:
            self.logger.error(f"패턴 및 템플릿 저장 실패: {e}")
            return False

    def get_pattern_with_templates(
        self,
        pattern_id: str,
        version: Optional[str] = None,
    ) -> Optional[Tuple[AgentPattern, List[TemplateInfo]]]:
        """
        패턴과 관련 템플릿을 함께 조회합니다 (버전 지원).

        Args:
            pattern_id: 패턴 ID
            version: 특정 버전 (None이면 latest)

        Returns:
            Optional[Tuple[AgentPattern, List[TemplateInfo]]]: (패턴, 템플릿 목록)
        """
        if not self.client.verify_connectivity():
            return None

        try:
            result = self.client.run_query(
                GET_PATTERN_WITH_TEMPLATES.query,
                {"pattern_id": pattern_id, "version": version}
            )

            for record in result:
                pattern_data = dict(record["p"])
                pattern = self._record_to_pattern(pattern_data)

                templates = []
                if record.get("templates"):
                    for template_data in record["templates"]:
                        template_dict = dict(template_data)
                        templates.append(TemplateInfo(
                            id=template_dict.get("id", ""),
                            name=template_dict.get("name", ""),
                            category=template_dict.get("category", "code"),
                            code_template=template_dict.get("code", ""),
                            description=template_dict.get("description", ""),
                            parameters=template_dict.get("variables", []),
                        ))

                return (pattern, templates)

            return None
        except Exception as e:
            self.logger.error(f"패턴 조회 실패: {e}")
            return None

    def record_pattern_success(
        self,
        pattern_id: str,
        success: bool,
    ) -> bool:
        """
        패턴 사용 성공/실패를 기록합니다.

        Args:
            pattern_id: 패턴 ID
            success: 성공 여부

        Returns:
            bool: 기록 성공 여부
        """
        if not self.client.verify_connectivity():
            return False

        try:
            self.client.run_query(
                RECORD_PATTERN_SUCCESS.query,
                {"pattern_id": pattern_id, "success": success}
            )
            self.logger.info(f"패턴 성공 기록: {pattern_id} - {'성공' if success else '실패'}")
            return True
        except Exception as e:
            self.logger.error(f"패턴 성공 기록 실패: {e}")
            return False

    def get_pattern_recommendations(
        self,
        keyword: str,
        limit: int = 5,
    ) -> List[Tuple[AgentPattern, float, List[TemplateInfo]]]:
        """
        키워드 기반 패턴 추천 (성공률 가중치 적용).

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            List[Tuple[AgentPattern, float, List[TemplateInfo]]]:
                (패턴, 추천 점수, 템플릿 목록)
        """
        if not self.client.verify_connectivity():
            self.logger.warning("Neo4j 연결 불가, 내장 패턴 사용")
            return [(p, 0.5, self._get_builtin_templates(p.id))
                    for p in self._search_builtin_patterns("general", None, [keyword])[:limit]]

        try:
            result = self.client.run_query(
                GET_PATTERN_RECOMMENDATIONS.query,
                {"keyword": keyword, "limit": limit}
            )

            recommendations = []
            for record in result:
                pattern_data = dict(record["p"])
                pattern = self._record_to_pattern(pattern_data)
                score = record.get("recommendation_score", 0.0)

                templates = []
                if record.get("templates"):
                    for template_data in record["templates"]:
                        template_dict = dict(template_data)
                        templates.append(TemplateInfo(
                            id=template_dict.get("id", ""),
                            name=template_dict.get("name", ""),
                            category=template_dict.get("category", "code"),
                            code_template=template_dict.get("code", ""),
                            description=template_dict.get("description", ""),
                            parameters=template_dict.get("variables", []),
                        ))

                recommendations.append((pattern, score, templates))

            return recommendations
        except Exception as e:
            self.logger.error(f"패턴 추천 실패: {e}")
            return []

    def update_pattern_version(
        self,
        pattern_id: str,
        new_version: str,
        description: str,
    ) -> Optional[str]:
        """
        패턴의 새 버전을 생성합니다.

        Args:
            pattern_id: 기존 패턴 ID
            new_version: 새 버전 (예: "2.0.0")
            description: 새 버전 설명

        Returns:
            Optional[str]: 새 패턴 ID (성공 시)
        """
        if not self.client.verify_connectivity():
            return None

        try:
            new_pattern_id = f"{pattern_id}_v{new_version.replace('.', '_')}"

            result = self.client.run_query(
                UPDATE_PATTERN_VERSION.query,
                {
                    "pattern_id": pattern_id,
                    "new_pattern_id": new_pattern_id,
                    "version": new_version,
                    "description": description,
                }
            )

            if result:
                self.logger.info(f"패턴 버전 업데이트 성공: {pattern_id} -> {new_pattern_id}")
                return new_pattern_id

            return None
        except Exception as e:
            self.logger.error(f"패턴 버전 업데이트 실패: {e}")
            return None

    def get_pattern_history(
        self,
        pattern_name: str,
    ) -> List[AgentPattern]:
        """
        패턴의 버전 히스토리를 조회합니다.

        Args:
            pattern_name: 패턴 이름

        Returns:
            List[AgentPattern]: 버전별 패턴 목록 (최신 버전부터)
        """
        if not self.client.verify_connectivity():
            return []

        try:
            result = self.client.run_query(
                GET_PATTERN_HISTORY.query,
                {"pattern_name": pattern_name}
            )

            history = []
            for record in result:
                versions = record.get("versions", [])
                for version_data in versions:
                    pattern_dict = dict(version_data)
                    history.append(self._record_to_pattern(pattern_dict))

            return history
        except Exception as e:
            self.logger.error(f"패턴 히스토리 조회 실패: {e}")
            return []

    def deprecate_pattern(
        self,
        pattern_id: str,
        reason: str,
    ) -> bool:
        """
        패턴을 deprecated로 표시합니다.

        Args:
            pattern_id: 패턴 ID
            reason: deprecated 이유

        Returns:
            bool: 성공 여부
        """
        if not self.client.verify_connectivity():
            return False

        try:
            self.client.run_query(
                DEPRECATE_PATTERN.query,
                {"pattern_id": pattern_id, "reason": reason}
            )
            self.logger.info(f"패턴 deprecated 처리: {pattern_id}")
            return True
        except Exception as e:
            self.logger.error(f"패턴 deprecated 실패: {e}")
            return False
    
    def _calculate_similarity(
        self,
        requirement_features: List[str],
        pattern: AgentPattern,
    ) -> Tuple[float, List[str]]:
        """유사도 계산"""
        # 패턴의 특성들
        pattern_features = set()
        pattern_features.update(pattern.agent_roles)
        pattern_features.update(pattern.task_types)
        pattern_features.update(pattern.recommended_tools)
        pattern_features.add(pattern.domain)
        
        # 소문자로 정규화
        pattern_features = {f.lower() for f in pattern_features}
        req_features = {f.lower() for f in requirement_features}
        
        # 매칭되는 특성
        matched = pattern_features.intersection(req_features)
        
        # Jaccard 유사도
        union = pattern_features.union(req_features)
        if not union:
            return 0.0, []
        
        score = len(matched) / len(union)
        
        return round(score, 2), list(matched)
    
    def _suggest_adaptations(
        self,
        requirement_features: List[str],
        matched_features: List[str],
        pattern: AgentPattern,
    ) -> List[str]:
        """적응 제안 생성"""
        suggestions = []
        
        # 매칭되지 않은 요구사항 특성
        unmatched = set(f.lower() for f in requirement_features) - set(matched_features)
        
        if unmatched:
            suggestions.append(f"추가 기능 필요: {', '.join(list(unmatched)[:3])}")
        
        # 패턴의 추가 도구 제안
        if pattern.recommended_tools:
            suggestions.append(f"권장 도구: {', '.join(pattern.recommended_tools[:3])}")
        
        # 워크플로우 제안
        if pattern.workflow_type:
            suggestions.append(f"권장 워크플로우: {pattern.workflow_type}")
        
        return suggestions
    
    def _record_to_pattern(self, data: Dict) -> AgentPattern:
        """Neo4j 레코드를 패턴 객체로 변환"""
        return AgentPattern(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            pattern_type=data.get("pattern_type", PatternType.WORKFLOW),
            agent_roles=data.get("agent_roles", []),
            task_types=data.get("task_types", []),
            recommended_tools=data.get("recommended_tools", []),
            workflow_type=data.get("workflow_type", "sequential"),
            use_case=data.get("use_case", ""),
            usage_count=data.get("usage_count", 0),
            domain=data.get("domain", "general"),
        )
    
    def _load_builtin_patterns(self) -> List[AgentPattern]:
        """
        내장 패턴 로드 (Refactored: P1.2)

        Load patterns from external YAML file instead of hardcoded data.
        Reduces code from 379 lines to 3 lines (-97%).
        """
        from app.knowledge.graph.patterns_loader import load_builtin_patterns
        return load_builtin_patterns()
    
    def _search_builtin_patterns(
        self,
        domain: str,
        task_types: Optional[List[str]],
        keywords: Optional[List[str]],
    ) -> List[AgentPattern]:
        """내장 패턴에서 검색"""
        matches = []
        
        for pattern in self.builtin_patterns:
            score = 0
            
            # 도메인 매칭
            if pattern.domain == domain or pattern.domain == "general":
                score += 2
            
            # 태스크 유형 매칭
            if task_types:
                for task_type in task_types:
                    if task_type.lower() in [t.lower() for t in pattern.task_types]:
                        score += 1
            
            # 키워드 매칭
            if keywords:
                pattern_text = f"{pattern.name} {pattern.description} {pattern.use_case}".lower()
                for keyword in keywords:
                    if keyword.lower() in pattern_text:
                        score += 1
            
            if score > 0:
                matches.append((score, pattern))
        
        # 점수순 정렬
        matches.sort(key=lambda x: x[0], reverse=True)
        
        return [m[1] for m in matches]
    
    def _get_builtin_templates(self, pattern_id: str) -> List[TemplateInfo]:
        """내장 템플릿 조회"""
        templates_map = {
            "pattern_research_report": [
                TemplateInfo(
                    id="template_research_agent",
                    name="Research Agent Template",
                    category="agent",
                    description="Template for research-focused agent",
                    parameters=["topic", "sources", "depth"],
                ),
                TemplateInfo(
                    id="template_report_writer",
                    name="Report Writer Template",
                    category="agent",
                    description="Template for report writing agent",
                    parameters=["format", "length", "style"],
                ),
            ],
            "pattern_data_analysis": [
                TemplateInfo(
                    id="template_data_analyst",
                    name="Data Analyst Template",
                    category="agent",
                    description="Template for data analysis agent",
                    parameters=["data_type", "metrics", "visualizations"],
                ),
            ],
        }
        
        return templates_map.get(pattern_id, [])
