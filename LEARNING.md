# LLMOps 学习指南

本文档配合 [ARCHITECTURE.md](./ARCHITECTURE.md)，按 Phase 自己动手填业务逻辑。

当前仓库是**纯框架**：目录、路由、配置已就绪，业务函数均为 `NotImplementedError` 占位。

---

## 0. 先跑起来

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

验证：

```sh
curl http://localhost:8000/health
# {"status":"ok","env":"development","framework_only":true}

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hi"}'
# HTTP 501，提示去 chat_service 实现 — 说明框架通了
```

浏览器打开 `http://localhost:8000/docs` 可看 Swagger。

---

## 1. 理解分层（最重要）

请求路径固定，**不要跳层**：

```
HTTP 请求
  → api/          只做：校验参数、调用 service、返回响应
  → services/     编排业务流程（先 RAG 再 LLM 再写库）
  → rag/          分块、向量、检索
  → core/         LLM 网关（LiteLLM）
  → db/           Supabase 读写
```

**原则**：`api/` 里不写 LiteLLM；`llm_gateway` 里不写 SQL；RAG 里不调 HTTP。

---

## 2. Phase 1 — Chat + OpenAI

**目标**：`/api/chat` 能真正回复（可先不用 RAG）。

1. 安装 Phase 1 依赖：`pip install -r requirements-phase1.txt`（只需 LiteLLM，不要一次装 full）
2. `.env` 填入 `OPENAI_API_KEY`
3. 实现 `app/core/llm_gateway.py` 的 `completion`：
   - 用 `litellm.completion(model=..., messages=[...])`
   - 先写死 `model="gpt-4o-mini"` 即可
4. 实现 `app/services/chat_service.py` 的 `chat`：
   - 读 `app/prompts/chat_v1.txt` 作为 system prompt
   - 调用 `completion(message, system_prompt=...)`
   - 暂时 `use_rag=False` 或跳过 `retrieve_context`
5. 用 curl 或 `/docs` 测试

**自检**：返回真实 LLM 文本，`latency_ms` / `tokens` 有值。

---

## 3. Phase 2 — RAG（LlamaIndex + FAISS）

**目标**：上传文档后，chat 能带上检索上下文。

实现顺序建议：

| 顺序 | 文件 | 做什么 |
|------|------|--------|
| 1 | `rag/chunker.py` | `SentenceSplitter` 分块 |
| 2 | `rag/index.py` | FAISS 建索引、`add_documents`、持久化到 `data/faiss_index` |
| 3 | `rag/retrieve.py` | `as_retriever` 取 top_k，拼成字符串 |
| 4 | `services/ingest_service.py` | 串联 chunk → index（Supabase 可后做） |
| 5 | `services/chat_service.py` | `use_rag=True` 时先 `retrieve_context` 再 `completion` |

**自检**：

```sh
# 1. 入库
curl -X POST http://localhost:8000/api/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"content":"公司年假是15天","source":"hr"}'

# 2. 提问
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"年假几天？","use_rag":true}'
```

---

## 4. Phase 3 — Supabase 日志

1. 在 Supabase SQL Editor 执行 `supabase/schema.sql`
2. `.env` 配置 `SUPABASE_URL`、`SUPABASE_KEY`
3. 实现 `db/supabase.py` 三个函数（表结构见 ARCHITECTURE §9）
4. 在 `chat_service` / `ingest_service` 里调用

**自检**：Supabase 控制台能看到 `llm_logs` / `documents` / `chunks` 新行。

---

## 5. Phase 4 — LiteLLM 路由

实现 `llm_gateway.select_model` + 在 `completion` 里使用：

- 简单 → `settings.default_model`
- 推理 → `settings.reasoning_model`
- 长上下文 → `settings.long_context_model`
- 失败 → `settings.fallback_model`

`TaskType` 和 `ChatRequest.task_type` 已预留，API 不用改。

---

## 6. 目录速查

```
app/
  main.py              # FastAPI 入口，注册路由
  api/chat.py          # POST /api/chat
  api/ingest.py        # POST /api/ingest/*
  services/            # 你来写编排逻辑
  rag/                 # 你来写 RAG
  core/config.py       # 环境变量（已配好）
  core/llm_gateway.py  # 你来接 LiteLLM
  core/logger.py       # 日志（可直接用）
  db/supabase.py       # 你来写数据库
  prompts/chat_v1.txt  # 系统提示词模板
```

---

## 7. 遇到问题怎么查

| 现象 | 可能原因 |
|------|----------|
| 501 Not Implemented | 正常，说明该 Phase 还没实现 |
| import 报错 litellm | 还没 `pip install -r requirements-phase1.txt` |
| pip 安装 cryptography 失败 | 先升级 pip；Phase 1 用 `requirements-phase1.txt` 而非 full |
| FAISS 目录权限 | 确保 `data/` 可写 |
| Supabase insert 失败 | 表未建 / key 不对 / RLS 策略 |

---

## 8. 下一步你可以问我

按 Phase 学习时，可以直接问例如：

- 「Phase 1 的 `completion` 怎么写？」
- 「帮我 review 一下我的 `chunker.py`」
- 「ingest 和 chat 怎么联调？」

我会按你当前进度讲解，而不是一次性把业务代码全写好。
