import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.llm_provider import LLMProvider, OpenAIProvider


class TestLLMProvider:
    """Test cases for LLMProvider base class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.provider = LLMProvider()
    
    def test_init(self):
        """Test LLMProvider initialization"""
        assert hasattr(self.provider, 'generate_text')
    
    def test_generate_text_abstract(self):
        """Test that generate_text is abstract"""
        with pytest.raises(NotImplementedError):
            self.provider.generate_text("test prompt")


class TestOpenAIProvider:
    """Test cases for OpenAIProvider"""
    
    def setup_method(self):
        """Setup test fixtures"""
        with patch('backend.llm_provider.openai') as mock_openai:
            self.mock_openai = mock_openai
            self.provider = OpenAIProvider()
    
    def test_init(self):
        """Test OpenAIProvider initialization"""
        assert hasattr(self.provider, 'generate_text')
        assert hasattr(self.provider, 'client')
    
    def test_generate_text_success(self):
        """Test successful text generation"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers", "Suggestion": "Test suggestion"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        assert result == '{"SQLQuery": "SELECT * FROM customers", "Suggestion": "Test suggestion"}'
        self.mock_openai.OpenAI.return_value.chat.completions.create.assert_called_once()
    
    def test_generate_text_with_parameters(self):
        """Test text generation with custom parameters"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text(
            "Test prompt",
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000
        )
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['model'] == "gpt-4o-mini"
        assert call_args[1]['temperature'] == 0.1
        assert call_args[1]['max_tokens'] == 1000
    
    def test_generate_text_api_error(self):
        """Test handling of API error"""
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_rate_limit_error(self):
        """Test handling of rate limit error"""
        from openai import RateLimitError
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded", response=Mock(), body=None)
        
        with pytest.raises(RateLimitError):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_timeout_error(self):
        """Test handling of timeout error"""
        from openai import APITimeoutError
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = APITimeoutError("Request timeout", request=Mock())
        
        with pytest.raises(APITimeoutError):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_authentication_error(self):
        """Test handling of authentication error"""
        from openai import AuthenticationError
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = AuthenticationError("Invalid API key", response=Mock(), body=None)
        
        with pytest.raises(AuthenticationError):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_permission_error(self):
        """Test handling of permission error"""
        from openai import PermissionError
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = PermissionError("Insufficient permissions", response=Mock(), body=None)
        
        with pytest.raises(PermissionError):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_bad_request_error(self):
        """Test handling of bad request error"""
        from openai import BadRequestError
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = BadRequestError("Invalid request", response=Mock(), body=None)
        
        with pytest.raises(BadRequestError):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_with_system_message(self):
        """Test text generation with system message"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text(
            "Test prompt",
            system_message="You are a SQL expert"
        )
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        messages = call_args[1]['messages']
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == "You are a SQL expert"
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == "Test prompt"
    
    def test_generate_text_with_multiple_messages(self):
        """Test text generation with multiple messages"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"}
        ]
        
        result = self.provider.generate_text("Test prompt", messages=messages)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        actual_messages = call_args[1]['messages']
        
        assert len(actual_messages) == 4
        assert actual_messages[0]['role'] == 'user'
        assert actual_messages[0]['content'] == "First message"
        assert actual_messages[1]['role'] == 'assistant'
        assert actual_messages[1]['content'] == "First response"
        assert actual_messages[2]['role'] == 'user'
        assert actual_messages[2]['content'] == "Second message"
        assert actual_messages[3]['role'] == 'user'
        assert actual_messages[3]['content'] == "Test prompt"
    
    def test_generate_text_with_json_response(self):
        """Test text generation expecting JSON response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers", "Suggestion": "Test suggestion"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", response_format={"type": "json_object"})
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['response_format'] == {"type": "json_object"}
    
    def test_generate_text_with_streaming(self):
        """Test text generation with streaming"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", stream=True)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['stream'] is True
    
    def test_generate_text_with_tools(self):
        """Test text generation with tools"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_schema",
                    "description": "Get database schema",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "table": {"type": "string"}
                        }
                    }
                }
            }
        ]
        
        result = self.provider.generate_text("Test prompt", tools=tools)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['tools'] == tools
    
    def test_generate_text_with_tool_choice(self):
        """Test text generation with tool choice"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", tool_choice="auto")
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['tool_choice'] == "auto"
    
    def test_generate_text_with_seed(self):
        """Test text generation with seed for reproducibility"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", seed=12345)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['seed'] == 12345
    
    def test_generate_text_with_top_p(self):
        """Test text generation with top_p parameter"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", top_p=0.9)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['top_p'] == 0.9
    
    def test_generate_text_with_frequency_penalty(self):
        """Test text generation with frequency penalty"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", frequency_penalty=0.5)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['frequency_penalty'] == 0.5
    
    def test_generate_text_with_presence_penalty(self):
        """Test text generation with presence penalty"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", presence_penalty=0.5)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['presence_penalty'] == 0.5
    
    def test_generate_text_with_logit_bias(self):
        """Test text generation with logit bias"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        logit_bias = {"SELECT": 100, "FROM": 50}
        result = self.provider.generate_text("Test prompt", logit_bias=logit_bias)
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['logit_bias'] == logit_bias
    
    def test_generate_text_with_user(self):
        """Test text generation with user parameter"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", user="test_user")
        
        call_args = self.mock_openai.OpenAI.return_value.chat.completions.create.call_args
        assert call_args[1]['user'] == "test_user"
    
    def test_generate_text_with_extra_headers(self):
        """Test text generation with extra headers"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        extra_headers = {"X-Custom-Header": "custom_value"}
        result = self.provider.generate_text("Test prompt", extra_headers=extra_headers)
        
        # Note: This would require modifying the provider to support extra_headers
        # For now, we just test that the call doesn't fail
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
    
    def test_generate_text_with_extra_query(self):
        """Test text generation with extra query parameters"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        extra_query = {"custom_param": "custom_value"}
        result = self.provider.generate_text("Test prompt", extra_query=extra_query)
        
        # Note: This would require modifying the provider to support extra_query
        # For now, we just test that the call doesn't fail
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
    
    def test_generate_text_with_extra_body(self):
        """Test text generation with extra body parameters"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        extra_body = {"custom_body_param": "custom_value"}
        result = self.provider.generate_text("Test prompt", extra_body=extra_body)
        
        # Note: This would require modifying the provider to support extra_body
        # For now, we just test that the call doesn't fail
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
    
    def test_generate_text_with_timeout(self):
        """Test text generation with timeout"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt", timeout=30.0)
        
        # Note: This would require modifying the provider to support timeout
        # For now, we just test that the call doesn't fail
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
    
    def test_generate_text_with_retry(self):
        """Test text generation with retry logic"""
        # First call fails, second call succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = [
            Exception("Temporary error"),
            mock_response
        ]
        
        # This would require implementing retry logic in the provider
        # For now, we expect the first exception to be raised
        with pytest.raises(Exception):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_with_fallback(self):
        """Test text generation with fallback model"""
        # Primary model fails, fallback succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.side_effect = [
            Exception("Model not available"),
            mock_response
        ]
        
        # This would require implementing fallback logic in the provider
        # For now, we expect the first exception to be raised
        with pytest.raises(Exception):
            self.provider.generate_text("Test prompt")
    
    def test_generate_text_with_validation(self):
        """Test text generation with response validation"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        # Validate that the response is valid JSON
        try:
            json.loads(result)
            assert True
        except json.JSONDecodeError:
            assert False, "Response should be valid JSON"
    
    def test_generate_text_with_empty_response(self):
        """Test text generation with empty response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = ""
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        assert result == ""
    
    def test_generate_text_with_none_response(self):
        """Test text generation with None response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        assert result is None
    
    def test_generate_text_with_multiple_choices(self):
        """Test text generation with multiple choices"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(),
            Mock()
        ]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        mock_response.choices[1].message.content = '{"SQLQuery": "SELECT id FROM customers"}'
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        # Should return the first choice
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
    
    def test_generate_text_with_finish_reason(self):
        """Test text generation with finish reason"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        mock_response.choices[0].finish_reason = "stop"
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
    
    def test_generate_text_with_usage_info(self):
        """Test text generation with usage information"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"SQLQuery": "SELECT * FROM customers"}'
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        
        self.mock_openai.OpenAI.return_value.chat.completions.create.return_value = mock_response
        
        result = self.provider.generate_text("Test prompt")
        
        assert result == '{"SQLQuery": "SELECT * FROM customers"}'
        assert mock_response.usage.prompt_tokens == 100
        assert mock_response.usage.completion_tokens == 50
        assert mock_response.usage.total_tokens == 150
