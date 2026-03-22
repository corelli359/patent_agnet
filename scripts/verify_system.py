#!/usr/bin/env python3
"""
快速验证脚本 - 测试所有组件
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("🔧 系统组件验证")
print("=" * 60)

# 1. 测试导入
print("\n1️⃣ 测试模块导入...")
try:
    from shared.db import get_database, init_database
    from skills.patent_search.scripts import GooglePatentsSeleniumCrawler
    from backend.app.services import PatentSearchService
    print("   ✅ 所有模块导入成功")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    sys.exit(1)

# 2. 测试数据库
print("\n2️⃣ 测试数据库连接...")
try:
    db = get_database()
    with db.get_session() as session:
        print("   ✅ 数据库连接正常")
except Exception as e:
    print(f"   ❌ 数据库失败: {e}")
    sys.exit(1)

# 3. 测试ChromeDriver
print("\n3️⃣ 测试ChromeDriver...")
try:
    import subprocess
    result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True, timeout=2)
    print(f"   ✅ ChromeDriver: {result.stdout.strip()}")
except Exception as e:
    print(f"   ❌ ChromeDriver未安装或不可用: {e}")
    print("      运行: brew install chromedriver")
    sys.exit(1)

# 4. 测试FastAPI
print("\n4️⃣ 测试FastAPI应用...")
try:
    from backend.app.main import app
    print(f"   ✅ FastAPI加载成功: {app.title}")
except Exception as e:
    print(f"   ❌ FastAPI加载失败: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 所有组件验证通过！")
print("=" * 60)
print("\n💡 下一步:")
print("   1. 启动API: python backend/run_server.py")
print("   2. 打开前端: open frontend/index.html")
print("   3. 或运行demo: python scripts/demo_search.py")
