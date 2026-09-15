# ACP-001：阿里云环境与 Milvus 架构变更记录

状态：用户已明确批准

日期：2026-09-14

## 变更来源

用户明确说明：知识库管理平台与电商运营助手环境相同，未来在阿里云上线；阿里云项目根目录 `/root/myproject` 已创建；GitHub 仓库为 `https://github.com/feihu0608/AI_Knowledge_Base.git`；向量数据库使用 Milvus；当前只记录，不实施。

## 架构变化

- 云环境从“云厂商待定”变为阿里云 ECS，沿用电商运营助手容器化部署模式。
- 向量存储从 pgvector 候选方案改为 Milvus。
- PostgreSQL 保持业务、tenant、ACL、chunk 正文、任务、Graph Checkpoint 和发布状态的权威事实源。
- Milvus 成为独立向量数据面，通过批量幂等 Synchronizer、Outbox 和 Reconciler 与 PostgreSQL 协调。
- 本地向量召回先在 Milvus 强制按 tenant/index_version 过滤，再回 PostgreSQL 加载当前状态与四维 ACL，最后 Rerank。
- 项目代码根目录建议为 `/root/myproject/AI_Knowledge_Base`，最终目录实施前复核。

## 不变的业务

多租户、单直属部门、部门向下继承、四维 OR 权限、五种文件、MinerU、LangGraph 文档分析、三路问答、FAQ 审核缓存、知识缺口、运营看板、7 日业务日志均保持不变。

## 风险与决策缺口

电商运营助手环境记录为 2 核 4 GiB。Milvus Standalone 还需要自身进程及元数据/对象存储依赖，与 PostgreSQL、Redis、API 和 Worker 同机可能产生明显内存和磁盘压力。本 ACP 不自行决定自建、独立 ECS 或托管形态，必须在实施前完成资源盘点与最小负载验证。

## 本次未执行

没有连接阿里云、访问 GitHub、克隆仓库、安装 Milvus、修改安全组、创建数据卷、配置密钥或调用任何付费服务。
