# LLM RAG App Architecture

## 1. Project Goal

Build a minimal, production-ready LLM application with RAG support.

Constraints:
- 1–2 developers
- API-first
- Fast to ship
- Easy to scale later
- **Hybrid deployment**: Windows runs the product, WSL2 runs Xinference on the RTX 3060
- Default Chat uses a cloud OpenAI-compatible API; local Chat is an optional Xinference model

---

## 2. Core Principles

- Keep system simple (no microservices)
- Single backend (FastAPI)
- No workflow engines in core logic
- Separate concerns strictly:
  - API layer
  - LLM layer
  - RAG / Embedding layer
  - Vision layer (future)
  - Data layer
- **Chat, Embedding, and Vision are independently swappable** via `.env`
- **Business UI lives in LLMOps; model ops UI lives in Xinference** (see §16)

---

## 3. System Architecture

### Target Runtime (Current Direction)

```text
User (Vue Frontend — LLMOps 产品界面)
 ↓
FastAPI Backend (Mac / dev machine)
 ↓
Chat Service ──────────────────→ GeekAI API (OpenAI-compatible)
Ingest Service
Vision Service (future) ───────→ Xinference YOLO (Win PC)
 ↓
RAG Layer (LlamaIndex)
 ↓
Embedding Provider
 ├── mock        → deterministic local vectors (dev only)
 ├── openai      → GeekAI embedding API
 └── local       → HuggingFace via Xinference / TEI
       ├── tei         → remote OpenAI-compatible endpoint (Xinference primary)
       └── huggingface → in-process HF model (optional)
 ↓
FAISS (local vector store)

Win PC (RTX 3060) — Xinference (:9997)
 ├── bge-base-zh-v1.5   → Embedding
 ├── yolo11s            → Vision detection (future)
 └── (optional) local LLM

Data:
- PostgreSQL (Docker, local)
- FAISS index (./data/faiss_index)
```

### Hybrid Deployment Model

### Actual Local Development Topology (2026-07)

```text
Windows
├── Docker Desktop: PostgreSQL (:5432)
├── FastAPI backend (:8000)
└── Vue/Vite frontend (:5173)

WSL2 (NAT address exposed to Windows)
└── Xinference (:9997)
    ├── bge-base-zh-v1.5 — local embedding, 768 dimensions
    └── optional Qwen 7B GGUF — local Chat, Q4 quantization
```

The backend calls Xinference through `EMBEDDING_API_BASE`. The current
adapter sends requests directly to `/v1/embeddings`, so custom Xinference
model UIDs are supported without LlamaIndex's OpenAI model enum. PostgreSQL
stores documents, chunks, versions, and logs; FAISS stores vectors locally.

Xinference is a runtime service and model launch is separate: restarting the
Xinference supervisor can leave `/v1/models` empty, in which case BGE must be
launched again before RAG queries can embed their input.

| Component | Runtime | Provider | Notes |
|-----------|---------|----------|-------|
| Chat LLM | Cloud API | GeekAI | Default; requires a valid `GEEKAI_API_KEY` |
| Chat LLM (optional) | WSL2 GPU | Qwen 7B GGUF via Xinference | RTX 3060 12GB; use Q4 quantization |
| Embedding | WSL2 GPU | BGE via **Xinference** | OpenAI-compatible `/v1` |
| Vision (YOLO) | WSL2 GPU | **Xinference** flexible YOLO | Business logic stays in LLMOps |
| Vector DB | Local | FAISS | Same machine as backend |
| Metadata DB | Local | PostgreSQL | documents / chunks / logs |
| Model ops UI | Win PC | Xinference Web | Admin only; not end-user facing |
| Product UI | Windows | LLMOps Vue | Chat / Ingest / Status / Vision |

**Why hybrid:**
- Chat quality depends on large models → keep cloud API for now
- Embedding + YOLO share one GPU machine → **one Xinference** instead of multiple services
- LLMOps owns product workflows; Xinference owns model runtime only

---

## 4. Tech Stack

### Implemented (Current)

