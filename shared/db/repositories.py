"""
专利数据仓库
处理专利元数据的数据库操作
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from shared.db.models import PatentMetadata, SearchHistory, SearchResult
import logging

logger = logging.getLogger(__name__)


class PatentRepository:
    """专利数据仓库"""
    
    def __init__(self, session: Session):
        """
        初始化仓库
        
        Args:
            session: SQLAlchemy会话
        """
        self.session = session
    
    def save_patent(self, patent_data: Dict) -> PatentMetadata:
        """
        保存或更新专利元数据
        
        Args:
            patent_data: 专利数据字典
            
        Returns:
            PatentMetadata: 保存的专利对象
        """
        patent_number = patent_data.get('patent_number')
        if not patent_number:
            raise ValueError("专利号不能为空")
        
        # 检查是否已存在
        existing = self.get_by_patent_number(patent_number)
        
        if existing:
            # 更新
            for key, value in patent_data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            logger.info(f"更新专利: {patent_number}")
            return existing
        else:
            # 新增
            patent = PatentMetadata(**patent_data)
            self.session.add(patent)
            logger.info(f"新增专利: {patent_number}")
            return patent
    
    def get_by_patent_number(self, patent_number: str) -> Optional[PatentMetadata]:
        """根据专利号查询"""
        return self.session.query(PatentMetadata).filter(
            PatentMetadata.patent_number == patent_number
        ).first()
    
    def get_by_id(self, patent_id: str) -> Optional[PatentMetadata]:
        """根据ID查询"""
        return self.session.query(PatentMetadata).filter(
            PatentMetadata.id == patent_id
        ).first()
    
    def search_by_keywords(
        self, 
        keywords: List[str], 
        limit: int = 20
    ) -> List[PatentMetadata]:
        """
        根据关键词搜索（本地数据库）
        
        Args:
            keywords: 关键词列表
            limit: 最大结果数
            
        Returns:
            List[PatentMetadata]: 专利列表
        """
        query = self.session.query(PatentMetadata)
        
        # 在标题和摘要中搜索
        for keyword in keywords:
            query = query.filter(
                (PatentMetadata.title.like(f'%{keyword}%')) |
                (PatentMetadata.abstract.like(f'%{keyword}%'))
            )
        
        return query.limit(limit).all()
    
    def save_search_history(self, search_data: Dict) -> SearchHistory:
        """保存检索历史"""
        history = SearchHistory(**search_data)
        self.session.add(history)
        logger.info(f"保存检索历史: {search_data.get('query')}")
        return history
    
    def save_search_results(
        self,
        search_id: str,
        patents: List[PatentMetadata],
        similarity_scores: Optional[List[float]] = None
    ):
        """
        保存检索结果关联
        
        Args:
            search_id: 检索历史ID
            patents: 专利列表
            similarity_scores: 相似度评分列表（可选）
        """
        for idx, patent in enumerate(patents):
            result = SearchResult(
                search_id=search_id,
                patent_id=patent.id,
                rank=idx + 1,
                similarity_score=similarity_scores[idx] if similarity_scores else None
            )
            self.session.add(result)
        
        logger.info(f"保存检索结果: {len(patents)} 条")
    
    def get_search_history(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[SearchHistory]:
        """
        获取用户检索历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            List[SearchHistory]: 检索历史列表
        """
        return self.session.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).order_by(
            SearchHistory.created_at.desc()
        ).limit(limit).offset(offset).all()
    
    def get_search_results(self, search_id: str) -> List[Dict]:
        """
        获取检索结果（含专利详情）
        
        Args:
            search_id: 检索历史ID
            
        Returns:
            List[Dict]: 检索结果列表
        """
        results = self.session.query(SearchResult).filter(
            SearchResult.search_id == search_id
        ).order_by(SearchResult.rank).all()
        
        output = []
        for result in results:
            patent = self.get_by_id(result.patent_id)
            if patent:
                output.append({
                    'rank': result.rank,
                    'similarity_score': result.similarity_score,
                    'patent': patent.to_dict()
                })
        
        return output
