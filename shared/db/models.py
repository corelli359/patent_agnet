"""
数据库模型定义
使用SQLAlchemy ORM
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4())


class SearchHistory(Base):
    """检索历史表"""
    __tablename__ = 'search_history'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    query = Column(Text, nullable=False, comment="检索关键词")
    filters = Column(JSON, comment="筛选条件（IPC、时间等）")
    source = Column(String(50), default='google_patents', comment="检索源")
    result_count = Column(Integer, default=0, comment="结果数量")
    status = Column(String(20), comment="success/failed/pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'query': self.query,
            'filters': self.filters,
            'source': self.source,
            'result_count': self.result_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PatentMetadata(Base):
    """专利元数据表"""
    __tablename__ = 'patent_metadata'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patent_number = Column(String(50), unique=True, nullable=False, index=True, comment="专利号")
    title = Column(String(500), comment="专利标题")
    abstract = Column(Text, comment="摘要")
    ipc_classifications = Column(JSON, comment='IPC分类号列表')
    publication_date = Column(DateTime, comment="公开日期")
    country_code = Column(String(10), comment="国家代码")
    pdf_url = Column(Text, comment="PDF下载链接")
    pdf_local_path = Column(Text, comment="本地PDF路径")
    source = Column(String(50), comment="来源：google_patents/local/bigquery")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'patent_number': self.patent_number,
            'title': self.title,
            'abstract': self.abstract,
            'ipc_classifications': self.ipc_classifications,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'country_code': self.country_code,
            'pdf_url': self.pdf_url,
            'pdf_local_path': self.pdf_local_path,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SearchResult(Base):
    """检索结果关联表"""
    __tablename__ = 'search_results'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    search_id = Column(String(36), ForeignKey('search_history.id'), nullable=False, index=True)
    patent_id = Column(String(36), ForeignKey('patent_metadata.id'), nullable=False, index=True)
    rank = Column(Integer, comment="排名")
    similarity_score = Column(Float, comment="相似度（0-100）")
    
    def to_dict(self):
        return {
            'id': self.id,
            'search_id': self.search_id,
            'patent_id': self.patent_id,
            'rank': self.rank,
            'similarity_score': self.similarity_score
        }


class Conversation(Base):
    """对话历史表 (Skill 1使用)"""
    __tablename__ = 'conversations'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), nullable=False, index=True, comment="会话ID")
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    message = Column(Text, nullable=False, comment="消息内容")
    role = Column(String(20), nullable=False, comment="角色: user/assistant/system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'message': self.message,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PatentDraft(Base):
    """专利草稿表 (存储各阶段文档)"""
    __tablename__ = 'patent_drafts'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    patent_type = Column(String(50), comment="专利类型: 发明/实用新型/外观设计")
    title = Column(String(255), comment="发明名称")
    status = Column(String(50), default='draft', comment="状态: draft/reviewing/submitted/granted")
    content = Column(JSON, comment="内容JSON: {invention_intent, disclosure, claims, specification, abstract}")
    version = Column(Integer, default=1, comment="版本号")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'patent_type': self.patent_type,
            'title': self.title,
            'status': self.status,
            'content': self.content,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PatentDraftVersion(Base):
    """专利草稿版本表"""
    __tablename__ = 'patent_draft_versions'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_id = Column(String(36), ForeignKey('patent_drafts.id'), nullable=False, index=True, comment="草稿ID")
    version_number = Column(Integer, nullable=False, index=True, comment="版本号")
    title = Column(String(255), comment="当时的发明名称")
    patent_type = Column(String(50), comment="当时的专利类型")
    status = Column(String(50), comment="当时的状态")
    document_key = Column(String(50), comment="本次变更的主文档键")
    change_summary = Column(String(255), comment="变更摘要")
    changed_fields = Column(JSON, comment="本次变更涉及的字段列表")
    snapshot = Column(JSON, comment="完整草稿快照")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'draft_id': self.draft_id,
            'version_number': self.version_number,
            'title': self.title,
            'patent_type': self.patent_type,
            'status': self.status,
            'document_key': self.document_key,
            'change_summary': self.change_summary,
            'changed_fields': self.changed_fields,
            'snapshot': self.snapshot,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ExaminationRecord(Base):
    """审查记录表 (Skill 4使用)"""
    __tablename__ = 'examination_records'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_id = Column(String(36), ForeignKey('patent_drafts.id'), nullable=False, index=True, comment="草稿ID")
    examination_type = Column(String(50), comment="审查类型: novelty/inventiveness/clarity/support/formal")
    defects = Column(JSON, comment="缺陷列表JSON")
    status = Column(String(50), comment="状态: pass/fail/warning")
    report_content = Column(Text, comment="审查报告内容")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'draft_id': self.draft_id,
            'examination_type': self.examination_type,
            'defects': self.defects,
            'status': self.status,
            'report_content': self.report_content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