| Layer | Choice | Status |
|-------|--------|--------|
| Backend | FastAPI | ✅ |
| Frontend | Vue 3 + Vite | ✅ |
| LLM Gateway | OpenAI SDK → GeekAI | ✅ (LiteLLM deferred) |
| RAG Framework | LlamaIndex | ✅ |
| Vector DB | FAISS | ✅ |
| Database | PostgreSQL (Docker) | ✅ (Supabase deferred) |
| Chat Provider | GeekAI (cloud) | ✅ |
| Embedding Provider | HuggingFace BGE via Xinference | ✅ configured; Win PC deploy pending |
| Vision Provider | YOLO via Xinference | 🔲 planned |
| Model Platform | Xinference (Win PC) | 🔲 planned; replaces separate TEI + YOLO services |
| Dev Mock | mock embedding + mock chat | ✅ |

### Deferred / Future

### Current Implementation Status

- FastAPI, Vue/Vite, PostgreSQL, LlamaIndex, and FAISS are implemented.
- `bge-base-zh-v1.5` is deployed in WSL2 Xinference on the RTX 3060 and is
  used for both document and query embeddings.
- The local embedding adapter calls Xinference's OpenAI-compatible API
  directly and supports the custom model UID `bge-base-zh-v1.5`.
- RAG restores the complete persisted LlamaIndex state (`docstore.json`,
  `index_store.json`, and the FAISS vector store), rather than trying to
  initialize from FAISS alone.
- `npm start` starts PostgreSQL, Xinference, FastAPI, and Vue; the BGE model
  itself must be launched after Xinference if its model list is empty.
- Local Chat is not the default yet. The planned first candidate is a Qwen
  7B GGUF Q4 model served by Xinference; it can coexist with BGE if context
  length and GPU memory are kept under control.

| Layer | Original Plan | Decision |
|-------|---------------|----------|
| LLM Gateway | LiteLLM | Deferred; OpenAI SDK sufficient for MVP |
| Database | Supabase | Deferred; local Postgres works |
| Vector DB scale | Pinecone | Deferred; FAISS sufficient |
| Local Chat LLM | vLLM / Ollama | Optional; can also run inside Xinference |
| Embedding alt | Standalone TEI | Supported via `EMBEDDING_BACKEND=tei`; Xinference preferred |

### Local Model Tooling (Reference)

| Tool | Role | Used Here? |
|------|------|------------|
| **HuggingFace Hub** | Model source (BGE, YOLO weights) | ✅ |
| **Xinference** | Unified model platform on Win PC (Embedding + YOLO + optional LLM) | ✅ **primary** |
| **TEI** | Standalone embedding server | Optional; same API shape as Xinference embedding |
| **Ollama** | Easy local LLM runner | Optional for chat experiments |
| **Ultralytics YOLO** | Object detection engine | Via Xinference launcher, not a separate service |
| **vLLM** | Production LLM serving | Future, not MVP |

All local deployment options are **free / open-source**. Cost is hardware + electricity only.

---

## 5. Module Structure

```text
app/
  main.py
  api/
    chat.py
    ingest.py
    rag.py          # status / reindex / model-check / embedding-check
    logs.py
  services/
    chat_service.py
    ingest_service.py
    rag_service.py
  rag/
    index.py           # FAISS + embed model factory
    retrieve.py
    chunker.py
    local_embedding.py # HuggingFace / Xinference / TEI adapter
    mock_embedding.py  # dev mock vectors
  vision/              # future
    detector.py        # Xinference YOLO client
    zone_checker.py    # OK/NG position rules
  core/
    llm_gateway.py     # OpenAI SDK → GeekAI
    config.py          # all provider switches
    logger.py
    online_api.py      # ALLOW_ONLINE_API guard
  db/
    postgres.py
  prompts/
    chat_v1.txt

src/                   # Vue frontend
  views/               # Chat, Ingest, Status, Logs, Vision (future)
  api/client.ts
```

---

## 6. Provider Configuration

All provider switches live in `.env`. No code change required to swap.

### Chat (LLM)

```env
GEEKAI_API_KEY=...
GEEKAI_BASE_URL=https://geekai.co/api/v1
DEFAULT_MODEL=...
ALLOW_ONLINE_API=true
```

Future local chat (optional):

```env
GEEKAI_BASE_URL=http://localhost:11434/v1   # Ollama
GEEKAI_API_KEY=ollama
DEFAULT_MODEL=qwen2.5:7b
```

### Embedding

