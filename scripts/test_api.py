#!/usr/bin/env python3
"""
测试API端点
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import time

print("🧪 测试API端点连通性\n")

API_BASE = "http://localhost:8000"

# 等待服务器启动
print("⏳ 等待服务器启动...")
for i in range(10):
    try:
        response = requests.get(f"{API_BASE}/", timeout=2)
        if response.status_code == 200:
            print("✅ 服务器已启动\n")
            break
    except:
        time.sleep(1)
else:
    print("❌ 服务器未启动，请运行: python backend/run_server.py")
    sys.exit(1)

# 测试健康检查
print("1️⃣ 测试健康检查...")
try:
    response = requests.get(f"{API_BASE}/api/v1/health")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ {data}")
    else:
        print(f"   ❌ 状态码: {response.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 测试检索（模拟）
print("\n2️⃣ 测试检索端点（模拟请求）...")
try:
    # 这里不真实调用，因为会启动Chrome
    print("   ℹ️  跳过实际检索（避免启动浏览器）")
    print("   💡 使用 python scripts/demo_search.py 进行完整测试")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n✅ API端点测试完成")
print("\n💡 下一步:")
print("  - 打开前端: open frontend/index.html")
print("  - 完整测试: python scripts/demo_search.py")
