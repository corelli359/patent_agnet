"""
意图提取器 - Skill 1: 发明意图总结
从对话历史中提取结构化的发明意图信息
"""

import logging
from typing import Dict, Any
import json

from shared.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class IntentExtractor:
    """意图提取器"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        """
        初始化
        
        Args:
            llm_provider: LLM提供商
        """
        self.llm_client = get_llm_client(llm_provider)
    
    def extract_intent(self, conversation_history: list, extracted_info: Dict) -> Dict[str, Any]:
        """
        从对话历史和已提取信息中生成完整的发明意图
        
        Args:
            conversation_history: 对话历史列表
            extracted_info: 已提取的信息字典
            
        Returns:
            Dict: 结构化的发明意图 {
                'title': str,
                'technical_field': str,
                'technical_problem': str,
                'prior_art_defects': str,
                'solution': str,
                'key_steps': List[str],
                'effect': str,
                'innovation_points': List[str]
            }
        """
        # 整理对话历史
        conversation_text = self._format_conversation(conversation_history)
        
        # 构建提取Prompt
        prompt = f"""你是一位资深专利代理师，请从以下对话和已提取信息中，总结出完整、结构化的发明意图。

对话历史:
{conversation_text}

已提取信息:
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}

请生成JSON格式的发明意图，包含以下字段:
1. title: 发明名称（简洁、描述性强）
2. technical_field: 技术领域（一句话，以"本发明涉及...领域"开头）
3. technical_problem: 要解决的技术问题（清晰、具体）
4. prior_art_defects: 现有技术的不足（列举2-3点）
5. solution: 解决方案概述（核心思想）
6. key_steps: 关键技术步骤（列表形式，3-5步）
7. effect: 有益效果（列举2-3点）
8. innovation_points: 创新点（列举1-3个）

要求:
- 专业、规范
- 信息完整、逻辑清晰
- 使用专利领域的规范用语

只返回JSON对象，不要其他内容。"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages, temperature=0.3, max_tokens=2000)
            
            # 解析JSON
            intent = json.loads(response.strip().strip('```json').strip('```'))
            
            logger.info("发明意图提取成功")
            return intent
        
        except Exception as e:
            logger.error(f"意图提取失败: {e}")
            # 返回基于已提取信息的降级版本
            return self._fallback_extraction(extracted_info)
    
    def _format_conversation(self, conversation_history: list) -> str:
        """格式化对话历史"""
        formatted = []
        for msg in conversation_history:
            role = msg.get('role', '')
            content = msg.get('message', '')
            
            if role == 'user':
                formatted.append(f"用户: {content}")
            elif role == 'assistant':
                formatted.append(f"助手: {content}")
        
        return '\n\n'.join(formatted)
    
    def _fallback_extraction(self, extracted_info: Dict) -> Dict[str, Any]:
        """降级提取方案"""
        return {
            'title': extracted_info.get('title', '一种技术方案'),
            'technical_field': extracted_info.get('technical_field', '本发明涉及相关技术领域'),
            'technical_problem': extracted_info.get('technical_problem', ''),
            'prior_art_defects': extracted_info.get('prior_art_defects', ''),
            'solution': extracted_info.get('solution', ''),
            'key_steps': extracted_info.get('key_steps', []),
            'effect': extracted_info.get('effect', ''),
            'innovation_points': extracted_info.get('innovation_points', [])
        }
