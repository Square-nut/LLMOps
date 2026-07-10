<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  getRuntimeConfig,
  postEmbeddingCheck,
  postModelCheck,
  postReindex,
  type EmbeddingCheckResponse,
  type ModelCheckResponse,
  type ReindexResponse,
  type RuntimeConfigResponse,
} from '@/api/client'

const config = ref<RuntimeConfigResponse | null>(null)
const modelCheck = ref<ModelCheckResponse | null>(null)
const embeddingCheck = ref<EmbeddingCheckResponse | null>(null)
const reindexResult = ref<ReindexResponse | null>(null)
const error = ref('')
const actionError = ref('')
const loading = ref(false)
const modelChecking = ref(false)
const embeddingChecking = ref(false)
const reindexing = ref(false)

function yesNo(value: boolean) {
  return value ? '是' : '否'
}

function secretLabel(value: { configured: boolean }) {
  return value.configured ? '已配置' : '未配置'
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    config.value = await getRuntimeConfig()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '配置加载失败'
  } finally {
    loading.value = false
  }
}

async function handleModelCheck() {
  modelChecking.value = true
  modelCheck.value = null
  actionError.value = ''
  try {
    modelCheck.value = await postModelCheck()
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : '模型检查失败'
  } finally {
    modelChecking.value = false
  }
}

async function handleEmbeddingCheck() {
  embeddingChecking.value = true
  embeddingCheck.value = null
  actionError.value = ''
  try {
    embeddingCheck.value = await postEmbeddingCheck()
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Embedding 检查失败'
  } finally {
    embeddingChecking.value = false
  }
}

