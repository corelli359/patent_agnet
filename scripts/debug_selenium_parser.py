#!/usr/bin/env python3
"""
调试Selenium解析 - 查看实际HTML结构
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from skills.patent_search.scripts.google_patents_client import GooglePatentsSeleniumCrawler
import logging

logging.basicConfig(level=logging.INFO)

print("🔍 调试Selenium解析")
print("=" * 60)

try:
    crawler = GooglePatentsSeleniumCrawler(headless=True, delay=3.0)
    
    print("\n搜索: blockchain")
    print("等待页面加载...\n")
    
    results = crawler.search("blockchain", num=2)
    
    print(f"找到结果: {len(results)}")
    
    for idx, result in enumerate(results, 1):
        print(f"\n【结果 {idx}】")
        print(f"  patent_id: {result.get('patent_id')}")
        print(f"  patent_number: {result.get('patent_number')}")
        print(f"  title: {result.get('title', '')[:50]}...")
        print(f"  link: {result.get('link')}")
    
    # 保存HTML用于调试
    print("\n💾 HTML已保存（在crawler内部）")
    
    crawler.close()
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