```env
# mock | openai | local
EMBEDDING_PROVIDER=local

# tei (remote Xinference/TEI) | huggingface (in-process)
EMBEDDING_BACKEND=tei
EMBEDDING_MODEL=bge-base-zh-v1.5
EMBEDDING_DIM=768
EMBEDDING_API_BASE=http://192.168.x.x:9997/v1   # Xinference OpenAI-compatible
EMBEDDING_API_KEY=
EMBEDDING_DEVICE=cuda          # only for huggingface backend
```

### Vision (future)

```env
VISION_ENABLED=false
VISION_API_BASE=http://192.168.x.x:9997           # Xinference host (no /v1)
VISION_MODEL=yolo11s
```

| Provider | Use Case | Dim (example) |
|----------|----------|---------------|
| `mock` | Dev / CI without GPU or API | 1536 (configurable) |
| `openai` | Cloud embedding via GeekAI | 1536 |
| `local` + `tei` | Win PC Xinference (or standalone TEI) | 768 (bge-base-zh) |
| `local` + `huggingface` | Same-machine HF load | 768 |

**Rule:** Changing model or dim requires **FAISS reindex**. `embedding_version` tracks this in DB and index meta.

---

## 7. Request Flow

### Chat Flow

1. User sends message (optionally with RAG)
2. FastAPI → `chat_service`
3. If RAG enabled → `retrieve.py` queries FAISS (uses configured embedding provider for query vector)
4. Prompt assembled with retrieved context
5. `llm_gateway.py` → GeekAI API
6. Response returned + logged to `llm_logs`

### Ingest / RAG Flow

1. Document uploaded (text or file)
2. `chunker.py` splits text
3. `index.py` generates embeddings via configured provider
4. Vectors stored in FAISS; metadata in `documents` + `chunks`
5. `embedding_version` recorded per chunk

### Status / Ops Flow

- `GET /api/rag/status` — embedding config, index health, version mismatch warnings
- `POST /api/rag/reindex` — rebuild FAISS from DB documents
- `POST /api/rag/model-check` — probe chat LLM
- `POST /api/rag/embedding-check` — probe embedding service (dim validation)
- `POST /api/rag/vision-check` — probe YOLO service (future)

### Vision Flow (future)

1. Camera frame or uploaded image
2. `vision/detector.py` → Xinference YOLO → bounding boxes
3. `vision/zone_checker.py` → compare boxes to configured zones → OK / NG
4. Result shown on Vision page; optional log to DB

Xinference returns **detection boxes only**. Position rules and product UI remain in LLMOps.

---

## 8. LLM Gateway

### Current Implementation

All chat calls go through `app/core/llm_gateway.py` using **OpenAI SDK** pointed at GeekAI.

Routing strategy (config-driven):
- `simple` → `default_model`
- `reasoning` → `reasoning_model`
- `long_context` → `long_context_model`
- failure → `fallback_model`

### Future: LiteLLM

LiteLLM remains the planned upgrade for multi-provider routing (Anthropic, Gemini, vLLM, Ollama) without changing business logic. Not required for current MVP.

---

## 9. Embedding Layer

### Design

Embedding is a **separate concern** from chat LLM:

```text
_get_embed_model() in index.py
  ├── mock       → MockEmbedding
  ├── openai     → OpenAIEmbedding (GeekAI)
  └── local      → local_embedding.get_local_embed_model()
        ├── tei         → OpenAIEmbedding (Xinference / TEI endpoint)
        └── huggingface → HuggingFaceEmbedding (in-process)
```

### Win PC Deployment (Xinference)

The stable deployment uses WSL2 native Linux rather than a Windows bind
mount or a Docker Xinference container. Docker is reserved for PostgreSQL.
This avoids Windows filesystem permission and Python dependency issues in the
Xinference virtual environment.

```bash
source ~/xinference-runtime/.venv/bin/activate
export XINFERENCE_HOME=$HOME/.xinference
export XINFERENCE_MODEL_SRC=modelscope
export XINFERENCE_ENABLE_VIRTUAL_ENV=0
xinference-local -H 0.0.0.0 --port 9997
```

Windows uses the current WSL IP in `.env`:

```env
EMBEDDING_PROVIDER=local
EMBEDDING_BACKEND=tei
EMBEDDING_MODEL=bge-base-zh-v1.5
EMBEDDING_DIM=768
EMBEDDING_API_BASE=http://<wsl-ip>:9997/v1
```

