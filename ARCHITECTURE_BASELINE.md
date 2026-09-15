# Architecture Baseline

- Baseline version: v3.1
- Architecture document: `02_知识库管理平台_标准AI项目架构设计说明书.md`
- SHA-256: `A15D5947F2DCD34CF8A2B5567B7B963D222D7580FA3FB9B0A4EB742432057A43`
- Baseline date: 2026-09-14
- Approval source: 用户明确要求标准 AI 架构、LangGraph 文档导入、多 Agent、结构化模块与架构图；随后明确指定与电商运营助手相同的阿里云环境、Milvus、`/root/myproject` 和 GitHub 仓库，本次只记录不实施。

## 本次文档守卫结果

- Markdown 代码围栏成对闭合；当前包含 Mermaid 架构与工作流图 22 个。
- 需求追踪：原 2.9 组织权限、导入解析、四维鉴权、问答、三路融合、FAQ、知识缺口、看板和云部署均有对应模块、Graph 或测试。
- AI 架构：包含 Agent Harness、四个独立 LangGraph、Agent/State/Node/Tool/Provider 边界、Prompt 与 Schema 版本、Checkpoint、Eval 和可观测性。
- 文档导入：包含独立 `DocumentIngestionGraph`、完整 State、节点状态变化、四个分析 Agent、MinerU、DOC 转换、人工复核、Embedding、索引和发布，并提供流程图、时序图和跨 Graph 关系图。
- 模块结构：包含 apps/packages 分层和 Graph 内 state、nodes、agents、schemas 的独立目录。
- 敏感信息扫描：未发现实际密钥、Bearer Token 或真实 Provider URL。
- 实现守卫：尚未运行。当前目录没有项目代码仓库，不能把文档检查声明为代码架构检查通过。

后续对 Graph 边界、框架、状态所有权、Provider、部署边界或安全规则的实质变更，需要先记录 Architecture Change Proposal，并由用户确认后更新本文件和 SHA-256。
