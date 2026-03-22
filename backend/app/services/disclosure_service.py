"""
技术交底书生成服务 - Skill 2
基于发明意图生成技术交底书
"""

import logging
from typing import Dict, Optional
import json

from shared.utils.llm_client import get_llm_client
from shared.utils.pdf_parser import PDFParser
from shared.db import get_database
from shared.db.models import PatentDraft
from .project_support import (
    create_version_record,
    ensure_version_baseline,
    normalize_content,
    require_action_requirements,
)

logger = logging.getLogger(__name__)


class DisclosureService:
    """技术交底书服务"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        """初始化"""
        self.llm_client = get_llm_client(llm_provider)
        self.db = get_database()
        self.pdf_parser = PDFParser()
    
    def generate_from_intent(self, draft_id: str) -> Dict:
        """
        从发明意图生成技术交底书
        
        Args:
            draft_id: 专利草稿ID
            
        Returns:
            Dict: {disclosure_doc, sections}
        """
        # 获取发明意图
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"草稿不存在: {draft_id}")

            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            require_action_requirements(content, "generate_disclosure", "生成技术交底书")
            intent = content.get('invention_intent', {})
        
        # 生成各章节
        sections = {
            'technical_field': self._generate_technical_field(intent),
            'background': self._generate_background(intent),
            'invention_content': self._generate_invention_content(intent),
            'embodiments': self._generate_embodiments(intent)
        }
        
        # 组装完整文档
        disclosure_doc = self._assemble_disclosure(sections, intent)
        
        # 更新数据库
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            content['disclosure'] = sections
            content['disclosure_doc'] = disclosure_doc
            draft.content = content
            create_version_record(
                session,
                draft,
                change_summary="生成技术交底书",
                document_key="disclosure_doc",
                changed_fields=["disclosure", "disclosure_doc"],
            )
            session.commit()
        
        return {
            'disclosure_doc': disclosure_doc,
            'sections': sections
        }
    
    def _generate_technical_field(self, intent: Dict) -> str:
        """生成技术领域"""
        prompt = f"""基于以下发明意图，生成规范的"技术领域"描述:

发明名称: {intent.get('title', '')}
技术领域: {intent.get('technical_field', '')}

要求:
1. 以"本发明涉及...领域，具体涉及..."格式
2. 简洁、明确
3. 一段话说明

只返回技术领域描述，不要其他内容。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.llm_client.chat(messages, temperature=0.3, max_tokens=200) 
    
    def _generate_background(self, intent: Dict) -> str:
        """生成背景技术"""
        prompt = f"""基于以下信息，生成"背景技术"章节:

技术问题: {intent.get('technical_problem', '')}
现有技术不足: {intent.get('prior_art_defects', '')}

要求:
1. 客观描述现有技术
2. 指出现有技术的不足（2-3点）
3. 200-300字
4. 符合专利说明书规范

只返回背景技术内容，不要其他内容。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.llm_client.chat(messages, temperature=0.3, max_tokens=500)
    
    def _generate_invention_content(self, intent: Dict) -> str:
        """生成发明内容"""
        prompt = f"""基于以下信息，生成"发明内容"章节:

技术问题: {intent.get('technical_problem', '')}
解决方案: {intent.get('solution', '')}
预期效果: {intent.get('effect', '')}

要求:
1. 包含三个部分:
   - 要解决的技术问题
   - 技术方案
   - 有益效果
2. 清晰、结构化
3. 300-500字

只返回发明内容，不要其他内容。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.llm_client.chat(messages, temperature=0.3, max_tokens=800)
    
    def _generate_embodiments(self, intent: Dict) -> str:
        """生成具体实施方式"""
        key_steps = intent.get('key_steps', [])
        if isinstance(key_steps, str):
            key_steps_str = key_steps
        else:
            key_steps_str = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(key_steps)])
        
        prompt = f"""基于以下信息，生成"具体实施方式"章节:

解决方案: {intent.get('solution', '')}
关键步骤:
{key_steps_str}

要求:
1. 详细描述技术实现
2. 包含实施例1（可选实施例2）
3. 结合具体参数、流程
4. 400-600字

只返回具体实施方式内容，不要其他内容。"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.llm_client.chat(messages, temperature=0.4, max_tokens=1000)
    
    def _assemble_disclosure(self, sections: Dict, intent: Dict) -> str:
        """组装完整技术交底书"""
        doc = f"""# 技术交底书

## 发明名称

{intent.get('title', '（待补充）')}

## 技术领域

{sections['technical_field']}

## 背景技术

{sections['background']}

## 发明内容

{sections['invention_content']}

## 具体实施方式

{sections['embodiments']}

---

**说明**: 本文档由AI辅助生成，仅供参考。"""
        
        return doc
