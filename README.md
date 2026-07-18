# LLMOps

Minimal LLM + RAG application (FastAPI backend + Vue frontend).

- 开发与验收依据：[PRD.md](./PRD.md)
- 页面生成规范：[UI_GENERATION_RULES.md](./UI_GENERATION_RULES.md)
- 学习指南：[LEARNING.md](./LEARNING.md)

## 快速启动（本地开发）

前置条件：Node.js `22.18+`（Vite 8 要求 Node 20.19+；项目统一使用 Node 22）和 Docker Desktop。

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-full.txt
cp .env.example .env   # 填入 DATABASE_URL，以及实际使用的 GEEKAI_API_KEY / OPENAI_API_KEY
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
# macOS / Linux 全栈：需先打开 Docker Desktop；Embedding 可连接 WinPC Xinference
npm start

# Windows（本机 WSL2 同时运行 Xinference）
npm run start:win

# 仅 API + 前端（数据库已起，或暂不需要落库）
npm run start:app
```

`npm start` 失败并提示 `docker.sock` → Docker Desktop 没开，先启动 Docker 再重试，或用 `npm run start:app`。`npm start` 不依赖 WSL；只有 Windows 主机需要同时拉起 Xinference 时才使用 `npm run start:win`。

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

### 本地 Xinference（Docker + GPU）

```sh
# 需 Docker Desktop + NVIDIA Container Toolkit（--gpus all）
docker compose up xinference -d
```

浏览器打开 http://127.0.0.1:9997 ，在 Web UI 中 Launch 模型（3060 12G 推荐）：

| 类型 | 模型 | 维度 |
|------|------|------|
| Embedding | `bge-base-zh-v1.5` | 768 |
| Chat | `qwen2.5-instruct` 7B | — |

Launch 后复制 Running Models 里的 **model uid**，写入 `.env`（见 `.env.example` 中「本地 Xinference」注释块）。

- 本地 `uvicorn`：`GEEKAI_BASE_URL=http://127.0.0.1:9997/v1`
- `docker compose` 里的 api 容器：`GEEKAI_BASE_URL=http://xinference:9997/v1`

换 embedding 后需删 `./data/faiss_index/` 并重新 ingest。

## 数据存储位置（外置硬盘）

| 路径 | 内容 |
|------|------|
| `./data/postgres/` | PostgreSQL 数据 |
| `./data/faiss_index/` | RAG 向量索引 |
| `./data/xinference/` | Xinference 模型与缓存 |
| `./data/huggingface/` | HuggingFace 下载缓存 |

均在 `.gitignore` 中，不会进 Git。

## Frontend (Vue 3)

```sh
npm install
npm run dev
```
