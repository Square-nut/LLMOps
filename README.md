# LLMOps

Minimal LLM + RAG application skeleton (FastAPI backend + Vue frontend).

- 架构说明：[ARCHITECTURE.md](./ARCHITECTURE.md)
- **学习 / 实现指南：[LEARNING.md](./LEARNING.md)** ← 从这里开始

## 当前状态

**仅基础框架**：目录分层、路由、配置已就绪；业务逻辑为占位（调用返回 HTTP 501）。

## 快速启动（框架）

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- 健康检查：`GET /health`
- API 文档：`http://localhost:8000/docs`
- 实现业务时按 Phase 安装：`requirements-phase1.txt` → Phase 2/3 再 `requirements-full.txt`

## Docker

```sh
docker compose up --build
```

## Frontend (Vue 3)

```sh
npm install
npm run dev
```
