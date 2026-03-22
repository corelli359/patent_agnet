"""
专利检索服务
整合Google Patents检索、数据存储、历史管理
"""

from typing import List, Dict, Optional
from datetime import datetime
import uuid
import logging

from skills.patent_search.scripts.google_patents_client import GooglePatentsAdvancedCrawler
from shared.db import get_database, PatentMetadata
from shared.db.repositories import PatentRepository

logger = logging.getLogger(__name__)


class PatentSearchService:
    """专利检索服务"""
    
    def __init__(self):
        """初始化服务"""
        self.crawler = GooglePatentsAdvancedCrawler(headless=True, delay=3.0)
        self.db = get_database()
    
    def search(
        self,
        query: str = None,  # 保留兼容性
        keywords: Optional[List[Dict[str, str]]] = None,  # 新：[{"term": "AI", "scope": "CL"}]
        ipc_classes: Optional[List[str]] = None,  # 新：IPC分类
        cpc_classes: Optional[List[str]] = None,  # 新：CPC分类
        user_id: str = "default_user",
        ipc_filter: Optional[str] = None,  # 废弃，保留兼容性
        country: Optional[str] = None,
        date_range: Optional[tuple] = None,
        max_results: int = 20,
        save_history: bool = True
    ) -> Dict:
        """
        执行专利检索（支持高级检索）
        
        Args:
            query: 简单查询（兼容旧接口）
            keywords: 关键词列表 [{"term": "区块链", "scope": "CL"}]
            ipc_classes: IPC分类号列表 ["G06F", "H04L"]
            cpc_classes: CPC分类号列表
            user_id: 用户ID
            date_range: 日期范围 ("2020-01-01", "2026-12-31")
            max_results: 最大结果数
            save_history: 是否保存历史
        """
        # 兼容性处理：如果传入简单query，转换为keywords格式
        if query and not keywords:
            keywords = [{"term": query, "scope": "TAC"}]
        
        # 构建查询描述（用于日志和历史）
        query_desc = self._build_query_description(keywords, ipc_classes, cpc_classes)
        stored_query = query or query_desc
        logger.info(f"开始检索: {query_desc}, max_results={max_results}")
        
        try:
            # 1. 调用Google Patents爬虫
            raw_results = self.crawler.search(
                keywords=keywords,
                ipc_classes=ipc_classes,
                cpc_classes=cpc_classes,
                after_date=date_range[0] if date_range and len(date_range) > 0 else None,
                before_date=date_range[1] if date_range and len(date_range) > 1 else None,
                num=max_results
            )
            
            # 2. 保存到数据库
            with self.db.get_session() as session:
                repo = PatentRepository(session)
                
                # 保存专利元数据
                saved_patents = []
                for patent_data in raw_results:
                    # 转换为数据库模型格式
                    db_data = self._convert_to_db_format(patent_data)
                    patent = repo.save_patent(db_data)
                    saved_patents.append(patent)
            
                # 保存检索历史（先保存history获取ID）
                search_id = None
                if save_history:
                    history_data = {
                        'user_id': user_id,
                        'query': stored_query,
                        'filters': {
                            'keywords': keywords,
                            'ipc_classes': ipc_classes,
                            'cpc_classes': cpc_classes,
                            'ipc': ipc_filter,
                            'country': country,
                            'date_range': date_range
                        },
                        'source': 'google_patents',
                        'result_count': len(saved_patents),
                        'status': 'success'
                    }
                    history = repo.save_search_history(history_data)
                    search_id = history.id
                    
                    # 提交以获取history.id
                    session.commit()
                    
                    # 保存检索结果关联
                    repo.save_search_results(search_id, saved_patents)
                
                session.commit()
            
            # 3. 生成分析报告
            from skills.patent_search.scripts.analysis_reporter import PatentAnalysisReporter
            reporter = PatentAnalysisReporter()
            analysis_report = reporter.generate_report(
                query=query,
                patents=[p.to_dict() for p in saved_patents],
                search_id=search_id
            )
            
            # 4. 返回结果
            return {
                'search_id': search_id,
                'query': stored_query,
                'result_count': len(saved_patents),
                'results': [p.to_dict() for p in saved_patents],
                'analysis_report': analysis_report  # 新增：分析报告
            }
        
        except Exception as e:
            logger.error(f"检索失败: {e}")
            
            # 保存失败记录
            if save_history:
                with self.db.get_session() as session:
                    repo = PatentRepository(session)
                    history_data = {
                        'user_id': user_id,
                        'query': stored_query,
                        'filters': {
                            'keywords': keywords,
                            'ipc_classes': ipc_classes,
                            'cpc_classes': cpc_classes,
                            'ipc': ipc_filter,
                            'country': country
                        },
                        'source': 'google_patents',
                        'result_count': 0,
                        'status': 'failed'
                    }
                    repo.save_search_history(history_data)
                    session.commit()
            
            raise
    
    def _build_query_description(
        self,
        keywords: Optional[List[Dict[str, str]]],
        ipc_classes: Optional[List[str]],
        cpc_classes: Optional[List[str]]
    ) -> str:
        """构建查询描述（用于日志和历史）"""
        parts = []
        
        if keywords:
            kw_parts = []
            for kw in keywords:
                term = kw.get('term', '')
                scope = kw.get('scope', 'TAC')
                scope_name = {
                    'TI': '标题',
                    'AB': '摘要',
                    'CL': '权利要求',
                    'TAC': '全文'
                }.get(scope, '全文')
                kw_parts.append(f'"{term}"({scope_name})')
            parts.append('关键词:' + '+'.join(kw_parts))
        
        if ipc_classes:
            parts.append(f'IPC:{",".join(ipc_classes)}')
        
        if cpc_classes:
            parts.append(f'CPC:{",".join(cpc_classes)}')
        
        return ' '.join(parts) if parts else '空查询'
    
    def get_history(
        self,
        user_id: str = "default_user",
        page: int = 1,
        limit: int = 10
    ) -> Dict:
        """
        获取检索历史
        
        Args:
            user_id: 用户ID
            page: 页码
            limit: 每页数量
            
        Returns:
            Dict: 历史记录
        """
        offset = (page - 1) * limit
        
        with self.db.get_session() as session:
            repo = PatentRepository(session)
            histories = repo.get_search_history(user_id, limit, offset)
            
            return {
                'page': page,
                'limit': limit,
                'items': [h.to_dict() for h in histories]
            }
    
    def get_search_results(self, search_id: str) -> List[Dict]:
        """
        获取某次检索的结果
        
        Args:
            search_id: 检索ID
            
        Returns:
            List[Dict]: 结果列表
        """
        with self.db.get_session() as session:
            repo = PatentRepository(session)
            return repo.get_search_results(search_id)
    
    def _convert_to_db_format(self, patent_data: Dict) -> Dict:
        """
        将Google Patents API返回的数据转换为数据库格式
        
        Args:
            patent_data: API返回的专利数据
            
        Returns:
            Dict: 数据库格式
        """
        # 提取国家代码（从专利号）
        patent_number = patent_data.get('patent_number')
        country_code = patent_number[:2] if patent_number else None
        
        # 解析日期
        pub_date = patent_data.get('publication_date')
        if pub_date and isinstance(pub_date, str):
            try:
                pub_date = datetime.strptime(pub_date, "%Y-%m-%d")
            except:
                pub_date = None
        
        return {
            'patent_number': patent_number,
            'title': patent_data.get('title'),
            'abstract': patent_data.get('snippet'),  # Google Patents返回的是snippet
            'ipc_classifications': patent_data.get('ipc_classifications', []),
            'publication_date': pub_date,
            'country_code': country_code,
            'pdf_url': patent_data.get('pdf_link'),
            'source': 'google_patents'
        }


# 便捷函数
def search_patents(
    query: str,
    ipc: Optional[str] = None,
    country: Optional[str] = None,
    max_results: int = 20
) -> Dict:
    """
    便捷检索函数
    
    Args:
        query: 检索关键词
        ipc: IPC分类号
        country: 国家代码
        max_results: 最大结果数
        
    Returns:
        Dict: 检索结果
    """
    service = PatentSearchService()
    return service.search(
        query=query,
        ipc_filter=ipc,
        country=country,
        max_results=max_results
    )
