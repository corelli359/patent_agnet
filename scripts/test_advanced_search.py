#!/usr/bin/env python3
"""
测试新的Advanced Search爬虫
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from skills.patent_search.scripts.google_patents_client import GooglePatentsAdvancedCrawler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("🧪 测试Google Patents Advanced Search爬虫")
print("=" * 70)

try:
    crawler = GooglePatentsAdvancedCrawler(headless=True, delay=3.0)
    
    print("\n🔍 搜索: '大模型' 在全文, '敏感词' 在权利要求")
    print("📅 日期: 2020-01-01 之后")
    print("📊 数量: 5条\n")
    
    results = crawler.search(
        keywords=[
            {"term": "大模型", "scope": "TAC"},  # 全文
            {"term": "敏感词", "scope": "CL"}    # 权利要求
        ],
        after_date="2020-01-01",
        num=5
    )
    
    print(f"\n✅ 找到 {len(results)} 个结果\n")
    print("=" * 70)
    
    for idx, patent in enumerate(results, 1):
        print(f"\n【{idx}】")
        print(f"  专利号: {patent.get('patent_number')}")
        print(f"  标题: {patent.get('title', '')[:60]}...")
        print(f"  日期: {patent.get('publication_date')}")
        print(f"  链接: {patent.get('link')}")
    
    print("\n" + "=" * 70)
    
    if results and results[0].get('patent_number'):
        print("✅ 测试成功！专利号提取正常")
    else:
        print("❌ 警告：专利号为空")
    
    crawler.close()
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
