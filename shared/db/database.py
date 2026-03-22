"""
数据库连接和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from pathlib import Path
import logging

from .models import Base

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_url: str = None, echo: bool = False):
        """
        初始化数据库连接
        
        Args:
            db_url: 数据库连接字符串，不提供则使用环境变量或默认SQLite
            echo: 是否打印SQL语句
        """
        self.db_url = db_url or self._get_db_url()
        self.engine = create_engine(self.db_url, echo=echo)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        
        logger.info(f"数据库连接已建立: {self.db_url.split('@')[-1] if '@' in self.db_url else self.db_url}")
    
    def _get_db_url(self) -> str:
        """从环境变量获取数据库URL或使用默认SQLite"""
        env = os.getenv('ENVIRONMENT', 'development')
        
        if env == 'production':
            # 生产环境使用MySQL
            host = os.getenv('MYSQL_HOST', 'localhost')
            port = os.getenv('MYSQL_PORT', '3306')
            user = os.getenv('MYSQL_USER', 'patent_user')
            password = os.getenv('MYSQL_PASSWORD', '')
            database = os.getenv('MYSQL_DATABASE', 'patent_db')
            
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        else:
            # 开发环境使用SQLite
            db_path = Path("data/patent.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("数据库表创建完成")
    
    def drop_tables(self):
        """删除所有表（谨慎使用）"""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("数据库表已删除")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        获取数据库会话（上下文管理器）
        
        Usage:
            with db.get_session() as session:
                session.query(Model).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()


# 全局数据库实例
_db_instance = None


def get_database(force_new: bool = False) -> Database:
    """
    获取数据库实例（单例模式）
    
    Args:
        force_new: 是否强制创建新实例
        
    Returns:
        Database: 数据库实例
    """
    global _db_instance
    if _db_instance is None or force_new:
        _db_instance = Database()
    return _db_instance


def init_database():
    """初始化数据库（创建表）"""
    db = get_database()
    db.create_tables()
    logger.info("数据库初始化完成")