The API is OpenAI-compatible, but the BGE model must be present in
`GET /v1/models`; otherwise embedding requests return 404.

Primary plan for RTX 3060 machine — **one platform** for Embedding + YOLO:

```powershell
pip install xinference
xinference-local --host 0.0.0.0 --port 9997
```

Web UI: `http://<win-pc-ip>:9997`

1. Launch **embedding** model: `bge-base-zh-v1.5`
2. Register **YOLO** model via flexible launcher (`yolo11s.pt` or custom weights)
3. Mac backend connects:
   - Embedding: `EMBEDDING_API_BASE=http://<win-pc-ip>:9997/v1`
   - Vision: `VISION_API_BASE=http://<win-pc-ip>:9997`

Standalone TEI remains supported if only embedding is needed:

```powershell
docker run --gpus all -p 8080:80 \
  ghcr.io/huggingface/text-embeddings-inference:latest \
  --model-id BAAI/bge-base-zh-v1.5
```

Backend connects via `EMBEDDING_API_BASE=http://<win-pc-ip>:8080/v1`.

### Model Selection

| Model | Dim | VRAM | Notes |
|-------|-----|------|-------|
| `BAAI/bge-small-zh-v1.5` | 512 | ~1 GB | Fast, lighter |
| `BAAI/bge-base-zh-v1.5` | 768 | ~2 GB | **Recommended** for Chinese RAG |
| `BAAI/bge-m3` | 1024 | ~3 GB | Multilingual, heavier |

---

## 10. Database Design (PostgreSQL)

### llm_logs
- id, user_id, input, output, model, tokens, latency, created_at

### documents
- id, content, source, created_at

### chunks
- id, document_id, chunk_text, embedding_version

Originally planned Supabase; current implementation uses local PostgreSQL via Docker. Schema compatible for future migration.

---

## 11. RAG Rules

- Always chunk before embedding
- Keep chunk size 300–800 tokens (current default: 512, overlap 64)
- Store metadata in PostgreSQL
- Keep vector store independent (FAISS)
- Embedding model must be versioned (`embedding_version`)
- **Reindex required** when: model, dim, or provider changes
- Status page surfaces version / dim mismatches as warnings

---

## 12. GPU Extension

### Current: Xinference on Win PC

Win PC (3060) runs **Xinference** for Embedding (+ YOLO later). Backend machine does not need GPU.

Load models on demand; avoid running BGE + YOLO + 7B LLM simultaneously on 12 GB VRAM.

### Future: Local Chat LLM

When needed, swap chat provider without RAG changes:

```env
GEEKAI_BASE_URL=http://<gpu-host>:9997/v1   # Xinference local LLM
# or
GEEKAI_BASE_URL=http://<gpu-host>:11434/v1   # Ollama
```

No changes required in `chat_service` or RAG layer.

---

## 13. What NOT to add (anti-overengineering rules)

Do NOT add:
- Kubernetes
- Kafka / event bus
- microservices
- agent frameworks
- complex workflow engines (n8n in core path)
- forcing Chat and Embedding onto the same local runtime prematurely
- rebuilding Xinference's model management UI inside LLMOps

---

## 14. UI Boundaries: Xinference vs LLMOps

Xinference is **not a replacement** for LLMOps. It is the **model runtime layer**; LLMOps is the **product layer**.

### What each UI is for

| UI | Who uses it | Frequency | Purpose |
|----|-------------|-----------|---------|
| **LLMOps Vue app** | End users + daily dev | Daily | Chat, ingest, logs, vision OK/NG, unified status |
| **Xinference Web** | Admin / ops on Win PC | Occasional | Deploy, start/stop models, GPU monitoring |

### Avoiding a fragmented experience

```text
❌ Bad:  users switch between LLMOps and Xinference for normal work
✅ Good: users only open LLMOps; admin opens Xinference when models change
```

Rules:
1. **All business workflows** (RAG, ingest, zone check, OK/NG) live in LLMOps only
2. **Xinference Web** is internal ops — Win PC LAN only, not linked from product nav
3. **LLMOps `/status`** is the single daily dashboard for service health
4. Xinference models should **auto-start or stay running** so admin UI is rarely needed

### Capability split (why both exist)

