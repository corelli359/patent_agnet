#!/usr/bin/env python3
"""
演示脚本：大模型+敏感词专利检索
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from backend.app.services.patent_search_service import PatentSearchService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """演示：大模型+敏感词检索"""
    
    logger.info("=" * 70)
    logger.info("演示：专利检索与分析")
    logger.info("=" * 70)
    logger.info("\n📋 检索条件:")
    logger.info("  关键词: 大模型 and 敏感词")
    logger.info("  时间范围: 2020年之后")
    logger.info("  结果数量: 10条（演示用，可改为30）")
    logger.info("  国家: CN (中国)\n")
    
    try:
        # 初始化服务
        logger.info("⚙️  初始化检索服务...")
        service = PatentSearchService()
        
        # 执行检索
        logger.info("\n🔍 开始检索...")
        logger.info("⏳ 这可能需要30-60秒（Selenium渲染）...\n")
        
        results = service.search(
            query="大模型 and 敏感词",
            user_id="demo_user",
            country="CN",
            date_range=("2020-01-01", "2026-12-31"),
            max_results=10,  # 改为30可获取更多结果
            save_history=True
        )
        
        logger.info(f"\n✅ 检索完成！")
        logger.info(f"🆔 检索ID: {results['search_id']}")
        logger.info(f"📊 结果数量: {results['result_count']}")
        
        # 显示专利列表
        logger.info("\n" + "=" * 70)
        logger.info("📄 专利列表:")
        logger.info("=" * 70)
        
        for idx, patent in enumerate(results['results'], 1):
            logger.info(f"\n【{idx}】")
            logger.info(f"  标题: {patent.get('title', 'N/A')}")
            logger.info(f"  专利号: {patent.get('patent_number', 'N/A')}")
            if patent.get('publication_date'):
                logger.info(f"  公开日期: {patent['publication_date']}")
            if patent.get('link'):
                logger.info(f"  链接: {patent['link']}")
        
        # 保存分析报告
        if results.get('analysis_report'):
            report_file = project_root / "demo_analysis_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(results['analysis_report'])
            
            logger.info("\n" + "=" * 70)
            logger.info(f"📊 分析报告已保存: {report_file}")
            logger.info("=" * 70)
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 演示完成！")
        logger.info("=" * 70)
        logger.info("\n💡 下一步:")
        logger.info("  1. 查看分析报告: cat demo_analysis_report.md")
        logger.info("  2. 启动Web服务: python backend/run_server.py")
        logger.info("  3. 打开浏览器: file:///$(pwd)/frontend/index.html")
        logger.info("  4. 在Web界面中查看结果和历史记录")
        
    except Exception as e:
        logger.error(f"\n❌ 检索失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # 关闭浏览器
        if hasattr(service, 'crawler') and service.crawler:
            service.crawler.close()


if __name__ == "__main__":
    main()
