# LLM RAG App Architecture

## 1. Project Goal

Build a minimal, production-ready LLM application with RAG support.

Constraints:
- 1–2 developers
- API-first
- Fast to ship
- Easy to scale later
- External LLM APIs as default
- Optional local GPU support (vLLM)

---

## 2. Core Principles

- Keep system simple (no microservices)
- Single backend (FastAPI)
- No workflow engines in core logic
- Separate concerns strictly:
  - API layer
  - LLM layer
  - RAG layer
  - Data layer

---

## 3. System Architecture

User
 ↓
FastAPI Backend
 ↓
Chat / Ingest Services
 ↓
RAG Layer (LlamaIndex)
 ↓
LLM Gateway (LiteLLM)
 ↓
LLM Providers (OpenAI / Anthropic / Local GPU)

Data:
- Supabase (Postgres)
- Vector Store (FAISS → Pinecone later)

---

## 4. Tech Stack

### Core Backend
- FastAPI

### LLM Gateway
- LiteLLM

### RAG Framework
- LlamaIndex

### Database
- Supabase (Postgres)

### Vector DB
- FAISS (MVP)
- Pinecone (scale)

### LLM Providers
- OpenAI (primary)
- Anthropic (fallback)
- Local GPU (vLLM, optional)

---

## 5. Module Structure

app/
  main.py
  api/
    chat.py
    ingest.py
  services/
    chat_service.py
    ingest_service.py
  rag/
    index.py
    retrieve.py
    chunker.py
  core/
    llm_gateway.py
    logger.py
    config.py
  db/
    supabase.py
  prompts/
    chat_v1.txt

---

## 6. Request Flow

### Chat Flow

1. User sends message
2. FastAPI receives request
3. chat_service handles logic
4. RAG retrieves context (if needed)
5. LiteLLM selects model
6. LLM generates response
7. Response returned
8. Log stored in Supabase

---

## 7. RAG Flow

1. Document uploaded
2. Chunking (LlamaIndex)
3. Embedding generation
4. Store:
   - Vector DB (FAISS)
   - Metadata (Supabase)

---

## 8. LLM Gateway Rules

All LLM calls MUST go through LiteLLM.

Routing strategy:
- simple tasks → gpt-4o-mini
- reasoning → gpt-4.1 / Claude
- long context → Claude
- fallback → secondary provider

Optional future:
- local GPU (vLLM OpenAI-compatible endpoint)

---

## 9. Database Design (Supabase)

### llm_logs
- id
- user_id
- input
- output
- model
- tokens
- latency
- created_at

### documents
- id
- content
- source
- created_at

### chunks
- id
- document_id
- chunk_text
- embedding_version

---

## 10. RAG Rules

- Always chunk before embedding
- Keep chunk size 300–800 tokens
- Store metadata in Supabase
- Keep vector store independent
- Embedding model must be versioned

---

## 11. GPU Extension (Optional)

When needed:

Replace LLM provider in LiteLLM:

OpenAI → vLLM (OpenAI-compatible API)

No changes required in business logic.

---

## 12. What NOT to add (anti-overengineering rules)

Do NOT add:
- Kubernetes
- Kafka / event bus
- microservices
- agent frameworks
- complex workflow engines (n8n in core path)

---

## 13. MVP Milestones

Phase 1:
- FastAPI chat endpoint
- OpenAI integration

Phase 2:
- RAG (LlamaIndex + FAISS)

Phase 3:
- Supabase logging

Phase 4:
- LiteLLM routing

Phase 5 (optional):
- GPU inference (vLLM)

---

## 14. Success Criteria

- System runs in single repo
- One command deploy
- RAG works end-to-end
- LLM logs are stored
- Model can be swapped without code changes