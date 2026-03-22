#!/usr/bin/env python3
"""
完整链路测试脚本
测试：检索 → 分析 → 报告生成
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
    """测试完整链路"""
    
    logger.info("=" * 60)
    logger.info("测试Skill 6完整链路")
    logger.info("=" * 60)
    logger.info("\n📋 测试流程:")
    logger.info("1. Google Patents检索")
    logger.info("2. 数据库存储")
    logger.info("3. 关键词分析")
    logger.info("4. IPC分类分析")
    logger.info("5. 生成Markdown报告\n")
    
    try:
        # 初始化服务
        logger.info("初始化检索服务...")
        service = PatentSearchService()
        
        # 执行检索
        logger.info("\n🔍 执行检索: 'blockchain encryption'")
        logger.info("国家: CN")
        logger.info("最大结果数: 5\n")
        
        results = service.search(
            query="blockchain encryption",
            user_id="test_user",
            country="CN",
            max_results=5,
            save_history=True
        )
        
        logger.info(f"\n✅ 检索完成！")
        logger.info(f"检索ID: {results['search_id']}")
        logger.info(f"结果数量: {results['result_count']}")
        
        # 显示专利列表
        logger.info("\n📄 专利列表:")
        for idx, patent in enumerate(results['results'], 1):
            logger.info(f"  {idx}. {patent.get('title', 'N/A')}")
        
        # 保存分析报告
        report = results.get('analysis_report', '')
        if report:
            report_file = project_root / "analysis_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"\n📊 分析报告已生成: {report_file}")
            logger.info("\n报告预览（前500字符）:")
            logger.info("-" * 60)
            logger.info(report[:500] + "...")
            logger.info("-" * 60)
        
        logger.info("\n🎉 完整链路测试成功！")
        logger.info(f"\n💡 下一步:")
        logger.info(f"1. 查看完整报告: cat analysis_report.md")
        logger.info(f"2. 启动API服务: python backend/run_server.py")
        logger.info(f"3. 访问API文档: http://localhost:8000/docs")
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # 关闭浏览器
        if hasattr(service, 'crawler'):
            service.crawler.close()


if __name__ == "__main__":
    main()
