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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
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
