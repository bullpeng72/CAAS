"""
Knowledge Graph Cypher Queries

Neo4j용 Cypher 쿼리 모음입니다.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class QueryTemplate:
    """쿼리 템플릿"""

    name: str
    description: str
    query: str
    parameters: List[str]


# =============================================================================
# Agent 관련 쿼리
# =============================================================================

FIND_AGENT_BY_ROLE = QueryTemplate(
    name="find_agent_by_role",
    description="역할로 에이전트 검색",
    query="""
    MATCH (a:Agent)
    WHERE a.role CONTAINS $role
    RETURN a
    ORDER BY a.name
    LIMIT $limit
    """,
    parameters=["role", "limit"],
)

FIND_AGENTS_IN_DOMAIN = QueryTemplate(
    name="find_agents_in_domain",
    description="도메인에 속한 에이전트 검색",
    query="""
    MATCH (a:Agent)-[:BELONGS_TO]->(d:Domain)
    WHERE d.name = $domain
    RETURN a
    ORDER BY a.name
    """,
    parameters=["domain"],
)

CREATE_AGENT = QueryTemplate(
    name="create_agent",
    description="에이전트 생성",
    query="""
    CREATE (a:Agent {
        id: $id,
        name: $name,
        role: $role,
        goal: $goal,
        backstory: $backstory,
        created_at: datetime()
    })
    RETURN a
    """,
    parameters=["id", "name", "role", "goal", "backstory"],
)

# =============================================================================
# Task 관련 쿼리
# =============================================================================

FIND_TASKS_BY_TYPE = QueryTemplate(
    name="find_tasks_by_type",
    description="유형으로 태스크 검색",
    query="""
    MATCH (t:Task)
    WHERE t.type = $task_type
    RETURN t
    ORDER BY t.name
    """,
    parameters=["task_type"],
)

FIND_TASKS_FOR_AGENT = QueryTemplate(
    name="find_tasks_for_agent",
    description="에이전트에 할당된 태스크 검색",
    query="""
    MATCH (a:Agent)-[:PERFORMS]->(t:Task)
    WHERE a.id = $agent_id
    RETURN t
    ORDER BY t.priority DESC
    """,
    parameters=["agent_id"],
)

CREATE_TASK = QueryTemplate(
    name="create_task",
    description="태스크 생성",
    query="""
    CREATE (t:Task {
        id: $id,
        name: $name,
        description: $description,
        expected_output: $expected_output,
        type: $type,
        created_at: datetime()
    })
    RETURN t
    """,
    parameters=["id", "name", "description", "expected_output", "type"],
)

# =============================================================================
# Tool 관련 쿼리
# =============================================================================

FIND_TOOLS_BY_CAPABILITY = QueryTemplate(
    name="find_tools_by_capability",
    description="기능으로 도구 검색",
    query="""
    MATCH (tool:Tool)-[:HAS_CAPABILITY]->(c:Capability)
    WHERE c.name = $capability
    RETURN tool
    ORDER BY tool.name
    """,
    parameters=["capability"],
)

FIND_TOOLS_FOR_TASK = QueryTemplate(
    name="find_tools_for_task",
    description="태스크에 필요한 도구 검색",
    query="""
    MATCH (t:Task)-[:REQUIRES]->(tool:Tool)
    WHERE t.id = $task_id
    RETURN tool
    """,
    parameters=["task_id"],
)

# =============================================================================
# Pattern 관련 쿼리
# =============================================================================

FIND_PATTERNS_BY_DOMAIN = QueryTemplate(
    name="find_patterns_by_domain",
    description="도메인에 적용 가능한 패턴 검색",
    query="""
    MATCH (p:Pattern)-[:APPLIES_TO]->(d:Domain)
    WHERE d.name = $domain
    RETURN p
    ORDER BY p.usage_count DESC
    LIMIT $limit
    """,
    parameters=["domain", "limit"],
)

FIND_SIMILAR_PATTERNS = QueryTemplate(
    name="find_similar_patterns",
    description="유사한 패턴 검색",
    query="""
    MATCH (p:Pattern)
    WHERE p.description CONTAINS $keyword
       OR p.name CONTAINS $keyword
    RETURN p
    ORDER BY p.usage_count DESC
    LIMIT $limit
    """,
    parameters=["keyword", "limit"],
)

CREATE_PATTERN = QueryTemplate(
    name="create_pattern",
    description="패턴 생성",
    query="""
    CREATE (p:Pattern {
        id: $id,
        name: $name,
        description: $description,
        use_case: $use_case,
        usage_count: 0,
        created_at: datetime()
    })
    RETURN p
    """,
    parameters=["id", "name", "description", "use_case"],
)

INCREMENT_PATTERN_USAGE = QueryTemplate(
    name="increment_pattern_usage",
    description="패턴 사용 횟수 증가",
    query="""
    MATCH (p:Pattern)
    WHERE p.id = $pattern_id
    SET p.usage_count = p.usage_count + 1,
        p.last_used = datetime()
    RETURN p
    """,
    parameters=["pattern_id"],
)

# =============================================================================
# Template 관련 쿼리
# =============================================================================

FIND_TEMPLATES_FOR_PATTERN = QueryTemplate(
    name="find_templates_for_pattern",
    description="패턴에 대한 템플릿 검색",
    query="""
    MATCH (t:Template)-[:IMPLEMENTS]->(p:Pattern)
    WHERE p.id = $pattern_id
    RETURN t
    ORDER BY t.rating DESC
    """,
    parameters=["pattern_id"],
)

FIND_TEMPLATES_BY_CATEGORY = QueryTemplate(
    name="find_templates_by_category",
    description="카테고리별 템플릿 검색",
    query="""
    MATCH (t:Template)
    WHERE t.category = $category
    RETURN t
    ORDER BY t.usage_count DESC
    LIMIT $limit
    """,
    parameters=["category", "limit"],
)

# =============================================================================
# Relationship 관련 쿼리
# =============================================================================

LINK_AGENT_TO_TASK = QueryTemplate(
    name="link_agent_to_task",
    description="에이전트-태스크 관계 생성",
    query="""
    MATCH (a:Agent), (t:Task)
    WHERE a.id = $agent_id AND t.id = $task_id
    CREATE (a)-[r:PERFORMS]->(t)
    RETURN r
    """,
    parameters=["agent_id", "task_id"],
)

LINK_AGENT_TO_TOOL = QueryTemplate(
    name="link_agent_to_tool",
    description="에이전트-도구 관계 생성",
    query="""
    MATCH (a:Agent), (tool:Tool)
    WHERE a.id = $agent_id AND tool.id = $tool_id
    CREATE (a)-[r:USES]->(tool)
    RETURN r
    """,
    parameters=["agent_id", "tool_id"],
)

LINK_TASK_TO_TOOL = QueryTemplate(
    name="link_task_to_tool",
    description="태스크-도구 관계 생성",
    query="""
    MATCH (t:Task), (tool:Tool)
    WHERE t.id = $task_id AND tool.id = $tool_id
    CREATE (t)-[r:REQUIRES]->(tool)
    RETURN r
    """,
    parameters=["task_id", "tool_id"],
)

LINK_TASK_DEPENDENCY = QueryTemplate(
    name="link_task_dependency",
    description="태스크 의존성 관계 생성",
    query="""
    MATCH (t1:Task), (t2:Task)
    WHERE t1.id = $task_id AND t2.id = $depends_on_id
    CREATE (t1)-[r:DEPENDS_ON]->(t2)
    RETURN r
    """,
    parameters=["task_id", "depends_on_id"],
)

LINK_AGENT_TO_DOMAIN = QueryTemplate(
    name="link_agent_to_domain",
    description="에이전트-도메인 관계 생성",
    query="""
    MATCH (a:Agent), (d:Domain)
    WHERE a.id = $agent_id AND d.name = $domain
    CREATE (a)-[r:BELONGS_TO]->(d)
    RETURN r
    """,
    parameters=["agent_id", "domain"],
)

# =============================================================================
# Graph Analysis 쿼리
# =============================================================================

GET_AGENT_TASK_GRAPH = QueryTemplate(
    name="get_agent_task_graph",
    description="에이전트-태스크 그래프 조회",
    query="""
    MATCH (a:Agent)-[r:PERFORMS]->(t:Task)
    RETURN a, r, t
    LIMIT $limit
    """,
    parameters=["limit"],
)

GET_FULL_WORKFLOW = QueryTemplate(
    name="get_full_workflow",
    description="전체 워크플로우 조회",
    query="""
    MATCH path = (a:Agent)-[:PERFORMS]->(t:Task)-[:DEPENDS_ON*0..]->(dep:Task)
    WHERE a.id IN $agent_ids
    RETURN path
    """,
    parameters=["agent_ids"],
)

GET_DOMAIN_STATISTICS = QueryTemplate(
    name="get_domain_statistics",
    description="도메인별 통계",
    query="""
    MATCH (d:Domain)
    OPTIONAL MATCH (a:Agent)-[:BELONGS_TO]->(d)
    OPTIONAL MATCH (p:Pattern)-[:APPLIES_TO]->(d)
    RETURN d.name AS domain,
           count(DISTINCT a) AS agent_count,
           count(DISTINCT p) AS pattern_count
    ORDER BY agent_count DESC
    """,
    parameters=[],
)

# =============================================================================
# Advanced Pattern Queries (Versioning & Success Tracking)
# =============================================================================

CREATE_PATTERN_WITH_TEMPLATE = QueryTemplate(
    name="create_pattern_with_template",
    description="패턴과 코드 템플릿을 함께 생성",
    query="""
    CREATE (p:Pattern {
        id: $pattern_id,
        name: $name,
        description: $description,
        use_case: $use_case,
        version: $version,
        latest: true,
        usage_count: 0,
        success_count: 0,
        failure_count: 0,
        created_at: datetime()
    })
    CREATE (ct:CodeTemplate {
        id: $template_id,
        language: $language,
        code: $code,
        variables: $variables,
        created_at: datetime()
    })
    CREATE (p)-[:HAS_TEMPLATE]->(ct)
    RETURN p, ct
    """,
    parameters=[
        "pattern_id",
        "name",
        "description",
        "use_case",
        "version",
        "template_id",
        "language",
        "code",
        "variables",
    ],
)

UPDATE_PATTERN_VERSION = QueryTemplate(
    name="update_pattern_version",
    description="패턴 새 버전 생성 및 이전 버전 링크",
    query="""
    MATCH (old:Pattern {id: $pattern_id, latest: true})
    SET old.latest = false
    CREATE (new:Pattern {
        id: $new_pattern_id,
        name: old.name,
        description: $description,
        use_case: old.use_case,
        version: $version,
        latest: true,
        usage_count: 0,
        success_count: 0,
        failure_count: 0,
        created_at: datetime()
    })
    CREATE (new)-[:PREVIOUS_VERSION]->(old)
    RETURN new, old
    """,
    parameters=["pattern_id", "new_pattern_id", "description", "version"],
)

FIND_LATEST_PATTERN = QueryTemplate(
    name="find_latest_pattern",
    description="최신 버전의 패턴 조회",
    query="""
    MATCH (p:Pattern {latest: true})
    WHERE p.name = $pattern_name
    OPTIONAL MATCH (p)-[:HAS_TEMPLATE]->(ct:CodeTemplate)
    RETURN p, collect(ct) as templates
    """,
    parameters=["pattern_name"],
)

RECORD_PATTERN_SUCCESS = QueryTemplate(
    name="record_pattern_success",
    description="패턴 사용 성공 기록",
    query="""
    MATCH (p:Pattern)
    WHERE p.id = $pattern_id
    SET p.usage_count = p.usage_count + 1,
        p.success_count = p.success_count + CASE WHEN $success THEN 1 ELSE 0 END,
        p.failure_count = p.failure_count + CASE WHEN $success THEN 0 ELSE 1 END,
        p.last_used = datetime(),
        p.success_rate = toFloat(p.success_count + CASE WHEN $success THEN 1 ELSE 0 END) /
                        toFloat(p.usage_count + 1)
    RETURN p
    """,
    parameters=["pattern_id", "success"],
)

GET_PATTERN_RECOMMENDATIONS = QueryTemplate(
    name="get_pattern_recommendations",
    description="유사도 및 성공률 기반 패턴 추천",
    query="""
    MATCH (p:Pattern {latest: true})
    WHERE p.description CONTAINS $keyword
       OR p.name CONTAINS $keyword
       OR p.use_case CONTAINS $keyword
    WITH p,
         CASE
            WHEN p.name CONTAINS $keyword THEN 3
            WHEN p.description CONTAINS $keyword THEN 2
            ELSE 1
         END as name_score,
         CASE
            WHEN p.usage_count > 10 THEN p.success_rate * 2
            WHEN p.usage_count > 5 THEN p.success_rate * 1.5
            ELSE p.success_rate
         END as weighted_success_rate
    WITH p, (name_score + weighted_success_rate) as recommendation_score
    ORDER BY recommendation_score DESC, p.usage_count DESC
    LIMIT $limit
    OPTIONAL MATCH (p)-[:HAS_TEMPLATE]->(ct:CodeTemplate)
    RETURN p, collect(ct) as templates, recommendation_score
    """,
    parameters=["keyword", "limit"],
)

FIND_PATTERNS_BY_ONTOLOGY = QueryTemplate(
    name="find_patterns_by_ontology",
    description="온톨로지 기반 의미적 패턴 검색",
    query="""
    MATCH (p:Pattern {latest: true})-[:APPLIES_TO]->(d:Domain)
    WHERE d.name = $domain
    OPTIONAL MATCH (p)-[:REQUIRES]->(c:Capability)
    WHERE c.name IN $required_capabilities
    WITH p, count(DISTINCT c) as capability_matches
    OPTIONAL MATCH (p)-[:USES_TOOL]->(t:Tool)
    WHERE t.id IN $available_tools
    WITH p, capability_matches, count(DISTINCT t) as tool_matches
    WHERE capability_matches > 0 OR tool_matches > 0
    RETURN p,
           (capability_matches * 2 + tool_matches) as ontology_score,
           p.success_rate as success_rate
    ORDER BY ontology_score DESC, success_rate DESC
    LIMIT $limit
    """,
    parameters=["domain", "required_capabilities", "available_tools", "limit"],
)

GET_WORKFLOW_OPTIMIZATION = QueryTemplate(
    name="get_workflow_optimization",
    description="워크플로우 분석 및 최적화 패턴 제안",
    query="""
    MATCH (a:Agent)-[:PERFORMS]->(t:Task)
    WHERE a.id IN $agent_ids
    WITH collect(DISTINCT t.type) as task_types,
         count(DISTINCT a) as agent_count,
         count(DISTINCT t) as task_count
    MATCH (p:Pattern {latest: true})
    WHERE any(tt IN task_types WHERE p.description CONTAINS tt)
    WITH p,
         size([tt IN task_types WHERE p.description CONTAINS tt]) as type_match_count,
         task_types,
         agent_count,
         task_count
    WITH p,
         (toFloat(type_match_count) / size(task_types)) as workflow_match_score,
         CASE
            WHEN agent_count <= 3 AND p.name CONTAINS 'simple' THEN 1.2
            WHEN agent_count > 5 AND p.name CONTAINS 'complex' THEN 1.2
            ELSE 1.0
         END as complexity_bonus
    WHERE workflow_match_score > 0.3
    RETURN p,
           (workflow_match_score * complexity_bonus * p.success_rate) as optimization_score
    ORDER BY optimization_score DESC
    LIMIT $limit
    """,
    parameters=["agent_ids", "limit"],
)

# =============================================================================
# Code Template Queries
# =============================================================================

CREATE_CODE_TEMPLATE = QueryTemplate(
    name="create_code_template",
    description="코드 템플릿 생성",
    query="""
    CREATE (ct:CodeTemplate {
        id: $id,
        language: $language,
        code: $code,
        variables: $variables,
        description: $description,
        created_at: datetime()
    })
    RETURN ct
    """,
    parameters=["id", "language", "code", "variables", "description"],
)

LINK_TEMPLATE_TO_PATTERN = QueryTemplate(
    name="link_template_to_pattern",
    description="템플릿을 패턴에 연결",
    query="""
    MATCH (ct:CodeTemplate), (p:Pattern)
    WHERE ct.id = $template_id AND p.id = $pattern_id
    CREATE (p)-[r:HAS_TEMPLATE]->(ct)
    RETURN r
    """,
    parameters=["template_id", "pattern_id"],
)

FIND_TEMPLATES_BY_LANGUAGE = QueryTemplate(
    name="find_templates_by_language",
    description="언어별 코드 템플릿 검색",
    query="""
    MATCH (ct:CodeTemplate)
    WHERE ct.language = $language
    OPTIONAL MATCH (p:Pattern)-[:HAS_TEMPLATE]->(ct)
    RETURN ct, p
    ORDER BY p.usage_count DESC
    LIMIT $limit
    """,
    parameters=["language", "limit"],
)

GET_PATTERN_WITH_TEMPLATES = QueryTemplate(
    name="get_pattern_with_templates",
    description="패턴과 모든 템플릿 함께 조회",
    query="""
    MATCH (p:Pattern)
    WHERE p.id = $pattern_id AND (p.version = $version OR $version IS NULL)
    OPTIONAL MATCH (p)-[:HAS_TEMPLATE]->(ct:CodeTemplate)
    RETURN p, collect(ct) as templates
    """,
    parameters=["pattern_id", "version"],
)

# =============================================================================
# Pattern Lifecycle Queries
# =============================================================================

GET_PATTERN_HISTORY = QueryTemplate(
    name="get_pattern_history",
    description="패턴 버전 히스토리 조회",
    query="""
    MATCH path = (latest:Pattern {latest: true})-[:PREVIOUS_VERSION*0..]->(old:Pattern)
    WHERE latest.name = $pattern_name
    RETURN nodes(path) as versions
    ORDER BY latest.version DESC
    """,
    parameters=["pattern_name"],
)

GET_PATTERN_USAGE_STATS = QueryTemplate(
    name="get_pattern_usage_stats",
    description="패턴 사용 통계 조회",
    query="""
    MATCH (p:Pattern)
    WHERE p.id = $pattern_id
    RETURN p.usage_count as usage_count,
           p.success_count as success_count,
           p.failure_count as failure_count,
           p.success_rate as success_rate,
           p.last_used as last_used,
           p.created_at as created_at
    """,
    parameters=["pattern_id"],
)

DEPRECATE_PATTERN = QueryTemplate(
    name="deprecate_pattern",
    description="패턴을 deprecated로 표시",
    query="""
    MATCH (p:Pattern)
    WHERE p.id = $pattern_id
    SET p.deprecated = true,
        p.deprecated_at = datetime(),
        p.deprecated_reason = $reason,
        p.latest = false
    RETURN p
    """,
    parameters=["pattern_id", "reason"],
)

# =============================================================================
# Query Collections
# =============================================================================

AGENT_QUERIES = {
    "find_by_role": FIND_AGENT_BY_ROLE,
    "find_in_domain": FIND_AGENTS_IN_DOMAIN,
    "create": CREATE_AGENT,
}

TASK_QUERIES = {
    "find_by_type": FIND_TASKS_BY_TYPE,
    "find_for_agent": FIND_TASKS_FOR_AGENT,
    "create": CREATE_TASK,
}

TOOL_QUERIES = {
    "find_by_capability": FIND_TOOLS_BY_CAPABILITY,
    "find_for_task": FIND_TOOLS_FOR_TASK,
}

PATTERN_QUERIES = {
    "find_by_domain": FIND_PATTERNS_BY_DOMAIN,
    "find_similar": FIND_SIMILAR_PATTERNS,
    "create": CREATE_PATTERN,
    "increment_usage": INCREMENT_PATTERN_USAGE,
    # Advanced pattern queries
    "create_with_template": CREATE_PATTERN_WITH_TEMPLATE,
    "update_version": UPDATE_PATTERN_VERSION,
    "find_latest": FIND_LATEST_PATTERN,
    "record_success": RECORD_PATTERN_SUCCESS,
    "get_recommendations": GET_PATTERN_RECOMMENDATIONS,
    "find_by_ontology": FIND_PATTERNS_BY_ONTOLOGY,
    "get_workflow_optimization": GET_WORKFLOW_OPTIMIZATION,
}

TEMPLATE_QUERIES = {
    "find_for_pattern": FIND_TEMPLATES_FOR_PATTERN,
    "find_by_category": FIND_TEMPLATES_BY_CATEGORY,
    # Advanced template queries
    "create": CREATE_CODE_TEMPLATE,
    "link_to_pattern": LINK_TEMPLATE_TO_PATTERN,
    "find_by_language": FIND_TEMPLATES_BY_LANGUAGE,
    "get_with_pattern": GET_PATTERN_WITH_TEMPLATES,
}

LIFECYCLE_QUERIES = {
    "get_history": GET_PATTERN_HISTORY,
    "get_usage_stats": GET_PATTERN_USAGE_STATS,
    "deprecate": DEPRECATE_PATTERN,
}

RELATIONSHIP_QUERIES = {
    "agent_task": LINK_AGENT_TO_TASK,
    "agent_tool": LINK_AGENT_TO_TOOL,
    "task_tool": LINK_TASK_TO_TOOL,
    "task_dependency": LINK_TASK_DEPENDENCY,
    "agent_domain": LINK_AGENT_TO_DOMAIN,
}

ANALYSIS_QUERIES = {
    "agent_task_graph": GET_AGENT_TASK_GRAPH,
    "full_workflow": GET_FULL_WORKFLOW,
    "domain_statistics": GET_DOMAIN_STATISTICS,
}


def get_query(category: str, name: str) -> Optional[QueryTemplate]:
    """
    카테고리와 이름으로 쿼리 템플릿을 조회합니다.

    Args:
        category: 쿼리 카테고리 (agent, task, tool, pattern, template, lifecycle, relationship, analysis)
        name: 쿼리 이름

    Returns:
        Optional[QueryTemplate]: 쿼리 템플릿
    """
    collections = {
        "agent": AGENT_QUERIES,
        "task": TASK_QUERIES,
        "tool": TOOL_QUERIES,
        "pattern": PATTERN_QUERIES,
        "template": TEMPLATE_QUERIES,
        "lifecycle": LIFECYCLE_QUERIES,
        "relationship": RELATIONSHIP_QUERIES,
        "analysis": ANALYSIS_QUERIES,
    }

    collection = collections.get(category)
    if collection:
        return collection.get(name)
    return None
