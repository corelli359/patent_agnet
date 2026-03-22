#!/usr/bin/env python3
"""
调试Google Patents HTML结构
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from bs4 import BeautifulSoup

# 测试URL
url = "https://patents.google.com/?q=blockchain&country=CN&num=5"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

print("正在访问:", url)
response = requests.get(url, headers=headers, timeout=30)

print(f"\n状态码: {response.status_code}")
print(f"内容长度: {len(response.text)} 字符\n")

# 保存HTML到文件查看
output_file = "debug_google_patents.html"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"✅ HTML已保存到: {output_file}")
print("\n解析关键元素:")

soup = BeautifulSoup(response.text, 'html.parser')

# 查找可能的结果容器
print("\n1. 查找 search-result-item:")
items1 = soup.find_all('search-result-item')
print(f"   找到: {len(items1)} 个")

print("\n2. 查找包含'patent'的链接:")
links = soup.find_all('a', href=lambda x: x and 'patent' in x)
print(f"   找到: {len(links)} 个")
if links:
    print("   前3个链接:")
    for link in links[:3]:
        print(f"   - {link.get('href')}: {link.get_text(strip=True)[:50]}")

print("\n3. 查找所有<article>标签:")
articles = soup.find_all('article')
print(f"   找到: {len(articles)} 个")

print("\n4. 查找class包含'result'的元素:")
results = soup.find_all(class_=lambda x: x and 'result' in x.lower() if x else False)
print(f"   找到: {len(results)} 个")
if results:
    for idx, r in enumerate(results[:3]):
        print(f"   [{idx}] tag={r.name}, class={r.get('class')}")

print("\n" + "="*60)
print("建议：打开 debug_google_patents.html 查看实际HTML结构")
