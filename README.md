# LLMOps

Minimal LLM + RAG application (FastAPI backend + Vue frontend).

- 架构说明：[ARCHITECTURE.md](./ARCHITECTURE.md)
- 学习指南：[LEARNING.md](./LEARNING.md)

## 快速启动（本地开发）

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-full.txt
cp .env.example .env   # 填入 GEEKAI_API_KEY、DATABASE_URL
```

### 1. 启动本地数据库（Docker，数据在外置硬盘 ./data/）

```sh
# 先打开 Docker Desktop
docker compose up postgres -d
```

首次启动会自动执行 `supabase/schema.sql` 建表。数据目录：`./data/postgres/`。

### 2. 启动 API

```sh
uvicorn app.main:app --reload --port 8000
```

- 健康检查：`GET /health`（`database: true` 表示已连上 Postgres）
- API 文档：`http://localhost:8000/docs`

### 一键启动（推荐）

```sh
# 全栈：需先打开 Docker Desktop
npm start

# 仅 API + 前端（数据库已起，或暂不需要落库）
npm run start:app
```

`npm start` 失败并提示 `docker.sock` → Docker Desktop 没开，先启动 Docker 再重试，或用 `npm run start:app`。

### 分步启动

| 页面 | 路径 | 功能 |
|------|------|------|
| 对话 | `/` | Chat + RAG 开关 |
| 入库 | `/ingest` | 文本入库 |
| 状态 | `/status` | 后端 / 数据库健康检查 |

Vite 已配置代理：`/api` 和 `/health` → `localhost:8000`

### Phase 3 验收

```sh
# 1. 健康检查
curl http://localhost:8000/health

# 2. 入库（写 documents + chunks + FAISS）
curl -X POST http://localhost:8000/api/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content":"公司年假是15天","source":"hr"}'

# 3. RAG 对话（写 llm_logs）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"年假几天？","use_rag":true}'

# 4. 查数据库
docker compose exec postgres psql -U llmops -d llmops -c "SELECT id, model, tokens FROM llm_logs ORDER BY created_at DESC LIMIT 3;"
```

### 一键 Docker（API + Postgres）

```sh
docker compose up --build
```

## 数据存储位置（外置硬盘）

| 路径 | 内容 |
|------|------|
| `./data/postgres/` | PostgreSQL 数据 |
| `./data/faiss_index/` | RAG 向量索引 |

均在 `.gitignore` 中，不会进 Git。

## Frontend (Vue 3)

```sh
npm install
npm run dev
```
