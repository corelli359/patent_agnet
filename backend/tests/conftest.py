"""测试配置"""

import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# 设置测试环境变量
os.environ['ENVIRONMENT'] = 'test'
os.environ['DEEPSEEK_API_KEY'] = 'test_deepseek_key'
os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
os.environ['CLAUDE_API_KEY'] = 'test_claude_key'


@pytest.fixture(scope="session")
def test_db():
    """测试数据库fixture"""
    from shared.db import Database
    
    # 使用内存SQLite数据库
    db = Database(db_url="sqlite:///:memory:")
    db.create_tables()
    
    yield db
    
    # 清理
    db.drop_tables()


@pytest.fixture
def db_session(test_db):
    """数据库会话fixture"""
    with test_db.get_session() as session:
        yield session
