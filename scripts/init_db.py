#!/usr/bin/env python3
"""
数据库初始化脚本
创建所有必要的表
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.db import init_database
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        init_database()
        logger.info("✅ 数据库初始化成功！")
        logger.info("数据库表已创建：")
        logger.info("  - search_history (检索历史)")
        logger.info("  - patent_metadata (专利元数据)")
        logger.info("  - search_results (检索结果)")
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