async function handleReindex() {
  if (!confirm('将清空 FAISS 索引，并按数据库中的文档重新 embedding。继续吗？')) return

  reindexing.value = true
  reindexResult.value = null
  actionError.value = ''
  try {
    reindexResult.value = await postReindex()
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : '重建索引失败'
  } finally {
    reindexing.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <div class="settings-page">
    <div class="toolbar">
      <button type="button" class="primary-btn" :disabled="loading" @click="loadConfig">
        {{ loading ? '刷新中…' : '刷新配置' }}
      </button>
      <span class="hint">只读视图：修改 `.env` 后需要重启 API。</span>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="config">
      <section class="section">
        <h2>应用</h2>
        <div class="cards">
          <div class="card">
            <span class="label">环境</span>
            <span class="value">{{ config.app.app_env }}</span>
          </div>
          <div class="card">
            <span class="label">日志级别</span>
            <span class="value">{{ config.app.log_level }}</span>
          </div>
          <div class="card">
            <span class="label">在线 API</span>
            <span class="value" :class="config.app.allow_online_api ? 'ok' : 'warn'">
              {{ yesNo(config.app.allow_online_api) }}
            </span>
          </div>
          <div class="card">
            <span class="label">数据库</span>
            <span class="value" :class="config.database.enabled ? 'ok' : 'warn'">
              {{ config.database.enabled ? '已启用' : '未启用' }}
            </span>
          </div>
        </div>
      </section>

      <section class="section">
        <h2>Chat 模型</h2>
        <div class="cards">
          <div class="card">
            <span class="label">Base URL</span>
            <span class="value mono">{{ config.providers.geekai_base_url }}</span>
          </div>
          <div class="card">
            <span class="label">GeekAI Key</span>
            <span class="value" :class="config.providers.geekai_api_key.configured ? 'ok' : 'warn'">
              {{ secretLabel(config.providers.geekai_api_key) }}
            </span>
          </div>
          <div class="card">
            <span class="label">默认模型</span>
            <span class="value mono">{{ config.routing.default_model }}</span>
          </div>
          <div class="card">
            <span class="label">推理 / 长上下文 / 兜底</span>
            <span class="value mono">
              {{ config.routing.reasoning_model }} / {{ config.routing.long_context_model }} /
              {{ config.routing.fallback_model }}
            </span>
          </div>
        </div>
      </section>

      <section class="section">
        <h2>Embedding</h2>
        <div class="cards">
          <div class="card">
            <span class="label">Provider / Backend</span>
            <span class="value">{{ config.embedding.provider }} / {{ config.embedding.backend }}</span>
          </div>
          <div class="card">
            <span class="label">模型</span>
            <span class="value mono">{{ config.embedding.model }}</span>
          </div>
          <div class="card">
            <span class="label">版本 / 维度</span>
            <span class="value mono">{{ config.embedding.version }} / {{ config.embedding.dim }}</span>
          </div>
          <div class="card">
            <span class="label">设备</span>
            <span class="value">{{ config.embedding.device }}</span>
          </div>
          <div class="card">
            <span class="label">Embedding 服务</span>
            <span class="value mono">{{ config.embedding.api_base || '-' }}</span>
          </div>
          <div class="card">
            <span class="label">Embedding Key</span>
            <span class="value" :class="config.embedding.api_key.configured ? 'ok' : 'muted'">
              {{ secretLabel(config.embedding.api_key) }}
            </span>
          </div>
        </div>
      </section>

      <section class="section">
        <h2>RAG</h2>
        <div class="cards">
          <div class="card">
            <span class="label">FAISS 路径</span>
            <span class="value mono">{{ config.rag.faiss_index_path }}</span>
          </div>
          <div class="card">
            <span class="label">Chunk size / overlap</span>
            <span class="value">{{ config.rag.chunk_size }} / {{ config.rag.chunk_overlap }}</span>
          </div>
          <div class="card">
            <span class="label">Top K</span>
            <span class="value">{{ config.rag.retrieval_top_k }}</span>
          </div>
          <div class="card">
            <span class="label">Mock RAG / Chat</span>
            <span class="value">{{ yesNo(config.mock.rag_enabled) }} / {{ yesNo(config.mock.chat_enabled) }}</span>
          </div>
        </div>
      </section>

      <section class="section">
        <h2>操作</h2>
        <div class="actions">
          <button type="button" class="primary-btn" :disabled="modelChecking" @click="handleModelCheck">
            {{ modelChecking ? '检查中…' : '检查 Chat 模型' }}
          </button>
          <button
            type="button"
            class="primary-btn"
            :disabled="embeddingChecking"
            @click="handleEmbeddingCheck"
          >
            {{ embeddingChecking ? '检查中…' : '检查 Embedding' }}
          </button>
          <button type="button" class="danger-btn" :disabled="reindexing" @click="handleReindex">
            {{ reindexing ? '重建中…' : '重建索引' }}
          </button>
        </div>

        <p v-if="actionError" class="error">{{ actionError }}</p>
        <p v-if="modelCheck" class="success">
          Chat OK：{{ modelCheck.model }} · {{ modelCheck.latency_ms }}ms · {{ modelCheck.reply }}
        </p>
        <p v-if="embeddingCheck" class="success">
          Embedding OK：{{ embeddingCheck.backend }} · {{ embeddingCheck.model }} · dim {{ embeddingCheck.dim }}
        </p>
        <p v-if="reindexResult" class="success">
          重建完成：{{ reindexResult.documents_processed }} 篇文档，{{ reindexResult.chunks_indexed }} 个分块，
          {{ reindexResult.vector_count }} 条向量。
        </p>
      </section>

      <section class="section">
        <h2>说明</h2>
        <ul class="notes">
          <li v-for="note in config.notes" :key="note">{{ note }}</li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.settings-page {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem 2rem;
  max-width: 58rem;
}

.toolbar,
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.section {
  margin-top: 1.5rem;
}

.section h2 {
  font-size: 0.9375rem;
  font-weight: 600;
  margin: 0 0 0.75rem;
}

.cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-radius: 0.75rem;
  background: var(--assistant-bg);
  border: 1px solid var(--border);
}

.label,
.hint,
.notes {
  font-size: 0.8125rem;
  color: #6e6e80;
}

.value {
  font-size: 0.875rem;
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.mono {
  font-family: ui-monospace, monospace;
}

.primary-btn,
.danger-btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--main-bg);
  font-size: 0.875rem;
  cursor: pointer;
}

.primary-btn {
  border-color: var(--accent);
  color: var(--accent);
}

.danger-btn {
  border-color: #e67e22;
  color: #e67e22;
}

.primary-btn:hover:not(:disabled),
.danger-btn:hover:not(:disabled) {
  background: var(--assistant-bg);
}

.primary-btn:disabled,
.danger-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ok,
.success {
  color: var(--accent);
}

.warn,
.error {
  color: #e67e22;
}

.muted {
  color: #8e8e8e;
}

.notes {
  margin: 0;
  padding-left: 1.25rem;
}
</style>
