"""
LLM客户端抽象层
支持多LLM切换（DeepSeek/Gemini/Claude）
"""

import os
from typing import List, Dict, Optional
from enum import Enum
import logging

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - 仅在缺少依赖时触发
    OpenAI = None

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM提供商"""
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    CLAUDE = "claude"


class LLMClient:
    """LLM客户端统一接口"""
    
    def __init__(self, provider: str = "deepseek", api_key: Optional[str] = None):
        """
        初始化LLM客户端
        
        Args:
            provider: LLM提供商 (deepseek/gemini/claude)
            api_key: API密钥，如果不提供则从环境变量读取
        """
        self.provider = LLMProvider(provider)
        self.api_key = api_key or self._get_api_key()
        self.client = self._init_client()
    
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        对话接口
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}, ...]
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: LLM响应内容
        """
        try:
            if self.provider == LLMProvider.DEEPSEEK:
                return self._chat_deepseek(messages, temperature, max_tokens)
            elif self.provider == LLMProvider.GEMINI:
                return self._chat_gemini(messages, temperature, max_tokens)
            elif self.provider == LLMProvider.CLAUDE:
                return self._chat_claude(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            # 重试逻辑
            return self._retry_with_fallback(messages, temperature, max_tokens, attempt=1)
    
    def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        文本向量化
        
        Args:
            text: 待向量化的文本
            model: 模型名称（可选，使用默认）
            
        Returns:
            List[float]: 向量表示
        """
        try:
            if self.provider == LLMProvider.DEEPSEEK:
                return self._embed_deepseek(text, model)
            elif self.provider == LLMProvider.GEMINI:
                return self._embed_gemini(text, model)
            else:
                # Claude不支持embedding，使用DeepSeek
                logger.warning("Claude不支持embedding，回退到DeepSeek")
                temp_client = LLMClient(provider="deepseek")
                return temp_client.embed(text, model)
        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            raise
    
    def _init_client(self):
        """初始化具体的LLM客户端"""
        if self.provider == LLMProvider.DEEPSEEK:
            if OpenAI is None:
                raise ImportError("openai 依赖未安装，无法初始化 DeepSeek 客户端")
            return OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
        elif self.provider == LLMProvider.GEMINI:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            return genai
        elif self.provider == LLMProvider.CLAUDE:
            from anthropic import Anthropic
            return Anthropic(api_key=self.api_key)
    
    def _get_api_key(self) -> str:
        """从环境变量获取API密钥"""
        key_map = {
            LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
            LLMProvider.GEMINI: "GEMINI_API_KEY",
            LLMProvider.CLAUDE: "CLAUDE_API_KEY"
        }
        env_var = key_map[self.provider]
        api_key = os.getenv(env_var)
        
        if not api_key:
            raise ValueError(f"未设置API密钥环境变量: {env_var}")
        
        return api_key
    
    # ============ DeepSeek实现 ============
    def _chat_deepseek(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """DeepSeek对话"""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def _embed_deepseek(self, text: str, model: Optional[str]) -> List[float]:
        """DeepSeek向量化"""
        # DeepSeek使用OpenAI兼容的embedding接口
        model = model or "text-embedding-ada-002"
        response = self.client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    
    # ============ Gemini实现 ============
    def _chat_gemini(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Gemini对话"""
        model = self.client.GenerativeModel('gemini-pro')
        
        # 转换消息格式
        chat_history = []
        user_message = ""
        for msg in messages:
            if msg['role'] == 'user':
                user_message = msg['content']
            elif msg['role'] == 'assistant':
                chat_history.append({
                    'role': 'model',
                    'parts': [msg['content']]
                })
        
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(
            user_message,
            generation_config={'temperature': temperature, 'max_output_tokens': max_tokens}
        )
        return response.text
    
    def _embed_gemini(self, text: str, model: Optional[str]) -> List[float]:
        """Gemini向量化"""
        model_name = model or "models/embedding-001"
        result = self.client.embed_content(
            model=model_name,
            content=text
        )
        return result['embedding']
    
    # ============ Claude实现 ============
    def _chat_claude(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Claude对话"""
        # 提取system消息
        system_msg = None
        chat_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                system_msg = msg['content']
            else:
                chat_messages.append(msg)
        
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg,
            messages=chat_messages
        )
        return response.content[0].text
    
    # ============ 重试与容错 ============
    def _retry_with_fallback(
        self, 
        messages: List[Dict], 
        temperature: float, 
        max_tokens: int,
        attempt: int = 1,
        max_attempts: int = 3
    ) -> str:
        """重试机制，最多3次"""
        if attempt >= max_attempts:
            raise Exception(f"LLM调用失败，已重试{max_attempts}次")
        
        logger.info(f"重试LLM调用，第{attempt}次")
        import time
        time.sleep(2 ** attempt)  # 指数退避
        
        try:
            return self.chat(messages, temperature, max_tokens)
        except Exception as e:
            logger.error(f"第{attempt}次重试失败: {e}")
        return self._retry_with_fallback(messages, temperature, max_tokens, attempt + 1)


def _provider_env_var(provider: str) -> str:
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "claude": "CLAUDE_API_KEY",
    }
    return key_map[provider]


def _has_provider_api_key(provider: str) -> bool:
    env_var = _provider_env_var(provider)
    return bool(os.getenv(env_var))


def resolve_llm_provider(provider: Optional[str] = None) -> str:
    """
    解析可用的LLM提供商。

    优先使用显式 provider，其次使用 DEFAULT_LLM_PROVIDER。
    若目标 provider 未配置密钥，则自动回退到已配置密钥的提供商。
    """
    requested = provider or os.getenv("DEFAULT_LLM_PROVIDER") or "deepseek"
    candidates = [
        requested,
        os.getenv("DEFAULT_LLM_PROVIDER"),
        "deepseek",
        "gemini",
        "claude",
    ]

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if _has_provider_api_key(candidate):
            if candidate != requested:
                logger.warning("LLM提供商 %s 未配置密钥，自动回退到 %s", requested, candidate)
            return candidate

    return requested


# 便捷函数
def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    获取LLM客户端实例
    
    Args:
        provider: LLM提供商
        
    Returns:
        LLMClient: 客户端实例
    """
    return LLMClient(provider=resolve_llm_provider(provider))
