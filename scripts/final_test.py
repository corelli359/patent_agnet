#!/usr/bin/env python3
"""
完整端到端测试：检索 → 分析 → 前端展示
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from backend.app.services.patent_search_service import PatentSearchService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 70)
print("🎯 完整端到端测试")
print("=" * 70)
print("\n📋 测试场景:")
print("  关键词: 大模型 and 敏感词")
print("  日期: 2020-01-01 之后")
print("  数量: 10条")
print("  用户: demo_user")
print()

try:
    # 初始化服务
    logger.info("初始化检索服务...")
    service = PatentSearchService()
    
    # 执行检索
    logger.info("开始检索...")
    results = service.search(
        query="大模型 and 敏感词",
        user_id="demo_user",
        date_range=("2020-01-01", "2026-12-31"),
        max_results=10,
        save_history=True
    )
    
    print("\n" + "=" * 70)
    print(f"✅ 检索成功！")
    print("=" * 70)
    print(f"\n🆔 检索ID: {results['search_id']}")
    print(f"📊 结果数量: {results['result_count']}")
    
    # 显示专利列表
    print("\n" + "=" * 70)
    print("📄 专利列表:")
    print("=" * 70)
    
    for idx, patent in enumerate(results['results'][:5], 1):
        print(f"\n【{idx}】")
        print(f"  专利号: {patent.get('patent_number')}")
        print(f"  标题: {patent.get('title', '')[:60]}...")
        print(f"  链接: {patent.get('link')}")
    
    # 保存分析报告
    if results.get('analysis_report'):
        report_file = project_root / "final_demo_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(results['analysis_report'])
        
        print("\n" + "=" * 70)
        print(f"📊 分析报告已保存: {report_file}")
        print("=" * 70)
        
        # 显示报告预览
        lines = results['analysis_report'].split('\n')[:20]
        print("\n报告预览:")
        print("-" * 70)
        print('\n'.join(lines))
        print("...")
        print("-" * 70)
    
    print("\n" + "=" * 70)
    print("🎉 测试完成！")
    print("=" * 70)
    print("\n💡 下一步:")
    print("  1. 查看完整报告: cat final_demo_report.md")
    print("  2. 打开前端: open frontend/index.html")
    print("  3. API已在运行: http://localhost:8000")
    print("  4. API文档: http://localhost:8000/docs")
    
    service.crawler.close()
    
except Exception as e:
    logger.error(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
