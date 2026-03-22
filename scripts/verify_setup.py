#!/usr/bin/env python3
"""
基础设施验证脚本
验证所有核心组件可正常导入和使用
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_imports():
    """测试所有核心模块导入"""
    logger.info("1. 测试模块导入...")
    
    try:
        from shared.utils import PDFParser, LLMClient, LLMProvider
        logger.info("  ✓ PDF解析器导入成功")
        logger.info("  ✓ LLM客户端导入成功")
        
        from shared.db import Database, SearchHistory, PatentMetadata, SearchResult
        logger.info("  ✓ 数据库模型导入成功")
        
        from shared.vector_store.chroma_manager import ChromaManager
        logger.info("  ✓ Chroma管理器导入成功")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ 导入失败: {e}")
        return False


def test_database():
    """测试数据库连接"""
    logger.info("\n2. 测试数据库...")
    
    try:
        from shared.db import Database
        db = Database(db_url="sqlite:///:memory:")  # 使用内存数据库
        db.create_tables()
        logger.info("  ✓ 数据库表创建成功")
        
        # 测试会话
        with db.get_session() as session:
            logger.info("  ✓ 数据库会话正常")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ 数据库测试失败: {e}")
        return False


def test_pdf_parser():
    """测试PDF解析器"""
    logger.info("\n3. 测试PDF解析器...")
    
    try:
        from shared.utils import PDFParser
        parser = PDFParser()
        logger.info("  ✓ PDF解析器初始化成功")
        
        # 测试文本清洗
        test_text = "  Line 1  \n\n  Line 2  "
        clean = parser._clean_text(test_text)
        assert clean == "Line 1\nLine 2"
        logger.info("  ✓ 文本清洗功能正常")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ PDF解析器测试失败: {e}")
        return False


def test_llm_client():
    """测试LLM客户端"""
    logger.info("\n4. 测试LLM客户端...")
    
    try:
        from shared.utils import LLMProvider
        
        # 测试Provider枚举
        assert LLMProvider.DEEPSEEK.value == "deepseek"
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.CLAUDE.value == "claude"
        logger.info("  ✓ LLM Provider枚举正常")
        
        # 注意：实际API调用需要配置环境变量，这里只测试初始化逻辑
        logger.info("  ⚠ LLM API调用需要配置环境变量（跳过实际调用测试）")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ LLM客户端测试失败: {e}")
        return False


def test_chroma():
    """测试Chroma向量数据库"""
    logger.info("\n5. 测试Chroma向量数据库...")
    
    try:
        from shared.vector_store.chroma_manager import ChromaManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            chroma = ChromaManager(persist_dir=tmpdir)
            logger.info("  ✓ Chroma管理器初始化成功")
            
            # 测试集合创建
            collection = chroma.get_or_create_collection("test_collection")
            logger.info("  ✓ Chroma集合创建成功")
        
        return True
    except Exception as e:
        logger.error(f"  ✗ Chroma测试失败: {e}")
        return False


def main():
    """运行所有验证测试"""
    logger.info("=" * 60)
    logger.info("开始验证Skill 6基础设施...")
    logger.info("=" * 60)
    
    results = []
    results.append(("模块导入", test_imports()))
    results.append(("数据库", test_database()))
    results.append(("PDF解析器", test_pdf_parser()))
    results.append(("LLM客户端", test_llm_client()))
    results.append(("Chroma向量库", test_chroma()))
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("验证结果汇总:")
    logger.info("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        logger.info(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("🎉 所有验证测试通过！基础设施就绪。")
        logger.info("\n下一步：开始阶段2 - Google Patents集成")
        return 0
    else:
        logger.error("⚠️  部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
