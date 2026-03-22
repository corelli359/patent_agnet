"""
专利申请文件起草服务 - Skill 3
生成权利要求书、说明书、摘要
"""

import logging
from typing import Dict
import re

from shared.utils.llm_client import get_llm_client
from shared.utils.markdown_formatter import get_formatter
from shared.db import get_database
from shared.db.models import PatentDraft
from .project_support import (
    create_version_record,
    ensure_version_baseline,
    mark_document_update,
    normalize_content,
    require_action_requirements,
)

logger = logging.getLogger(__name__)


class PatentDraftingService:
    """专利起草服务"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        """初始化"""
        self.llm_client = get_llm_client(llm_provider)
        self.formatter = get_formatter()
        self.db = get_database()
    
    def generate_patent_files(self, draft_id: str) -> Dict:
        """
        从技术交底书生成专利申请文件
        
        Returns:
            Dict: {claims, specification, abstract}
        """
        # 获取技术交底书
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            if not draft:
                raise ValueError(f"草稿不存在: {draft_id}")

            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            require_action_requirements(content, "generate_drafting", "生成专利申请文件")
            disclosure = content.get('disclosure', {})
            intent = content.get('invention_intent', {})
        
        # 生成文件
        claims = self._generate_claims(intent, disclosure)
        specification = self._generate_specification(intent, disclosure)
        abstract = self._generate_abstract(intent)
        
        # 格式化
        claims_formatted = self.formatter.format_claims(claims)
        spec_formatted = self.formatter.auto_number_paragraphs(specification)
        
        # 保存
        with self.db.get_session() as session:
            draft = session.query(PatentDraft).filter_by(id=draft_id).first()
            ensure_version_baseline(session, draft)
            content = normalize_content(draft.content)
            content['claims'] = claims_formatted
            content['specification'] = spec_formatted
            content['abstract'] = abstract
            content = mark_document_update(content, ["claims", "specification", "abstract"])
            draft.content = content
            create_version_record(
                session,
                draft,
                change_summary="生成专利申请文件",
                document_key="claims",
                changed_fields=["claims", "specification", "abstract"],
            )
            session.commit()
        
        return {
            'claims': claims_formatted,
            'specification': spec_formatted,
            'abstract': abstract
        }
    
    def _generate_claims(self, intent: Dict, disclosure: Dict) -> str:
        """生成权利要求书"""
        prompt = f"""基于以下信息，生成专利权利要求书:

发明名称: {intent.get('title', '')}
解决方案: {intent.get('solution', '')}
关键步骤: {intent.get('key_steps', [])}

要求:
1. 至少1条独立权利要求、3条从属权利要求
2. 独立权利要求必须包含"其特征在于"
3. 独立权利要求用单句表达
4. 从属权利要求用"根据权利要求X"开头
5. 格式: "1. 独立权利要求内容\\n\\n2. 根据权利要求1..."

只返回权利要求书内容，不要其他内容。"""
        
        messages = [{"role": "user", "content": prompt}]
        claims = self.llm_client.chat(messages, temperature=0.2, max_tokens=1500)
        
        return f"# 权利要求书\n\n{claims}"
    
    def _generate_specification(self, intent: Dict, disclosure: Dict) -> str:
        """生成说明书"""
        prompt = f"""基于以下信息，生成专利说明书:

技术领域: {disclosure.get('technical_field', '')}
背景技术: {disclosure.get('background', '')}
发明内容: {disclosure.get('invention_content', '')}
具体实施方式: {disclosure.get('embodiments', '')}

要求:
1. 包含: 技术领域、背景技术、发明内容、具体实施方式
2. 符合《专利审查指南》规范
3. 800-1500字

返回说明书内容 (不包含段落编号，将自动添加)。"""
        
        messages = [{"role": "user", "content": prompt}]
        spec = self.llm_client.chat(messages, temperature=0.3, max_tokens=2000)
        
        return f"# 说明书\n\n{spec}"
    
    def _generate_abstract(self, intent: Dict) -> str:
        """生成摘要"""
        prompt = f"""基于以下信息，生成专利摘要:

发明名称: {intent.get('title', '')}
技术问题: {intent.get('technical_problem', '')}
解决方案: {intent.get('solution', '')}
预期效果: {intent.get('effect', '')}

要求:
1. 150-300字
2. 包含技术问题、方案要点、效果
3. 简洁、清晰

只返回摘要内容，不要其他内容。"""
        
        messages = [{"role": "user", "content": prompt}]
        abstract = self.llm_client.chat(messages, temperature=0.3, max_tokens=400)
        
        return f"# 摘要\n\n{abstract}"
