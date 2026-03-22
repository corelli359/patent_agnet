#!/usr/bin/env python3
"""
Selenium版Google Patents测试脚本
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from skills.patent_search.scripts.google_patents_client import GooglePatentsSeleniumCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """测试Selenium爬虫"""
    
    logger.info("=" * 60)
    logger.info("测试Selenium版Google Patents爬虫")
    logger.info("=" * 60)
    logger.info("\n⚠️  首次运行需要安装ChromeDriver:")
    logger.info("   Mac: brew install chromedriver")
    logger.info("   或访问: https://chromedriver.chromium.org/\n")
    
    try:
        # 使用上下文管理器自动关闭浏览器
        with GooglePatentsSeleniumCrawler(headless=True, delay=3.0) as crawler:
            
            # 测试1：基本搜索
            logger.info("\n🔍 测试1: 搜索'blockchain'相关专利")
            logger.info("国家: CN (中国)")
            logger.info("结果数: 5\n")
            
            results = crawler.search(
                query="blockchain",
                country="CN",
                num=5
            )
            
            logger.info(f"\n✅ 搜索成功！找到 {len(results)} 个结果")
            
            if results:
                logger.info("\n" + "=" * 60)
                logger.info("专利列表:")
                logger.info("=" * 60)
                
                for idx, patent in enumerate(results, 1):
                    logger.info(f"\n【{idx}】{patent.get('patent_number', 'N/A')}")
                    logger.info(f"标题: {patent.get('title', 'N/A')}")
                    logger.info(f"链接: {patent.get('link', 'N/A')}")
                
                # 测试2：获取第一个专利的详情
                logger.info("\n" + "=" * 60)
                logger.info("🔍 测试2: 获取专利详情")
                logger.info("=" * 60)
                
                first_patent_id = results[0].get('patent_number')
                if first_patent_id:
                    logger.info(f"\n获取专利: {first_patent_id}\n")
                    
                    detail = crawler.get_patent_detail(first_patent_id)
                    
                    if detail:
                        logger.info(f"✅ 详情获取成功！")
                        logger.info(f"\n专利号: {detail.get('patent_number')}")
                        logger.info(f"标题: {detail.get('title', 'N/A')}")
                        logger.info(f"发明人: {detail.get('inventor', 'N/A')}")
                        logger.info(f"申请人: {detail.get('assignee', 'N/A')}")
                        logger.info(f"公开日期: {detail.get('publication_date', 'N/A')}")
                        
                        if detail.get('ipc_classifications'):
                            logger.info(f"IPC分类: {', '.join(detail['ipc_classifications'])}")
            
            logger.info("\n" + "=" * 60)
            logger.info("🎉 测试完成！")
            logger.info("\n注意:")
            logger.info("- 使用Selenium + Chrome无头模式")
            logger.info("- 每次搜索约需3-5秒（等待页面渲染）")
            logger.info("- 浏览器会自动关闭")
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        logger.error("\n常见问题:")
        logger.error("1. 未安装ChromeDriver: brew install chromedriver")
        logger.error("2. ChromeDriver版本不匹配Chrome版本")
        logger.error("3. 网络连接问题")
        
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
