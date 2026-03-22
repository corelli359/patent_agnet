#!/usr/bin/env python3
"""
启动Patent Search API服务器
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

# 配置日志（同时输出到控制台和文件）
log_file = project_root / "logs" / "patent_api.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),  # 文件
        logging.StreamHandler()  # 控制台
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("启动Patent Search API服务器")
    logger.info("=" * 60)
    logger.info("\n📍 访问地址:")
    logger.info("   - API文档: http://localhost:8000/docs")
    logger.info("   - Redoc: http://localhost:8000/redoc")
    logger.info("   - 健康检查: http://localhost:8000/health\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )
