"""
LLM客户端单元测试
"""

import pytest
from unittest.mock import Mock, patch
from shared.utils.llm_client import LLMClient, LLMProvider, get_llm_client


class TestLLMClient:
    """LLM客户端测试"""
    
    def test_provider_enum(self):
        """测试Provider枚举"""
        assert LLMProvider.DEEPSEEK.value == "deepseek"
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.CLAUDE.value == "claude"
    
    @patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'})
    def test_client_initialization_deepseek(self):
        """测试DeepSeek客户端初始化"""
        client = LLMClient(provider="deepseek")
        assert client.provider == LLMProvider.DEEPSEEK
        assert client.api_key == 'test_key'
    
    def test_client_missing_api_key(self):
        """测试缺少API密钥的情况"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="未设置API密钥"):
                LLMClient(provider="deepseek")
    
    @patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'})
    @patch('shared.utils.llm_client.OpenAI')
    def test_chat_deepseek(self, mock_openai):
        """测试DeepSeek对话"""
        # Mock OpenAI响应
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="测试响应"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        client = LLMClient(provider="deepseek")
        messages = [{"role": "user", "content": "你好"}]
        response = client.chat(messages)
        
        assert response == "测试响应"
    
    @patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'})  
    def test_get_llm_client(self):
        """测试便捷函数"""
        client = get_llm_client("deepseek")
        assert isinstance(client, LLMClient)
        assert client.provider == LLMProvider.DEEPSEEK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
