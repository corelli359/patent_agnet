#!/usr/bin/env python3
"""
完整集成测试 - 测试前后端连通
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
import time

API_BASE = "http://localhost:8000"

print("=" * 70)
print("🧪 前后端集成测试")
print("=" * 70)

# 1. 健康检查
print("\n1️⃣ API健康检查...")
try:
    response = requests.get(f"{API_BASE}/api/v1/health", timeout=5)
    print(f"   ✅ 状态: {response.json()}")
except Exception as e:
    print(f"   ❌ 健康检查失败: {e}")
    print("   请确保运行: python backend/run_server.py")
    sys.exit(1)

# 2. 测试检索端点（不实际执行，避免启动Chrome）
print("\n2️⃣ 测试API端点定义...")
print("   ℹ️  可用端点:")
print("   - POST /api/v1/search (检索)")
print("   - POST /api/v1/history (历史)")
print("   - GET /api/v1/search/{id}/results (结果)")
print("   - GET /docs (API文档)")

# 3. 测试历史API（应该返回空或之前的记录）
print("\n3️⃣ 测试检索历史API...")
try:
    response = requests.post(
        f"{API_BASE}/api/v1/history",
        json={"user_id": "test_user", "page": 1, "limit": 10},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 历史记录数: {len(data.get('data', {}).get('items', []))}")
    else:
        print(f"   ⚠️  状态码: {response.status_code}")
except Exception as e:
    print(f"   ❌ 历史API失败: {e}")

print("\n" + "=" * 70)
print("✅ 集成测试完成！")
print("=" * 70)

print("\n💡 下一步:")
print("  1. API文档: http://localhost:8000/docs")
print("  2. 打开前端: open frontend/index.html")
print("  3. 或运行完整检索: python scripts/demo_search.py")

print("\n📝 前端使用说明:")
print("  - 打开 frontend/index.html")
print("  - 填写检索表单")
print("  - 关键词: 大模型 and 敏感词")
print("  - 日期: 2020-01-01")
print("  - 国家: CN")
print("  - 点击检索即可")
