# 专利专家系统 (Patent Expert System)

## 项目简介

专利专家系统是一个基于AI的全流程专利辅助工具，采用Agent Skill架构，帮助企业工程师高效完成从技术创意到专利授权的完整流程。

## 核心特性

- 🎯 **模块化设计**：6个独立Skill，可组合使用
- 📝 **规范输出**：严格遵循《专利审查指南》
- 🔍 **智能检索**：多源专利数据检索与分析
- 🤖 **AI辅助**：基于DeepSeek/Gemini/Claude的智能生成
- 💾 **本地部署**：数据安全，支持离线工作

## 技术栈

- **后端**: Python 3.10+ (FastAPI)
- **前端**: Node.js 18+ (React)
- **数据库**: SQLite (测试) / MySQL (生产)
- **向量库**: Chroma
- **LLM**: DeepSeek API (主力), Gemini/Claude (备选)

## 项目结构

```
patent_agnet/
├── docs/                    # 📚 项目文档
│   ├── task.md              # 任务清单
│   ├── skill6_implementation_plan.md  # Skill 6实施计划
│   └── 专利审查指南.pdf      # 专利格式规范
├── skills/                  # 6个核心Skill
│   ├── invention_intent/    # 发明意图总结
│   ├── disclosure_writing/  # 技术交底书撰写
│   ├── patent_drafting/     # 专利申请文件起草
│   ├── patent_examination/  # 实质审查模拟
│   ├── patent_repair/       # 专利修复
│   └── patent_search/       # 专利检索与分析
├── shared/                  # 共享基础设施
│   ├── utils/               # PDF解析、LLM客户端等
│   ├── db/                  # 数据库层
│   └── vector_store/        # 向量数据库管理
├── backend/                 # Python后端
├── frontend/                # React前端
├── data/                    # 数据目录
│   ├── patents/             # 本地专利库
│   └── vector_db/           # Chroma数据库
├── requirements.md          # 📋 需求文档
└── README.md                # 本文件
```

## 6大核心Skill

| Skill | 功能 | 输入 | 输出 |
|-------|------|------|------|
| **1. 发明意图总结** | 多轮对话引导，生成发明意图文档 | 技术创意描述 | `invention_intent.md` |
| **2. 技术交底书撰写** | 生成规范的技术交底书 | 发明意图/技术方案 | `disclosure.md` |
| **3. 专利申请文件起草** | 生成权利要求书、说明书、摘要 | 技术交底书 | `claims.md`, `specification.md` |
| **4. 实质审查模拟** | 模拟审查员审查，识别缺陷 | 专利申请文件 | 缺陷识别报告 |
| **5. 专利修复** | 解析审查意见，提供修改方案 | 审查意见通知书 | 答复意见书、修改后文件 |
| **6. 专利检索与分析** | 多源检索，新颖性/创造性分析 | 技术关键词/方案 | 检索报告、对比分析 |

## 快速开始

### 环境要求
- Python ≥ 3.10
- Node.js ≥ 18.0
- MySQL（可选，用于生产环境）

### 安装依赖
```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 配置API Key
创建 `.env` 文件：
```bash
DEEPSEEK_API_KEY=your_api_key_here
# 可选
GEMINI_API_KEY=your_gemini_key
CLAUDE_API_KEY=your_claude_key
```

### 运行
```bash
# 后端
cd backend
uvicorn app.main:app --reload

# 前端
cd frontend
npm run dev
```

## 文档

- [需求文档](./requirements.md) - 详细的功能需求和Skill设计
- [任务清单](./docs/task.md) - 开发任务追踪
- [Skill 6实施计划](./docs/skill6_implementation_plan.md) - 专利检索模块详细设计
- [Minikube 部署说明](./docs/MINIKUBE_AUTOPAT_DEPLOY.md) - 本机 k8s 挂载部署与访问方式
- [专利审查指南](./docs/专利审查指南.pdf) - 输出格式规范依据

## 开发计划

当前正在实施：**Skill 6 - 专利检索与分析**

详见 [Skill 6实施计划](./docs/skill6_implementation_plan.md)

## 许可证

本项目为个人使用项目，暂不开源。

---

**作者**: 企业工程师  
**创建日期**: 2026-01-18
