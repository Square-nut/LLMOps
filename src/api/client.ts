const API_BASE = import.meta.env.VITE_API_BASE || ''

export interface ChatRequest {
  message: string
  user_id?: string
  use_rag?: boolean
  task_type?: string
}

export interface ChatResponse {
  reply: string
  model: string
  tokens: { prompt: number; completion: number; total: number }
  latency_ms: number
  used_rag: boolean
}

export interface IngestTextRequest {
  content: string
  source?: string
}

export interface IngestResponse {
  document_id: string | null
  source: string
  chunks_indexed: number
  embedding_version: string
}

export interface HealthResponse {
  status: string
  env: string
  database: boolean
  allow_online_api: boolean
}

export interface RagStatusResponse {
  status: 'ok' | 'needs_reindex' | 'empty'
  warnings: string[]
  chat_model: string
  embedding: {
    provider: string
    backend: string | null
    model: string
    version: string
    dim: number
    device: string
    api_base: string | null
    ready: boolean
  }
  index: {
    exists: boolean
    path: string
    vector_count: number
    stored_embedding_model: string | null
    stored_embedding_provider: string | null
    stored_embedding_version: string | null
    stored_dim: number | null
    updated_at: string | null
  }
  database: {
    enabled: boolean
    document_count: number
    chunk_count: number
    chunk_versions: Record<string, number>
  }
}

export interface ReindexResponse {
  documents_processed: number
  chunks_indexed: number
  vector_count: number
  embedding_version: string
}

export interface ModelCheckResponse {
  ok: boolean
  model: string
  latency_ms: number
  reply: string
}

export interface EmbeddingCheckResponse {
  ok: boolean
  backend: string
  model: string
  dim: number
  device: string
  api_base: string | null
  sample: string
}

export interface RuntimeConfigResponse {
  app: {
    app_env: string
    log_level: string
    allow_online_api: boolean
  }
  providers: {
    geekai_base_url: string
    geekai_api_key: { configured: boolean }
    openai_api_key: { configured: boolean }
    anthropic_api_key: { configured: boolean }
  }
  database: {
    enabled: boolean
    database_url: { configured: boolean }
  }
  embedding: {
    provider: string
    backend: string
    model: string
    version: string
    dim: number
    device: string
    api_base: string | null
    api_key: { configured: boolean }
  }
  rag: {
    faiss_index_path: string
    chunk_size: number
    chunk_overlap: number
    retrieval_top_k: number
  }
  mock: {
    rag_enabled: boolean
    rag_query: string
    rag_source: string
    chat_enabled: boolean
  }
  routing: {
    default_model: string
    reasoning_model: string
    long_context_model: string
    fallback_model: string
  }
  notes: string[]
}

export interface UsageSummary {
  chat_count: number
  total_tokens: number
  total_prompt_tokens: number
  total_completion_tokens: number
  document_count: number
  chunk_count: number
}

export interface ChatLogItem {
  id: string
  user_id: string | null
  input: string
  output: string
  model: string
  tokens: number
  prompt_tokens: number
  completion_tokens: number
  latency: number
  created_at: string
}

export interface IngestLogItem {
  id: string
  source: string
  content_length: number
  chunk_count: number
  embedding_version: string | null
  created_at: string
}

export interface LogsResponse {
  summary: UsageSummary
  chat_logs: ChatLogItem[]
  ingest_logs: IngestLogItem[]
}

export type ModelType = 'chat' | 'embedding' | 'vision'

export interface ModelConfigInput {
  model_key: string
  display_name: string
  model_type: ModelType
  provider: string
  model_name: string
  endpoint?: string | null
  dimension?: number | null
  enabled: boolean
  notes: string
}

export interface ModelConfig extends ModelConfigInput {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ModelActivationResponse {
  model: ModelConfig
  requires_reindex: boolean
  message: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function getHealth() {
  return request<HealthResponse>('/health')
}

export function postChat(body: ChatRequest) {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function postIngestText(body: IngestTextRequest) {
  return request<IngestResponse>('/api/ingest/text', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getLogs(limit = 50) {
  return request<LogsResponse>(`/api/logs?limit=${limit}`)
}

export function getRagStatus() {
  return request<RagStatusResponse>('/api/rag/status')
}

export function getRuntimeConfig() {
  return request<RuntimeConfigResponse>('/api/config')
}

export function postReindex() {
  return request<ReindexResponse>('/api/rag/reindex', { method: 'POST' })
}

export function postModelCheck() {
  return request<ModelCheckResponse>('/api/rag/model-check', { method: 'POST' })
}

export function postEmbeddingCheck() {
  return request<EmbeddingCheckResponse>('/api/rag/embedding-check', { method: 'POST' })
}

export function getModels() {
  return request<ModelConfig[]>('/api/models')
}

export function createModel(body: ModelConfigInput) {
  return request<ModelConfig>('/api/models', { method: 'POST', body: JSON.stringify(body) })
}

export function updateModel(id: string, body: ModelConfigInput) {
  return request<ModelConfig>(`/api/models/${id}`, { method: 'PUT', body: JSON.stringify(body) })
}

export function deleteModel(id: string) {
  return request<void>(`/api/models/${id}`, { method: 'DELETE' })
}

export function activateModel(id: string) {
  return request<ModelActivationResponse>(`/api/models/${id}/activate`, { method: 'POST' })
}
