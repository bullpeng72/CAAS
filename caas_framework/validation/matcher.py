"""
Feature Matching Algorithms

Golden Data와 Phase Output 간의 항목 매칭을 위한 알고리즘
"""

from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from caas_framework.utils.logger import get_logger

logger = get_logger("validation.matcher")


class FeatureMatcher:
    """
    Feature Matching 알고리즘

    Golden Data의 Features와 Output의 Tasks/Components를 매칭합니다.

    Matching Strategies:
    1. Exact Match: ID 또는 이름이 정확히 일치
    2. Fuzzy Match: 텍스트 유사도 기반 매칭 (SequenceMatcher)
    3. Semantic Match: LLM 기반 의미적 유사도 (optional)
    """

    def __init__(self, fuzzy_threshold: float = 0.6):
        """
        Args:
            fuzzy_threshold: Fuzzy matching 임계값 (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold

    def exact_match(self, golden_name: str, output_names: List[str]) -> Optional[str]:
        """
        정확한 매칭 (대소문자 무시)

        Args:
            golden_name: Golden Data의 항목 이름
            output_names: Output의 항목 이름 리스트

        Returns:
            매칭된 output 이름 또는 None
        """
        golden_lower = golden_name.lower().strip()

        for output_name in output_names:
            if output_name.lower().strip() == golden_lower:
                return output_name

        return None

    def fuzzy_match(
        self,
        golden_name: str,
        output_names: List[str],
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[str, float]]:
        """
        유사도 기반 매칭

        Args:
            golden_name: Golden Data의 항목 이름
            output_names: Output의 항목 이름 리스트
            threshold: 매칭 임계값 (None이면 기본값 사용)

        Returns:
            (매칭된 output 이름, 유사도) 튜플 또는 None
        """
        threshold = threshold or self.fuzzy_threshold
        golden_lower = golden_name.lower().strip()

        best_match = None
        best_score = 0.0

        for output_name in output_names:
            output_lower = output_name.lower().strip()

            # SequenceMatcher를 사용한 유사도 계산
            similarity = SequenceMatcher(None, golden_lower, output_lower).ratio()

            # 부분 문자열 포함 여부도 확인
            if golden_lower in output_lower or output_lower in golden_lower:
                similarity = max(similarity, 0.8)  # 부분 포함 시 최소 0.8 점수

            if similarity > best_score:
                best_score = similarity
                best_match = output_name

        if best_score >= threshold:
            return (best_match, best_score)

        return None

    def match_features_to_tasks(
        self, golden_features: List[str], output_tasks: List[str]
    ) -> dict:
        """
        Golden Features를 Output Tasks에 매칭

        Args:
            golden_features: Golden Data의 feature 이름 리스트
            output_tasks: Output의 task 이름 리스트

        Returns:
            dict: {
                "matched": [(golden_name, output_name, score), ...],
                "unmatched_golden": [golden_name, ...],
                "unmatched_output": [output_name, ...]
            }
        """
        logger.info(
            f"🔍 Matching {len(golden_features)} features to {len(output_tasks)} tasks..."
        )

        matched = []
        unmatched_golden = []
        matched_output = set()

        for golden_feature in golden_features:
            # 1. Exact match 시도
            exact = self.exact_match(golden_feature, output_tasks)
            if exact:
                matched.append((golden_feature, exact, 1.0))
                matched_output.add(exact)
                continue

            # 2. Fuzzy match 시도
            fuzzy = self.fuzzy_match(golden_feature, output_tasks)
            if fuzzy:
                output_name, score = fuzzy
                matched.append((golden_feature, output_name, score))
                matched_output.add(output_name)
                continue

            # 3. 매칭 실패
            unmatched_golden.append(golden_feature)

        # Unmatched output tasks
        unmatched_output = [task for task in output_tasks if task not in matched_output]

        logger.info(
            f"✅ Matching complete - "
            f"Matched: {len(matched)}, "
            f"Unmatched Golden: {len(unmatched_golden)}, "
            f"Unmatched Output: {len(unmatched_output)}"
        )

        return {
            "matched": matched,
            "unmatched_golden": unmatched_golden,
            "unmatched_output": unmatched_output,
        }

    def calculate_coverage_score(
        self, golden_items: List[str], output_items: List[str]
    ) -> float:
        """
        Coverage Score 계산

        Args:
            golden_items: Golden Data의 항목 리스트
            output_items: Output의 항목 리스트

        Returns:
            Coverage score (0-1)
        """
        if not golden_items:
            return 1.0

        matching_result = self.match_features_to_tasks(golden_items, output_items)
        matched_count = len(matching_result["matched"])

        return matched_count / len(golden_items)


class SemanticMatcher:
    """
    LLM 기반 의미적 매칭 (Optional)

    텍스트 유사도로 매칭하기 어려운 경우, LLM을 사용하여 의미적 동등성을 판단
    """

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 클라이언트 (선택적)
        """
        self.llm_client = llm_client

    def semantic_match(
        self, golden_description: str, output_description: str
    ) -> Tuple[bool, float, str]:
        """
        의미적 동등성 판단

        Args:
            golden_description: Golden Data의 항목 설명
            output_description: Output의 항목 설명

        Returns:
            (is_equivalent, confidence_score, reasoning)
        """
        if not self.llm_client:
            logger.warning("LLM client not available for semantic matching")
            return (False, 0.0, "LLM not available")

        # LLM을 사용하여 의미적 동등성 판단
        prompt = f"""
        Compare these two descriptions and determine if they are semantically equivalent:

        Description 1 (Golden Data):
        {golden_description}

        Description 2 (Output):
        {output_description}

        Are these two descriptions referring to the same feature or functionality?

        Answer in JSON format:
        {{
            "is_equivalent": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }}
        """

        try:
            # LLM 호출 (실제 구현 필요)
            self.llm_client.invoke(prompt)
            # Parse response and return
            # (실제 구현에서는 JSON 파싱 및 오류 처리 필요)
            return (True, 0.8, "Semantic match found")

        except Exception as e:
            logger.error(f"Semantic matching failed: {e}")
            return (False, 0.0, str(e))
