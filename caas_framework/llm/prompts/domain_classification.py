"""
Domain Classification Prompts

Prompt templates for classifying requirements into domains.
"""

# TODO: Implement actual prompt templates
# These are placeholders until proper prompts are defined

DOMAIN_CLASSIFICATION_SYSTEM = """You are an expert domain classifier.
Classify the user's requirement into the appropriate domain category.

Respond with a JSON object following the DomainClassification schema."""

DOMAIN_CLASSIFICATION_USER = """Classify the following requirement into a domain:

{requirement}

Consider domains such as:
- Data Processing
- Web Development
- Machine Learning
- Business Automation
- DevOps
- Analytics
- etc.

Provide the domain, subdomain, and confidence score."""

DOMAIN_CLASSIFICATION_USER_KO = """다음 요구사항을 도메인으로 분류하세요:

{requirement}

다음과 같은 도메인을 고려하세요:
- 데이터 처리
- 웹 개발
- 머신러닝
- 비즈니스 자동화
- DevOps
- 분석
- 기타

도메인, 하위 도메인, 신뢰도 점수를 제공하세요."""
