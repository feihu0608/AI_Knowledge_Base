# AI 知识库管理平台

面向企业内部试点的多租户知识管理与三路 AI 问答平台。当前代码已建立可运行的 M0/M1 骨架，严格保留 `mock` 与 `live` 的证据边界。

## 当前可运行能力

- 账号密码登录、PBKDF2 安全哈希、JWT、`authz_version` 撤权失效。
- 单直属部门、部门祖先范围、角色功能权限、四维文档 ACL。
- 知识库查询与文档上传；上传原文、版本、个人 ACL、导入任务、Outbox 同事务落库。
- `DocumentIngestionGraph`：校验、MinerU 解析、LLM 文档分析、分块、Embedding、Milvus 写入、发布。
- `KnowledgeAnswerGraph`：本地检索、魔搭 MCP、一般知识三路并行，证据融合、答案生成、引用校验。
- 会话、消息、证据快照和模型调用记录持久化。
- Celery Outbox 派发与导入 Worker。
- Vue 登录、知识库、上传和问答页面。
- PostgreSQL、Redis、Milvus Standalone、Nginx 的 Docker Compose 部署骨架。

当前运行适配器为显式 `mock`。硅基流动、MinerU 和魔搭 MCP 尚未完成真实授权调用，不能把演示结果当成真实 AI 结果。

## Windows 本地演示

后端当前可暂用电商运营助手的虚拟环境验证：

```powershell
cd 'F:\尚硅谷大模型\项目实战\知识库管理平台\backend'
& 'F:\尚硅谷大模型\项目实战\电商运营助手\backend\.venv\Scripts\python.exe' scripts/seed_demo.py --database-url sqlite:///./storage/demo.db --create-schema
$env:DATABASE_URL='sqlite:///./storage/demo.db'
$env:JWT_SECRET='local-development-secret'
./scripts/dev.ps1
```

另开终端：

```powershell
cd 'F:\尚硅谷大模型\项目实战\知识库管理平台\frontend'
npm install --cache .npm-cache
npm run dev
```

访问 `http://127.0.0.1:5173`。虚构演示账号：

- `demo-acme / admin_acme`
- `demo-bravo / admin_bravo`
- 本地默认演示密码：`DemoOnly!2026`

共享或云环境必须通过 `DEMO_ADMIN_PASSWORD` 改写演示密码，正式环境不应保留演示账号。

## 阿里云 Compose 准备

计划检出目录：`/root/myproject/AI_Knowledge_Base`。

```bash
cp .env.example .env
chmod 600 .env
# 填写强密码和 Provider 密钥后：
./manage.sh config
./manage.sh migrate
./manage.sh start
./manage.sh seed-demo   # 仅试点演示环境
```

入口为 `http://服务器IP:${WEB_PORT:-80}`。生产前仍需确定域名/HTTPS、ECS 规格、数据跨境界、备份 RPO/RTO 和真实并发容量。

## 验证

```powershell
python scripts/check_architecture.py
python -m compileall -q backend/apps backend/packages backend/migrations backend/scripts scripts
cd backend
python -m pytest -q
cd ../frontend
npm run build
cd ..
$env:ENV_FILE='.env.example'
docker compose -p ai-knowledge-base --env-file .env.example config --quiet
```

完整需求和架构见 [01_知识库管理平台_需求规格说明书.md](01_知识库管理平台_需求规格说明书.md) 与 [02_知识库管理平台_标准AI项目架构设计说明书.md](02_知识库管理平台_标准AI项目架构设计说明书.md)。
