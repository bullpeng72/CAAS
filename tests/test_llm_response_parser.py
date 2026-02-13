"""
Test LLM Response Parser

✅ v0.4.3 (Bug #3): Tests for safe JSON parsing with LLM responses
"""

import pytest
from caas_framework.utils.json_parser import LLMResponseParser, parse_llm_json


class MockLLMResponse:
    """Mock LLMResponse object for testing"""

    def __init__(self, content):
        self.content = content


class TestLLMResponseParser:
    """Test LLM response parsing with various formats"""

    def test_parse_plain_json_string(self):
        """Test: Plain JSON string"""
        response = '{"key": "value"}'
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_parse_llm_response_object(self):
        """Test: LLMResponse object with JSON content"""
        response = MockLLMResponse('{"key": "value"}')
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_parse_markdown_json_with_tag(self):
        """Test: Markdown code block with json tag"""
        response = '```json\n{"key": "value"}\n```'
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_parse_markdown_json_without_tag(self):
        """Test: Markdown code block without json tag"""
        response = '```\n{"key": "value"}\n```'
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_parse_llm_response_with_markdown(self):
        """Test: LLMResponse with markdown-wrapped JSON"""
        response = MockLLMResponse('```json\n{"sections": [{"title": "Test"}]}\n```')
        result = parse_llm_json(response)
        assert result == {"sections": [{"title": "Test"}]}

    def test_parse_malformed_json_trailing_comma(self):
        """Test: Malformed JSON with trailing comma (auto-repair)"""
        response = '{"key": "value",}'
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_parse_malformed_json_unquoted_keys(self):
        """Test: Malformed JSON with unquoted keys (auto-repair)"""
        response = '{key: "value"}'
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_parse_invalid_json_with_default(self):
        """Test: Invalid JSON returns default value"""
        response = 'This is not JSON at all'
        result = parse_llm_json(response, default={"fallback": True})
        assert result == {"fallback": True}

    def test_parse_empty_string_with_default(self):
        """Test: Empty string returns default value"""
        response = ''
        result = parse_llm_json(response, default={})
        assert result == {}

    def test_parse_dictionary_input(self):
        """Test: Direct dictionary input (no parsing needed)"""
        response = {"already": "parsed"}
        result = parse_llm_json(response)
        assert result == {"already": "parsed"}

    def test_to_string_with_various_types(self):
        """Test: to_string handles various input types"""
        parser = LLMResponseParser()

        # String
        assert parser.to_string("hello") == "hello"

        # LLMResponse
        assert parser.to_string(MockLLMResponse("content")) == "content"

        # Dictionary
        result = parser.to_string({"key": "value"})
        assert "key" in result and "value" in result

        # Other
        assert parser.to_string(123) == "123"

    def test_extract_json_multiple_patterns(self):
        """Test: extract_json handles multiple markdown patterns"""
        parser = LLMResponseParser()

        # Pattern 1: ```json ... ```
        text1 = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result1 = parser.extract_json(text1)
        assert '{"key": "value"}' in result1

        # Pattern 2: ``` ... ```
        text2 = 'Text\n```\n{"key": "value"}\n```'
        result2 = parser.extract_json(text2)
        assert '{"key": "value"}' in result2

        # Pattern 3: Direct JSON
        text3 = '{"key": "value"}'
        result3 = parser.extract_json(text3)
        assert result3 == '{"key": "value"}'

    def test_repair_json_comprehensive(self):
        """Test: repair_json fixes common issues"""
        parser = LLMResponseParser()

        # Trailing comma in object
        assert parser.repair_json('{"a": 1,}') == '{"a": 1}'

        # Trailing comma in array
        assert parser.repair_json('["a", "b",]') == '["a", "b"]'

        # Unquoted keys
        repaired = parser.repair_json('{name: "John"}')
        assert '"name"' in repaired

        # Single quotes to double quotes
        assert parser.repair_json("{'key': 'value'}") == '{"key": "value"}'

    def test_parse_json_safe_no_repair(self):
        """Test: parse_json_safe with repair disabled"""
        parser = LLMResponseParser()

        # Valid JSON works
        result = parser.parse_json_safe('{"key": "value"}', repair=False)
        assert result == {"key": "value"}

        # Invalid JSON returns default (repair disabled)
        result = parser.parse_json_safe('{"key": "value",}', default={"error": True}, repair=False)
        assert result == {"error": True}

    def test_complex_nested_json(self):
        """Test: Complex nested JSON structure"""
        complex_json = '''
        {
            "sections": [
                {
                    "title": "User Info",
                    "widgets": [
                        {"type": "text", "name": "username"},
                        {"type": "email", "name": "email"}
                    ]
                },
                {
                    "title": "Settings",
                    "widgets": [
                        {"type": "checkbox", "name": "notifications"}
                    ]
                }
            ]
        }
        '''
        result = parse_llm_json(complex_json)
        assert len(result["sections"]) == 2
        assert result["sections"][0]["title"] == "User Info"
        assert len(result["sections"][0]["widgets"]) == 2

    def test_llm_response_with_explanation_text(self):
        """Test: LLM response with explanatory text before JSON"""
        response = '''
        Here's the JSON you requested:

        ```json
        {
            "result": "success",
            "data": [1, 2, 3]
        }
        ```

        Hope this helps!
        '''
        result = parse_llm_json(response)
        assert result == {"result": "success", "data": [1, 2, 3]}


class TestAgentOutputParserIntegration:
    """Test integration with AgentOutputParser"""

    def test_parse_json_safe_integration(self):
        """Test: AgentOutputParser.parse_json_safe uses LLMResponseParser"""
        from caas_framework.agents.utils import AgentOutputParser

        # Test with LLMResponse object
        response = MockLLMResponse('{"agent": "test"}')
        result = AgentOutputParser.parse_json_safe(response)
        assert result == {"agent": "test"}

        # Test with default
        result = AgentOutputParser.parse_json_safe("invalid", default={"fallback": True})
        assert result == {"fallback": True}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
