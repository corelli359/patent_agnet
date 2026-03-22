# Skill: 专利申请文件起草 (Patent Drafting)

## 📌 用途
基于技术交底书，生成正式的专利申请文件，包括权利要求书、说明书、摘要。

## 🎯 功能概述
- 权利要求书生成（独立 + 从属）
- 说明书生成（严格遵循审查指南）
- 摘要生成
- 格式与一致性校验

## 📥 输入
- **技术交底书** (`disclosure.md`)
- **可选附图**

## 📤 输出
- `claims.md`：权利要求书
- `specification.md`：说明书
- `abstract.md`：摘要
- `format_check_report.json`：格式检查报告

## 🔧 使用方法

### 命令行使用
```bash
python scripts/claims_generator.py --input disclosure.md
python scripts/specification_generator.py --input disclosure.md
python scripts/abstract_generator.py --input disclosure.md
```

### API调用
```python
from skills.patent_drafting.scripts.claims_generator import ClaimsGenerator

generator = ClaimsGenerator()
claims = generator.generate(
    disclosure_file="disclosure.md",
    num_dependent_claims=5
)
```

## 📋 输出示例

### claims.md
```markdown
# 权利要求书

## 1. 独立权利要求
一种基于区块链的数据加密方法，其特征在于，包括以下步骤：
- 初始化区块链网络，建立分布式节点通信连接；
- 生成主密钥，并将所述主密钥分割为N个密钥分片；
- 将所述N个密钥分片分别存储到区块链网络的不同节点；
- 采用多重签名机制验证数据访问请求，至少需要M个节点签名确认；
- 结合时间锁机制，设置密钥分片的有效期和访问权限。

## 2. 从属权利要求
根据权利要求1所述的方法,其特征在于，所述N的取值范围为5-20，M的取值范围为N/2+1至N。

## 3. 从属权利要求
根据权利要求1所述的方法，其特征在于，所述多重签名机制采用Schnorr签名算法。

## 4. 从属权利要求
根据权利要求1所述的方法，其特征在于，所述时间锁机制包括：
- 设置密钥分片的初始锁定期T1；
- 设置密钥分片的访问冷却期T2；
- 当访问失败次数超过阈值时，延长锁定期至T1 × K。
```

### specification.md
```markdown
# 说明书

## 技术领域
[0001] 本发明涉及数据安全技术领域，具体涉及一种利用区块链技术实现密钥分布式存储的数据加密方法。

## 背景技术
[0002] 传统数据加密方法采用集中式密钥管理...

## 发明内容
[0003] 本发明要解决的技术问题是...
[0004] 为解决上述技术问题，本发明提供一种基于区块链的数据加密方法...
[0005] 本发明的有益效果包括...

## 具体实施方式
[0006] 下面结合具体实施例对本发明进行详细说明...
```

## ⚙️ 配置项
```json
{
  "claims": {
    "max_independent_claims": 1,
    "min_dependent_claims": 3,
    "max_dependent_claims": 10
  },
  "specification": {
    "paragraph_numbering": true,
    "min_embodiments": 1
  },
  "abstract": {
    "min_words": 150,
    "max_words": 300
  }
}
```

## 🔗 依赖
- **参考规范**: `docs/专利审查指南.pdf`
- **LLM**: DeepSeek API
- **模板**: Jinja2

## 📊 核心逻辑

### 权利要求生成
```python
class ClaimsGenerator:
    def generate_independent_claim(self, disclosure):
        """生成独立权利要求"""
        # 1. 提取核心技术特征
        # 2. 组织为"前序+特征"结构
        # 3. 单句表达
        pass
    
    def generate_dependent_claims(self, independent_claim, disclosure):
        """生成从属权利要求"""
        # 1. 识别可细化的技术特征
        # 2. 分层设计（2-3层）
        # 3. 保持引用关系正确
        pass
```

## 🧪 测试
```bash
pytest tests/test_claims_generator.py
pytest tests/test_consistency_checker.py
```

## ✅ 验收标准
- [ ] 至少1条独立权利要求、3条从属权利要求
- [ ] 说明书包含所有必要章节
- [ ] 通过格式校验
- [ ] 权利要求与说明书一致
- [ ] 单元测试覆盖率 > 70%

## 🔄 版本历史
- v1.0 (2026-01-18): 初始版本
