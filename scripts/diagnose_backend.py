#!/usr/bin/env python3
"""
诊断后端问题
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 诊断后端状态\n")

# 1. 测试模块导入
print("1️⃣ 测试关键模块...")
errors = []

try:
    from shared.db import get_database
    print("   ✅ shared.db")
except Exception as e:
    print(f"   ❌ shared.db: {e}")
    errors.append(("shared.db", e))

try:
    from backend.app.services.patent_search_service import PatentSearchService
    print("   ✅ PatentSearchService")
except Exception as e:
    print(f"   ❌ PatentSearchService: {e}")
    errors.append(("PatentSearchService", e))

try:
    from backend.app.main import app
    print("   ✅ FastAPI app")
except Exception as e:
    print(f"   ❌ FastAPI app: {e}")
    errors.append(("FastAPI app", e))

# 2. 如果有错误，显示详细信息
if errors:
    print("\n" + "="*60)
    print("❌ 发现错误:")
    print("="*60)
    for name, error in errors:
        print(f"\n【{name}】")
        print(f"  错误: {error}")
        import traceback
        traceback.print_exc()
else:
    print("\n✅ 所有模块加载正常")

# 3. 测试数据库
if not errors:
    print("\n2️⃣ 测试数据库...")
    try:
        db = get_database()
        with db.get_session() as session:
            print("   ✅ 数据库连接正常")
    except Exception as e:
        print(f"   ❌ 数据库错误: {e}")
        errors.append(("Database", e))

# 4. 总结
print("\n" + "="*60)
if errors:
    print(f"❌ 发现 {len(errors)} 个问题")
    print("请修复上述错误后重启服务器")
else:
    print("✅ 后端状态正常")
    print("服务器应该可以正常运行")
print("="*60)

sys.exit(1 if errors else 0)
