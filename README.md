# LLMOps

Minimal LLM + RAG application (FastAPI backend + Vue frontend).

- 架构说明：[ARCHITECTURE.md](./ARCHITECTURE.md)
- 学习指南：[LEARNING.md](./LEARNING.md)

## 快速启动（本地开发）

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-full.txt
cp .env.example .env   # 填入 GEEKAI_API_KEY
```

### 1. 启动本地数据库（Docker，数据在外置硬盘 ./data/）

```sh
docker compose up postgres -d
```

首次启动会自动执行 `supabase/schema.sql` 建表。数据目录：`./data/postgres/`。

### 2. 启动 API

```sh
uvicorn app.main:app --reload --port 8000
```

- 健康检查：`GET /health`（`database: true` 表示已连上 Postgres）
- API 文档：`http://localhost:8000/docs`

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
