"""
对话管理器 - Skill 1: 发明意图总结
多轮对话引导用户完整表达技术创意
"""

import uuid
import logging
from typing import List, Dict, Optional
from datetime import datetime

from shared.utils.llm_client import get_llm_client
from shared.db import get_database
from shared.db.models import Conversation

logger = logging.getLogger(__name__)


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, user_id: str = "default_user", llm_provider: str = "deepseek"):
        """
        初始化对话管理器
        
        Args:
            user_id: 用户ID
            llm_provider: LLM提供商
        """
        self.user_id = user_id
        self.session_id = None
        self.llm_client = get_llm_client(llm_provider)
        self.db = get_database()
        self.max_rounds = 10
        self.current_round = 0
        
        # 必需字段
        self.required_fields = ['technical_problem', 'solution', 'effect']
        self.extracted_info = {}
    
    def start_session(self) -> str:
        """
        开始新会话
        
        Returns:
            str: 会话ID
        """
        self.session_id = str(uuid.uuid4())
        self.current_round = 0
        self.extracted_info = {}
        
        logger.info(f"开始新会话: {self.session_id}")
        
        # 保存系统消息
        self._save_message("system", "开始发明意图总结会话")
        
        # 返回欢迎消息
        welcome_msg = """您好!我将协助您梳理技术创意，生成结构化的发明意图文档。

请简要描述您的技术创意，我会通过几个问题帮您完善细节。"""
        
        self._save_message("assistant", welcome_msg)
        
        return self.session_id
    
    def add_user_message(self, message: str) -> Dict:
        """
        添加用户消息并获取AI响应
        
        Args:
            message: 用户消息
            
        Returns:
            Dict: {
                'response': str,  # AI响应
                'completed': bool,  # 是否完成
                'round': int  # 当前轮次
            }
        """
        if not self.session_id:
            raise ValueError("请先调用 start_session()")
        
        # 保存用户消息
        self._save_message("user", message)
        self.current_round += 1
        
        # 提取信息
        self._extract_information(message)
        
        # 检查是否完成
        if self._is_complete() or self.current_round >= self.max_rounds:
            response = "感谢您的详细描述!我已收集到足够的信息，现在将生成发明意图文档。"
            self._save_message("assistant", response)
            return {
                'response': response,
                'completed': True,
                'round': self.current_round,
                'extracted_info': self.extracted_info
            }
        
        # 生成引导问题
        response = self._generate_question()
        self._save_message("assistant", response)
        
        return {
            'response': response,
            'completed': False,
            'round': self.current_round,
            'extracted_info': self.extracted_info
        }
    
    def get_history(self) -> List[Dict]:
        """
        获取对话历史
        
        Returns:
            List[Dict]: 消息列表
        """
        if not self.session_id:
            return []
        
        with self.db.get_session() as session:
            conversations = session.query(Conversation).filter(
                Conversation.session_id == self.session_id
            ).order_by(Conversation.created_at).all()
            
            return [conv.to_dict() for conv in conversations]
    
    def _save_message(self, role: str, message: str):
        """保存消息到数据库"""
        if not self.session_id:
            return
        
        with self.db.get_session() as session:
            conversation = Conversation(
                session_id=self.session_id,
                user_id=self.user_id,
                message=message,
                role=role
            )
            session.add(conversation)
            session.commit()
    
    def _extract_information(self, user_message: str):
        """使用LLM提取结构化信息"""
        prompt = f"""从以下用户描述中提取技术信息，以JSON格式返回:

用户描述: {user_message}

已提取的信息: {self.extracted_info}

请提取或更新以下字段(如果用户有提及):
- technical_problem: 要解决的技术问题
- prior_art_defects: 现有技术的不足
- solution: 解决方案的核心要点
- key_steps: 关键技术步骤
- effect: 预期效果或优势
- innovation_points: 创新点

只返回JSON对象,不要其他文字。"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat(messages, temperature=0.3)
            
            # 解析JSON
            import json
            extracted = json.loads(response.strip().strip('```json').strip('```'))
            
            # 更新已提取信息
            for key, value in extracted.items():
                if value:
                    self.extracted_info[key] = value
            
            logger.info(f"提取信息: {self.extracted_info}")
        
        except Exception as e:
            logger.error(f"信息提取失败: {e}")
    
    def _is_complete(self) -> bool:
        """检查是否收集到所有必需信息"""
        for field in self.required_fields:
            if field not in self.extracted_info or not self.extracted_info[field]:
                return False
        return True
    
    def _generate_question(self) -> str:
        """生成下一个引导问题"""
        # 识别缺失字段
        missing_fields = []
        for field in self.required_fields:
            if field not in self.extracted_info or not self.extracted_info[field]:
                missing_fields.append(field)
        
        # 使用LLM生成自然的问题
        prompt = f"""你是一位专利代理师，正在帮助用户梳理技术创意。

当前已收集信息:
{self.extracted_info}

缺失字段: {missing_fields}

当前轮次: {self.current_round}/{self.max_rounds}

请生成一个自然、引导性的问题，帮助用户补充缺失信息。问题应该:
1. 简洁明了
2. 聚焦一个方面
3. 引导用户提供具体细节

只返回问题本身，不要其他说明。"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            question = self.llm_client.chat(messages, temperature=0.7, max_tokens=200)
            return question.strip()
        
        except Exception as e:
            logger.error(f"问题生成失败: {e}")
            # 降级到预设问题
            return self._get_fallback_question(missing_fields)
    
    def _get_fallback_question(self, missing_fields: List[str]) -> str:
        """降级问题库"""
        questions = {
            'technical_problem': "您想解决的核心技术问题是什么？",
            'solution': "您的解决方案的关键要点是什么？",
            'effect': "相比现有技术，您的方案有哪些优势或改进？",
            'prior_art_defects': "现有技术存在哪些不足或痛点？",
            'key_steps': "您的方案包含哪些关键技术步骤？",
            'innovation_points': "您认为最主要的创新点在哪里？"
        }
        
        for field in missing_fields:
            if field in questions:
                return questions[field]
        
        return "请继续描述您的技术方案，越详细越好。"
