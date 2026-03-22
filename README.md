# Autopat 专利全流程产出系统

Autopat 是一套围绕“专利项目”组织的单用户专利产出系统，目标是把模糊创意逐步沉淀为可交付的专利申请底稿，而不是只提供若干彼此孤立的 AI 工具页面。

## 系统目标

围绕一个专利项目，串联以下主流程：

1. 发明意图澄清
2. 现有技术检索与分析
3. 技术交底书生成
4. 权利要求书、说明书、摘要起草
5. 审查模拟
6. 修复建议与交付包输出

当前产品重点是先把单用户场景打磨到可用，优先保证流程完整性、文档一致性和结果可追溯性。

## 当前能力

- 基于 `PatentDraft` 的项目级工作流骨架
- 发明意图、交底书、起草、审查、修复、检索 6 个能力模块
- FastAPI 后端与 React 工作台前端
- SQLite 默认持久化，支持后续切换 MySQL
- Minikube 挂载式部署，不构建业务镜像
- LLM provider 自动回退逻辑

## 仓库结构

```text
backend/           FastAPI 接口与服务编排
frontend-react/    当前主前端（Vite + React）
frontend/          静态原型页面
shared/            数据库、LLM、PDF、向量库等共享基础设施
skills/            各能力模块的 SKILL 文档与脚本
scripts/           初始化、测试、部署、诊断脚本
deploy/            Kubernetes 清单
docs/              产品方案、部署说明、变更记录、发布说明
```

## 快速开始

### 1. 准备环境

- Python 3.10+
- Node.js 18+
- 可选：Minikube

复制配置模板：

```bash
cp .env.example .env
```

至少配置一个 LLM key，例如：

```bash
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key
```

### 2. 启动后端

```bash
pip install -r backend/requirements.txt
python backend/run_server.py
```

默认地址：`http://localhost:8000`

### 3. 启动前端

```bash
cd frontend-react
npm install
npm run dev
```

### 4. 运行测试

```bash
pytest backend/tests -q
```

## 部署

本机 Minikube 部署使用挂载模式，不构建业务镜像：

```bash
bash scripts/deploy_autopat_minikube.sh
```

部署说明见 [Minikube 部署文档](./docs/MINIKUBE_AUTOPAT_DEPLOY.md)。

## 关键文档

- [产品总方案](./docs/PATENT_SYSTEM_BLUEPRINT.md)
- [变更记录](./docs/CHANGELOG.md)
- [首版发布说明](./docs/RELEASE_NOTES_v0.1.0.md)
- [Minikube 部署文档](./docs/MINIKUBE_AUTOPAT_DEPLOY.md)
- [需求文档](./requirements.md)

## 说明

- 仓库默认不提交运行数据、数据库、日志、构建产物和个人配置。
- 本地参考资料如《专利审查指南》PDF 可自行放在 `docs/` 下使用，但不随 Git 仓库分发。
