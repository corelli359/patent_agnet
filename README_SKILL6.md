# Skill 6 专利检索与分析

## 快速开始

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入真实的API密钥
# 至少需要配置：
# - DEEPSEEK_API_KEY
# - SERPAPI_KEY (用于Google Patents检索)
```

### 3. 初始化数据库
```bash
python scripts/init_db.py
```

### 4. 运行测试
```bash
cd backend
pytest tests/ -v
```

## 项目结构
```
patent_agnet/
├── backend/               # Python后端
│   ├── app/              # 应用代码
│   ├── tests/            # 单元测试
│   └── requirements.txt  # Python依赖
├── shared/               # 共享工具
│   ├── utils/           # PDF解析、LLM客户端
│   ├── db/              # 数据库模型
│   └── vector_store/    # Chroma向量库
├── data/                # 数据目录
│   ├── patents/         # 本地专利库
│   ├── vector_db/       # 向量数据库
│   └── patent.db        # SQLite数据库（自动生成）
└── scripts/             # 工具脚本
    └── init_db.py       # 数据库初始化
```

## 核心组件

### PDF解析器
```python
from shared.utils import PDFParser

parser = PDFParser()
text = parser.extract_text("path/to/patent.pdf")
sections = parser.extract_sections("path/to/patent.pdf")
```

### LLM客户端
```python
from shared.utils import LLMClient

# 使用DeepSeek
client = LLMClient(provider="deepseek")
response = client.chat([
    {"role": "user", "content": "你好"}
])

# 文本向量化
embedding = client.embed("待向量化的文本")
```

### 向量数据库
```python
from shared.vector_store.chroma_manager import ChromaManager

chroma = ChromaManager()
chroma.add_documents(
    collection_name="patents",
    documents=["专利文本1", "专利文本2"],
    metadatas=[{"patent_id": "123"}, {"patent_id": "456"}]
)

results = chroma.search(
    collection_name="patents",
    query_texts=["区块链加密"],
    n_results=10
)
```

## 开发计划

### ✅ 阶段1：基础设施（已完成）
- [x] 项目骨架
- [x] PDF解析工具
- [x] LLM抽象层
- [x] 向量数据库管理
- [x] 数据库模型

### 🚧 阶段2：Google Patents集成（进行中）
- [ ] Google Patents客户端
- [ ] 专利元数据解析
- [ ] 检索结果存储

### ⏳ 后续阶段
详见 [Skill 6实施计划](./docs/skill6_implementation_plan.md)

## 注意事项

⚠️ **重要约束**：
- 单元测试只能使用SQLite，禁止连接MySQL
- 开发环境默认使用SQLite（`data/patent.db`）
- 生产环境需配置MySQL环境变量

## 文档
- [Skill 6实施计划](./docs/skill6_implementation_plan.md) - 详细设计
- [任务清单](./docs/task.md) - 开发进度
- [阶段1进度报告](./docs/progress_phase1.md) - 基础设施完成情况
