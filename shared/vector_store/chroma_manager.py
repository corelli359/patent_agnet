"""
Chroma向量数据库管理器
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChromaManager:
    """Chroma向量数据库管理"""
    
    def __init__(self, persist_dir: str = "data/vector_db/chroma"):
        """
        初始化Chroma管理器
        
        Args:
            persist_dir: 持久化目录
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        logger.info(f"Chroma数据库初始化成功: {self.persist_dir}")
    
    def get_or_create_collection(
        self, 
        name: str, 
        metadata: Optional[Dict] = None
    ):
        """
        获取或创建集合
        
        Args:
            name: 集合名称
            metadata: 集合元数据
            
        Returns:
            Collection: Chroma集合对象
        """
        try:
            collection = self.client.get_or_create_collection(
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"集合已就绪: {name}")
            return collection
        except Exception as e:
            logger.error(f"创建集合失败: {name}, 错误: {e}")
            raise
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None
    ):
        """
        添加文档到集合
        
        Args:
            collection_name: 集合名称
            documents: 文档列表
            metadatas: 元数据列表
            ids: 文档ID列表
            embeddings: 预计算的向量（可选，不提供则自动生成）
        """
        collection = self.get_or_create_collection(collection_name)
        
        # 生成ID（如果未提供）
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        # 添加文档
        try:
            if embeddings:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
            else:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            logger.info(f"成功添加 {len(documents)} 个文档到集合: {collection_name}")
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise
    
    def search(
        self,
        collection_name: str,
        query_texts: List[str] = None,
        query_embeddings: List[List[float]] = None,
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> Dict:
        """
        语义搜索
        
        Args:
            collection_name: 集合名称
            query_texts: 查询文本列表
            query_embeddings: 查询向量列表（与query_texts二选一）
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            
        Returns:
            Dict: 搜索结果
        """
        collection = self.get_or_create_collection(collection_name)
        
        try:
            if query_texts:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
            elif query_embeddings:
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
            else:
                raise ValueError("必须提供query_texts或query_embeddings")
            
            logger.info(f"搜索完成，返回 {n_results} 个结果")
            return results
        
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise
    
    def delete_collection(self, name: str):
        """删除集合"""
        try:
            self.client.delete_collection(name=name)
            logger.info(f"集合已删除: {name}")
        except Exception as e:
            logger.error(f"删除集合失败: {name}, 错误: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        collections = self.client.list_collections()
        return [c.name for c in collections]
    
    def get_collection_info(self, name: str) -> Dict:
        """
        获取集合信息
        
        Returns:
            Dict: {"name": "...", "count": 100, "metadata": {...}}
        """
        collection = self.get_or_create_collection(name)
        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata
        }


# 便捷函数
def get_chroma_client(persist_dir: str = "data/vector_db/chroma") -> ChromaManager:
    """
    获取Chroma管理器实例
    
    Args:
        persist_dir: 持久化目录
        
    Returns:
        ChromaManager: 管理器实例
    """
    return ChromaManager(persist_dir=persist_dir)
