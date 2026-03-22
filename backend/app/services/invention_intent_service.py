"""
发明意图总结服务 - Skill 1
"""

import logging
from typing import Dict, Optional

from skills.invention_intent.scripts.conversation_manager import ConversationManager
from skills.invention_intent.scripts.intent_extractor import IntentExtractor
from skills.invention_intent.scripts.document_generator import DocumentGenerator
from shared.db import get_database
from shared.db.models import PatentDraft
from .project_support import create_version_record, ensure_version_baseline, normalize_content

logger = logging.getLogger(__name__)


class InventionIntentService:
    """发明意图总结服务"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        """初始化"""
        self.llm_provider = llm_provider
        self.db = get_database()
    
    def start_conversation(self, user_id: str = "default_user") -> Dict:
        """
        开始新对话
        
        Returns:
            Dict: {session_id, welcome_message}
        """
        manager = ConversationManager(user_id=user_id, llm_provider=self.llm_provider)
        session_id = manager.start_session()
        
        return {
            'session_id': session_id,
            'welcome_message': """您好!我将协助您梳理技术创意，生成结构化的发明意图文档。

请简要描述您的技术创意，我会通过几个问题帮您完善细节。"""
        }
    
    def chat(self, session_id: str, message: str, user_id: str = "default_user") -> Dict:
        """
        对话
        
        Args:
            session_id: 会话ID
            message: 用户消息
            user_id: 用户ID
            
        Returns:
            Dict: {response, completed, round, extracted_info}
        """
        manager = ConversationManager(user_id=user_id, llm_provider=self.llm_provider)
        manager.session_id = session_id
        
        result = manager.add_user_message(message)
        
        return result
    
    def generate_document(
        self,
        session_id: str,
        user_id: str = "default_user",
        draft_id: Optional[str] = None,
    ) -> Dict:
        """
        生成发明意图文档
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            draft_id: 现有草稿ID，可选
            
        Returns:
            Dict: {document, intent, draft_id}
        """
        # 获取对话历史
        manager = ConversationManager(user_id=user_id, llm_provider=self.llm_provider)
        manager.session_id = session_id
        history = manager.get_history()
        
        # 提取意图
        extractor = IntentExtractor(llm_provider=self.llm_provider)
        intent = extractor.extract_intent(history, manager.extracted_info)
        
        # 生成文档
        generator = DocumentGenerator()
        document = generator.generate(intent)
        
        # 保存到数据库
        with self.db.get_session() as session:
            if draft_id:
                draft = session.query(PatentDraft).filter_by(id=draft_id).first()
                if not draft:
                    raise ValueError(f"草稿不存在: {draft_id}")

                ensure_version_baseline(session, draft)
                content = normalize_content(draft.content)
                content['invention_intent'] = intent
                content['invention_intent_doc'] = document
                project_profile = dict(content.get('project_profile') or {})
                project_profile['technical_field'] = (
                    project_profile.get('technical_field') or intent.get('technical_field', '')
                )
                project_profile['summary'] = (
                    project_profile.get('summary') or intent.get('technical_problem', '')
                )
                content['project_profile'] = project_profile
                workflow = dict(content.get('workflow') or {})
                workflow['current_stage'] = 'prior_art_search'
                content['workflow'] = workflow
                draft.content = content
                if intent.get('title') and draft.title in ('', '未命名专利项目'):
                    draft.title = intent.get('title')
                create_version_record(
                    session,
                    draft,
                    change_summary="生成发明意图文档",
                    document_key="invention_intent_doc",
                    changed_fields=["invention_intent", "invention_intent_doc"],
                )
                session.add(draft)
                resolved_draft_id = draft.id
            else:
                draft = PatentDraft(
                    user_id=user_id,
                    patent_type="发明",
                    title=intent.get('title', ''),
                    status='draft',
                    content={'invention_intent': intent,  'invention_intent_doc': document}
                )
                session.add(draft)
                session.flush()
                ensure_version_baseline(session, draft)
                resolved_draft_id = draft.id
        
        logger.info(f"发明意图文档生成成功, draft_id: {resolved_draft_id}")
        
        return {
            'document': document,
            'intent': intent,
            'draft_id': resolved_draft_id
        }