| Capability | Xinference | LLMOps |
|------------|------------|--------|
| Run BGE / YOLO / local LLM | ✅ | calls API |
| OpenAI-compatible embedding API | ✅ | consumes API |
| Document ingest / chunking | ❌ | ✅ |
| FAISS index + reindex | ❌ | ✅ |
| RAG retrieve + chat UI | ❌ | ✅ |
| YOLO bounding boxes | ✅ | consumes API |
| Zone check → OK/NG | ❌ | ✅ (future) |
| Camera + product page | ❌ | ✅ (future) |
| Token / ingest logs | ❌ | ✅ |

**Analogy:** Xinference = engine room; LLMOps = bridge.

---

## 15. Status Page: Unified Model Service Dashboard

The Status page (`/status`) is the **single pane of glass** for daily operations. It replaces the need to open Xinference Web for routine checks.

### Current sections

| Section | Checks |
|---------|--------|
| 系统 | API, DB, `ALLOW_ONLINE_API` |
| 在线模型检查 | GeekAI chat (`POST /api/rag/model-check`) |
| Embedding 检查 | Embedding service (`POST /api/rag/embedding-check`) |
| Embedding & 索引 | Config, FAISS health, version/dim warnings, reindex |

### Planned extensions

| Section | Checks | Backend |
|---------|--------|---------|
| **模型服务总览** | Chat / Embedding / Vision readiness at a glance | extend `GET /api/rag/status` → `model_services[]` |
| **Vision 检查** | YOLO infer on sample image | `POST /api/rag/vision-check` (future) |
| Xinference 连通 | Host reachable, models loaded | optional ping to `VISION_API_BASE` / embedding base |

### Planned `model_services` shape (API)

```json
{
  "model_services": [
    {
      "id": "chat",
      "label": "对话 LLM",
      "runtime": "geekai",
      "endpoint": "https://geekai.co/api/v1",
      "ready": true
    },
    {
      "id": "embedding",
      "label": "RAG Embedding",
      "runtime": "xinference",
      "endpoint": "http://192.168.x.x:9997/v1",
      "model": "bge-base-zh-v1.5",
      "ready": false
    },
    {
      "id": "vision",
      "label": "工位检测 YOLO",
      "runtime": "xinference",
      "endpoint": "http://192.168.x.x:9997",
      "model": "yolo11s",
      "ready": false
    }
  ]
}
```

### UX rules

- Show **ready / not ready** per service; manual probe buttons per service
- Do **not** embed Xinference Web in an iframe
- Admin who needs to **swap model weights** still uses Xinference Web on Win PC — link optional in docs only, not in product nav

---

## 16. MVP Milestones

| Phase | Content | Status |
|-------|---------|--------|
| Phase 1 | FastAPI + Chat + GeekAI | ✅ Done |
| Phase 2 | RAG (LlamaIndex + FAISS) | ✅ Done |
| Phase 3 | PostgreSQL logging + persistence | ✅ Done |
| Phase 4 | Frontend (Chat / Ingest / Status / Logs) | ✅ Done |
| Phase 5 | Mock RAG/Chat for offline dev | ✅ Done |
| Phase 6 | HuggingFace local embedding config + remote adapter | ✅ Done (config) |
| Phase 7 | Win PC Xinference deploy + end-to-end local embedding | 🔲 Pending |
| Phase 8 | Status page model service dashboard (`model_services`) | 🔲 Planned |
| Phase 9 | Vision module (YOLO + zone check + page) | 🔲 Planned |
| Phase 10 (optional) | LiteLLM multi-provider gateway | 🔲 Deferred |
| Phase 11 (optional) | Local chat LLM via Xinference | 🔲 Deferred |

---

## 17. Success Criteria

### Updated Progress

- Phase 6 local embedding adapter: complete.
- Phase 7 WSL2 Xinference + BGE end-to-end: complete.
- Windows one-command development startup: complete via `npm start`.
- Local Chat through Xinference: optional next step; Qwen 7B GGUF Q4 is the
  target for the RTX 3060 12GB.

- System runs in single repo
- One command deploy (`npm start`)
- RAG works end-to-end
- LLM logs are stored
- Chat and Embedding providers swappable via `.env` without code changes
- Xinference on Win PC serves Embedding (+ YOLO later); LLMOps serves product UI only
- Daily ops use LLMOps Status page only; Xinference Web is admin-only
- Index version / dim mismatches visible on Status page
