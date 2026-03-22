# 专利专家系统 - 任务清单

## 需求分析阶段
- [x] 收集和理解用户需求
  - [x] 确认技术栈(Python后端、Node.js前端、DeepSeek API等)
  - [x] 确认部署方式(本地部署、数据库选型)
  - [x] 确认功能范围(全流程专利能力)
  - [x] 确认采用Agent Skill架构模式
- [x] 创建基于Skill架构的需求文档
  - [x] 项目概述与架构说明
  - [x] 6个核心Skill设计
  - [x] 共享工具设计(PDF解析、向量检索等)
  - [x] 数据库schema设计
  - [x] 技术约束与验收标准
- [ ] 需求评审与确认

## Skill 6实现阶段(进行中)
- [x] 共享基础设施
  - [x] PDF解析工具(pdfplumber)
  - [x] 向量数据库集成(Chroma)
  - [x] LLM抽象层(DeepSeek)
  - [x] 数据库模型与连接层
  - [x] 单元测试配置
- [x] Google Patents检索集成
    - [x] 搜索API封装（GooglePatentsClient）
    - [x] 结果解析与存储（PatentRepository）
    - [x] 检索服务层（PatentSearchService）
    - [x] 单元测试
  - [ ] 检索历史管理
    - [ ] 数据库表设计
    - [ ] 历史记录CRUD
  - [x] 技术方案对比分析
    - [x] 共性关键词提取（jieba + TF-IDF）
    - [x] IPC分类号识别与统计
    - [x] 对比报告生成（Markdown）
  - [/] 前后端集成
    - [x] REST API（FastAPI）
    - [ ] React前端界面
  - [ ] 端到端测试
- [ ] 其他Skill开发(待定)

## 部署与优化(待进行)
- [ ] 本地部署
- [ ] 性能优化
