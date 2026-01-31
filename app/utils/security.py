"""
CAAS Security Utilities

입력 검증 및 보안 크리티컬 작업을 위한 새니타이제이션 유틸리티.
"""

import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union


class SecurityError(Exception):
    """보안 검증 오류"""
    pass


class PathTraversalError(SecurityError):
    """경로 탐색 시도 감지"""
    pass


class YAMLSecurityError(SecurityError):
    """YAML 보안 검증 오류"""
    pass


# ============================================================================
# 경로 탐색 공격 방어
# ============================================================================

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    파일명을 새니타이즈하여 경로 탐색 및 기타 공격 방지.

    Args:
        filename: 새니타이즈할 파일명
        max_length: 최대 파일명 길이

    Returns:
        str: 새니타이즈된 파일명

    Raises:
        PathTraversalError: 경로 탐색 감지 시
        ValueError: 파일명이 유효하지 않은 경우

    보안 조치:
    - 절대 경로 거부
    - 상위 디렉토리 참조 (..) 거부
    - Null 바이트 거부
    - 안전한 문자만 허용: a-z, A-Z, 0-9, _, -, .
    - 길이 제한 적용
    """
    if not filename:
        raise ValueError("파일명은 비어 있을 수 없습니다")

    # 특수 디렉토리 참조 거부
    if filename in ('.', '..', '...'):
        raise ValueError(f"특수 디렉토리 참조는 허용되지 않습니다: {filename}")

    # 경로 탐색 시도 감지
    if '..' in filename:
        raise PathTraversalError(f"파일명에 경로 탐색 감지됨: {filename}")

    # 절대 경로 거부
    if filename.startswith('/') or (len(filename) > 1 and filename[1] == ':'):
        raise PathTraversalError(f"절대 경로는 허용되지 않습니다: {filename}")

    # Null 바이트 거부
    if '\0' in filename:
        raise PathTraversalError("파일명에 Null 바이트 포함")

    # 디렉토리 구분자 거부 (단순 파일명의 경우)
    if '/' in filename or '\\' in filename:
        raise PathTraversalError(f"디렉토리 구분자는 허용되지 않습니다: {filename}")

    # 길이 확인
    if len(filename) > max_length:
        raise ValueError(f"파일명이 너무 깁니다 (최대 {max_length}자): {len(filename)}")

    # 안전한 문자만 허용
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise ValueError(f"파일명에 유효하지 않은 문자 포함: {filename}")

    return filename


def sanitize_path_component(component: str, max_length: int = 255) -> str:
    """
    단일 경로 컴포넌트(디렉토리/파일명) 새니타이즈.

    Args:
        component: 새니타이즈할 경로 컴포넌트
        max_length: 최대 컴포넌트 길이

    Returns:
        str: 새니타이즈된 컴포넌트

    Raises:
        PathTraversalError: 경로 탐색 감지 시
        ValueError: 컴포넌트가 유효하지 않은 경우

    보안 조치:
    - 상위 디렉토리 참조 거부
    - 현재 디렉토리 참조 거부
    - 안전한 문자만 허용: a-z, A-Z, 0-9, _, -
    - 길이 제한 적용
    """
    if not component:
        raise ValueError("경로 컴포넌트는 비어 있을 수 없습니다")

    # . 및 .. 거부 (경로 탐색 공격)
    if component in ('.', '..') or '..' in component or component.startswith('./') or component.startswith('../'):
        raise PathTraversalError(f"경로 탐색 시도 감지: {component}")

    # 길이 확인
    if len(component) > max_length:
        raise ValueError(f"경로 컴포넌트가 너무 깁니다 (최대 {max_length}자): {len(component)}")

    # 영숫자, 밑줄, 하이픈 허용 (snake_case, kebab-case, 파일 확장자, dotfiles 포함)
    # Pattern:
    #   - Dotfiles: .env.example, .gitignore, etc. (start with dot, then alphanumeric+underscore+dot)
    #   - Regular files: README.md, my_file-v2.txt, etc. (start with alphanumeric, then alphanumeric+underscore+hyphen+dot)
    # Allow dotfiles but NOT . or .. (those are checked above)
    if not re.match(r'^(\.[a-zA-Z][a-zA-Z0-9_\-\.]*|[a-zA-Z][a-zA-Z0-9_\-\.]*)$', component):
        raise ValueError(
            f"경로 컴포넌트는 유효한 파일명이어야 합니다 (dotfiles, snake_case, kebab-case, 파일 확장자 허용): {component}"
        )

    return component


def sanitize_relative_path(
    path: str,
    base_dir: Path,
    max_depth: int = 5,
) -> Path:
    """
    상대 경로를 새니타이즈하고 base_dir 내에 유지되도록 보장.

    Args:
        path: 새니타이즈할 상대 경로
        base_dir: 경로가 유지되어야 하는 기본 디렉토리
        max_depth: 최대 디렉토리 깊이

    Returns:
        Path: 절대 새니타이즈된 경로 (resolve된 base_dir 기준)

    Raises:
        PathTraversalError: 경로가 base_dir을 벗어나는 경우
        ValueError: 경로가 유효하지 않은 경우

    보안 조치:
    - 경로가 base_dir 내에서 resolve되도록 보장
    - 심볼릭 링크 공격 거부
    - 깊이 제한 적용
    - 모든 컴포넌트 검증
    """
    if not path:
        raise ValueError("경로는 비어 있을 수 없습니다")

    # 절대 경로 거부
    if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
        raise ValueError(f"절대 경로는 허용되지 않습니다: {path}")

    # base_dir을 먼저 resolve (symlink 해결)
    try:
        base_resolved = base_dir.resolve()
    except (OSError, RuntimeError) as e:
        raise PathTraversalError(f"기본 디렉토리가 유효하지 않습니다: {base_dir} ({e})")

    # 경로를 컴포넌트로 파싱
    parts = path.replace('\\', '/').split('/')
    # 빈 문자열 제거
    parts = [p for p in parts if p]

    # 깊이 확인 (디렉토리 깊이, 파일 제외하지 않음)
    # max_depth는 실제로 허용되는 컴포넌트 수를 의미
    # 예: max_depth=3이면 "level1/level2/level3/file.txt" (4 parts) 허용
    if len(parts) > max_depth + 1:
        raise ValueError(f"경로가 너무 깊습니다 (최대 {max_depth} 레벨): {len(parts) - 1}")

    # 각 컴포넌트 검증
    for part in parts:
        sanitize_path_component(part)

    # resolve된 base_dir을 기준으로 경로 구성
    sanitized = base_resolved
    for part in parts:
        sanitized = sanitized / part

    # 절대 경로로 resolve하고 base_dir 내에 있는지 확인
    try:
        # 파일이 존재하지 않아도 경로 검증은 가능하도록
        # strict=False를 사용하거나 수동으로 경로 검증
        # Python 3.10+에서는 resolve(strict=False)가 기본
        try:
            resolved = sanitized.resolve(strict=False)
        except TypeError:
            # Python 3.9 이하에서는 strict 파라미터가 없을 수 있음
            resolved = sanitized.resolve()

        # resolved 경로가 기본 디렉토리 내에 있는지 확인
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise PathTraversalError(
                f"경로가 기본 디렉토리를 벗어남: {path} -> {resolved}"
            )

        return resolved

    except (OSError, RuntimeError) as e:
        raise PathTraversalError(f"유효하지 않은 경로: {path} ({e})")


def validate_project_name(name: str) -> str:
    """
    프로젝트 이름 검증 및 새니타이즈.

    Args:
        name: 프로젝트 이름

    Returns:
        str: 새니타이즈된 프로젝트 이름

    Raises:
        ValueError: 이름이 유효하지 않은 경우

    요구사항:
    - snake_case여야 함
    - 길이: 3-64자
    - 문자로 시작
    - 소문자, 숫자, 밑줄만 허용
    """
    if not name:
        raise ValueError("프로젝트 이름은 비어 있을 수 없습니다")

    if len(name) < 3:
        raise ValueError(f"프로젝트 이름이 너무 짧습니다 (최소 3자): {len(name)}")

    if len(name) > 64:
        raise ValueError(f"프로젝트 이름이 너무 깁니다 (최대 64자): {len(name)}")

    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ValueError(
            f"프로젝트 이름은 snake_case여야 합니다 (소문자, 문자로 시작): {name}"
        )

    return name


# ============================================================================
# Cypher 인젝션 방어
# ============================================================================

def sanitize_neo4j_label(label: str) -> str:
    """
    Neo4j 노드 레이블을 새니타이즈하여 인젝션 방지.

    Args:
        label: 노드 레이블

    Returns:
        str: 새니타이즈된 레이블

    Raises:
        ValueError: 레이블이 유효하지 않은 경우

    보안 조치:
    - 영숫자 및 밑줄만 허용
    - 문자로 시작해야 함
    - 길이 제한: 1-64자
    - Neo4j 예약어 거부
    """
    if not label:
        raise ValueError("레이블은 비어 있을 수 없습니다")

    if len(label) > 64:
        raise ValueError(f"레이블이 너무 깁니다 (최대 64자): {len(label)}")

    # 레이블에 대한 안전한 문자만 허용
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', label):
        raise ValueError(
            f"레이블은 문자로 시작하고 영숫자/밑줄만 포함해야 합니다: {label}"
        )

    # Neo4j 예약어 거부
    reserved_words = {
        'ALL', 'AND', 'AS', 'ASC', 'ASCENDING', 'BY', 'CALL', 'CASE', 'COMMIT',
        'CONSTRAINT', 'CREATE', 'DELETE', 'DESC', 'DESCENDING', 'DETACH',
        'DISTINCT', 'DROP', 'ELSE', 'END', 'EXISTS', 'FOREACH', 'IN', 'INDEX',
        'IS', 'LIMIT', 'MATCH', 'MERGE', 'NOT', 'NULL', 'ON', 'OPTIONAL',
        'OR', 'ORDER', 'REMOVE', 'RETURN', 'SET', 'SKIP', 'THEN', 'UNION',
        'UNIQUE', 'UNWIND', 'WHEN', 'WHERE', 'WITH', 'XOR', 'YIELD',
    }

    if label.upper() in reserved_words:
        raise ValueError(f"레이블은 예약어일 수 없습니다: {label}")

    return label


def sanitize_neo4j_property_key(key: str) -> str:
    """
    Neo4j 속성 키를 새니타이즈하여 인젝션 방지.

    Args:
        key: 속성 키 이름

    Returns:
        str: 새니타이즈된 키

    Raises:
        ValueError: 키가 유효하지 않은 경우

    보안 조치:
    - 영숫자, 밑줄, 하이픈만 허용
    - 문자 또는 밑줄로 시작해야 함
    - 길이 제한: 1-64자
    """
    if not key:
        raise ValueError("속성 키는 비어 있을 수 없습니다")

    if len(key) > 64:
        raise ValueError(f"속성 키가 너무 깁니다 (최대 64자): {len(key)}")

    # 안전한 문자 허용
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\-]*$', key):
        raise ValueError(
            f"속성 키는 문자/밑줄로 시작해야 합니다: {key}"
        )

    return key


def sanitize_neo4j_relationship_type(rel_type: str) -> str:
    """
    Neo4j 관계 타입을 새니타이즈하여 인젝션 방지.

    Args:
        rel_type: 관계 타입

    Returns:
        str: 새니타이즈된 관계 타입

    Raises:
        ValueError: 관계 타입이 유효하지 않은 경우

    보안 조치:
    - 대문자와 밑줄만 허용
    - 문자로 시작해야 함
    - 길이 제한: 1-64자
    """
    if not rel_type:
        raise ValueError("관계 타입은 비어 있을 수 없습니다")

    if len(rel_type) > 64:
        raise ValueError(f"관계 타입이 너무 깁니다 (최대 64자): {len(rel_type)}")

    # 규칙: 관계 타입은 UPPERCASE_WITH_UNDERSCORES
    if not re.match(r'^[A-Z][A-Z0-9_]*$', rel_type):
        raise ValueError(
            f"관계 타입은 UPPERCASE_WITH_UNDERSCORES여야 합니다: {rel_type}"
        )

    return rel_type


def validate_cypher_limit(limit: int, max_limit: int = 10000) -> int:
    """
    LIMIT 절 값 검증.

    Args:
        limit: Limit 값
        max_limit: 허용되는 최대 limit

    Returns:
        int: 검증된 limit

    Raises:
        ValueError: limit이 유효하지 않은 경우
    """
    if not isinstance(limit, int):
        raise ValueError(f"Limit은 정수여야 하지만 {type(limit)}을(를) 받음")

    if limit < 1:
        raise ValueError(f"Limit은 양수여야 하지만 {limit}을(를) 받음")

    if limit > max_limit:
        raise ValueError(f"Limit이 너무 큽니다 (최대 {max_limit}), {limit}을(를) 받음")

    return limit


# ============================================================================
# YAML Bomb 방어
# ============================================================================

def validate_yaml_size(
    yaml_content: str,
    max_size: int = 1_000_000,  # 1MB
    max_lines: int = 10_000,
) -> None:
    """
    YAML 컨텐츠 크기 제한 검증.

    Args:
        yaml_content: 검증할 YAML 컨텐츠
        max_size: 최대 크기(바이트)
        max_lines: 최대 라인 수

    Raises:
        YAMLSecurityError: 크기 제한 초과 시

    보안 조치:
    - 대용량 파일 DoS 방지
    - 라인 수 제한
    - 과도한 중첩 확인
    """
    if not yaml_content:
        raise ValueError("YAML 컨텐츠는 비어 있을 수 없습니다")

    # 바이트 크기 확인
    content_size = len(yaml_content.encode('utf-8'))
    if content_size > max_size:
        raise YAMLSecurityError(
            f"YAML이 너무 큽니다 ({content_size} 바이트, 최대 {max_size})"
        )

    # 라인 수 확인
    line_count = yaml_content.count('\n') + 1
    if line_count > max_lines:
        raise YAMLSecurityError(
            f"YAML에 라인이 너무 많습니다 ({line_count}, 최대 {max_lines})"
        )


def safe_yaml_load(
    yaml_content: str,
    max_size: int = 1_000_000,
    max_depth: int = 10,
) -> dict:
    """
    보안 검사와 함께 안전하게 YAML 로드.

    Args:
        yaml_content: 파싱할 YAML 컨텐츠
        max_size: 최대 컨텐츠 크기(바이트)
        max_depth: 최대 중첩 깊이

    Returns:
        dict: 파싱된 YAML 데이터

    Raises:
        YAMLSecurityError: 보안 검사 실패 시
        ValueError: YAML이 유효하지 않은 경우

    보안 조치:
    - 크기 제한
    - 깊이 제한
    - 복잡도 제한
    - Safe loader만 사용
    """
    # 크기 검증
    validate_yaml_size(yaml_content, max_size=max_size)

    # safe_load로 파싱 (코드 실행에 대해 이미 안전함)
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"유효하지 않은 YAML: {e}")

    if data is None:
        raise ValueError("YAML 컨텐츠가 비어 있거나 null입니다")

    if not isinstance(data, dict):
        raise ValueError("YAML 루트는 딕셔너리여야 합니다")

    # 깊이 검증
    actual_depth = _get_nested_depth(data)
    if actual_depth > max_depth:
        raise YAMLSecurityError(
            f"YAML이 너무 깊게 중첩됨 ({actual_depth}, 최대 {max_depth})"
        )

    # 복잡도 검증
    node_count = _count_nodes(data)
    max_nodes = 10_000
    if node_count > max_nodes:
        raise YAMLSecurityError(
            f"YAML이 너무 복잡함 ({node_count} 노드, 최대 {max_nodes})"
        )

    return data


def _get_nested_depth(obj: Any, current_depth: int = 0) -> int:
    """중첩 구조의 최대 중첩 깊이 계산."""
    if not isinstance(obj, (dict, list)):
        return current_depth

    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(
            _get_nested_depth(v, current_depth + 1)
            for v in obj.values()
        )

    if isinstance(obj, list):
        if not obj:
            return current_depth
        return max(
            _get_nested_depth(item, current_depth + 1)
            for item in obj
        )

    return current_depth


def _count_nodes(obj: Any) -> int:
    """중첩 구조의 총 노드 수 계산."""
    if isinstance(obj, dict):
        return 1 + sum(_count_nodes(v) for v in obj.values())
    elif isinstance(obj, list):
        return 1 + sum(_count_nodes(item) for item in obj)
    else:
        return 1


# ============================================================================
# 프롬프트 인젝션 방어
# ============================================================================

class PromptInjectionError(SecurityError):
    """프롬프트 인젝션 시도 감지"""
    pass


def sanitize_user_input(user_input: str, max_length: int = 10000) -> str:
    """
    사용자 입력 새니타이제이션 (프롬프트 인젝션 방지)

    Args:
        user_input: 원본 입력
        max_length: 최대 길이

    Returns:
        새니타이즈된 입력

    보안 조치:
    - 길이 제한
    - 프롬프트 템플릿 변수 이스케이프
    - 특수 토큰 제거
    """
    if not user_input:
        return ""

    # 1. 길이 제한
    sanitized = user_input[:max_length]

    # 2. 프롬프트 템플릿 변수 이스케이프 ({variable} 형태)
    sanitized = sanitized.replace("{", "{{").replace("}", "}}")

    # 3. LLM 특수 토큰 제거
    special_tokens = [
        "<|im_start|>", "<|im_end|>",  # ChatML
        "[INST]", "[/INST]",            # Llama
        "<s>", "</s>",                   # 일반 토큰
        "###", "Assistant:", "Human:",  # 일반 프롬프트 패턴
    ]
    for token in special_tokens:
        sanitized = sanitized.replace(token, "")

    return sanitized


def detect_prompt_injection(user_input: str) -> Optional[str]:
    """
    프롬프트 인젝션 시도 감지

    Args:
        user_input: 검사할 입력

    Returns:
        감지된 패턴 또는 None

    감지 패턴:
    - "ignore previous instructions"
    - "system: you are"
    - 시스템 프롬프트 오버라이드 시도
    - 과도한 특수문자
    """
    if not user_input:
        return None

    user_input_lower = user_input.lower()

    # 위험한 패턴
    dangerous_patterns = [
        r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
        r"disregard\s+(previous|all)",
        r"forget\s+(everything|all|previous)",
        r"system\s*:\s*(you are|act as)",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, user_input_lower, re.IGNORECASE):
            return f"Dangerous pattern: {pattern}"

    # 시스템 프롬프트 오버라이드 시도
    if re.search(r"(you are|act as|pretend to be).{0,50}(system|admin|root|assistant)", user_input_lower):
        return "System override attempt"

    # 과도한 특수문자 (난독화 시도)
    if len(user_input) > 0:
        special_char_ratio = sum(not c.isalnum() and not c.isspace() for c in user_input) / len(user_input)
        if special_char_ratio > 0.4:
            return "Excessive special characters"

    return None


def validate_requirement(requirement: str) -> tuple[bool, str]:
    """
    요구사항 유효성 검증

    Args:
        requirement: 요구사항 텍스트

    Returns:
        (is_valid, error_message)

    검증 항목:
    - 길이 (10자 ~ 10000자)
    - 프롬프트 인젝션 패턴
    - 최소 내용 (5단어 이상)
    - 반복 감지
    """
    # 1. 길이 체크
    if len(requirement) < 10:
        return False, "요구사항이 너무 짧습니다 (최소 10자)"

    if len(requirement) > 10000:
        return False, "요구사항이 너무 깁니다 (최대 10000자)"

    # 2. 프롬프트 인젝션 감지
    injection_pattern = detect_prompt_injection(requirement)
    if injection_pattern:
        return False, f"프롬프트 인젝션 시도 감지: {injection_pattern}"

    # 3. 최소 내용 검증
    words = requirement.split()
    if len(words) < 5:
        return False, "요구사항이 너무 짧습니다 (최소 5단어)"

    # 4. 반복 감지 (한글 지원: 2자 이상 단어 포함)
    # 한글은 대부분 2-3자 단어이므로 길이 필터를 완화
    unique_words = set(word.lower() for word in words if len(word) > 1)
    # 임계값을 40%로 조정 (스팸 차단 + 자연스러운 도메인 용어 반복 허용)
    if len(unique_words) < len(words) * 0.4:
        return False, "반복적인 내용이 과도합니다"

    return True, ""


def escape_for_prompt(text: str) -> str:
    """
    프롬프트에 안전하게 삽입할 수 있도록 이스케이프

    Args:
        text: 원본 텍스트

    Returns:
        이스케이프된 텍스트

    이스케이프 대상:
    - XML 태그 (<, >)
    - 백슬래시
    - 따옴표
    """
    # XML 태그 이스케이프
    text = text.replace("<", "&lt;").replace(">", "&gt;")

    # 백슬래시 이스케이프
    text = text.replace("\\", "\\\\")

    # 따옴표 이스케이프
    text = text.replace('"', '\\"').replace("'", "\\'")

    return text
