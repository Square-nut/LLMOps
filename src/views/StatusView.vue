<script setup lang="ts">
import { ref } from 'vue'
import { getHealth, getRagStatus, postReindex, type HealthResponse, type RagStatusResponse } from '@/api/client'

const health = ref<HealthResponse | null>(null)
const ragStatus = ref<RagStatusResponse | null>(null)
const error = ref('')
const ragError = ref('')
const loading = ref(false)
const checked = ref(false)
const reindexing = ref(false)
const reindexMessage = ref('')

function statusLabel(status: string) {
  if (status === 'ok') return '正常'
  if (status === 'needs_reindex') return '需要重建'
  if (status === 'empty') return '空'
  return status
}

function statusClass(status: string) {
  if (status === 'ok') return 'ok'
  if (status === 'empty') return 'muted'
  return 'warn'
}

function providerLabel(provider: string) {
  if (provider === 'mock') return 'Mock（本地）'
  if (provider === 'local') return '本地'
  return '云端'
}

async function loadAll() {
  loading.value = true
  error.value = ''
  ragError.value = ''
  try {
    health.value = await getHealth()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法连接后端'
  }
  try {
    ragStatus.value = await getRagStatus()
  } catch (e) {
    ragError.value = e instanceof Error ? e.message : '无法加载 RAG 状态'
  } finally {
    loading.value = false
    checked.value = true
  }
}

async function handleReindex() {
  if (!confirm('将清空 FAISS 索引，并按数据库中的文档重新 embedding。继续吗？')) return

  reindexing.value = true
  reindexMessage.value = ''
  ragError.value = ''
  try {
    const result = await postReindex()
    reindexMessage.value = `重建完成：${result.documents_processed} 篇文档，${result.chunks_indexed} 个分块，索引向量 ${result.vector_count}`
    ragStatus.value = await getRagStatus()
  } catch (e) {
    ragError.value = e instanceof Error ? e.message : '重建失败'
  } finally {
    reindexing.value = false
  }
}
</script>

<template>
  <div class="panel">
    <div class="toolbar">
      <button type="button" class="refresh-btn" :disabled="loading || reindexing" @click="loadAll">
        {{ loading ? '检查中…' : '检查状态' }}
      </button>
    </div>

    <p v-if="!checked && !loading" class="hint-top">状态检查不会调用在线 API，请点击「检查状态」手动触发。</p>

    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="health" class="section">
      <h2>系统</h2>
      <div class="cards">
        <div class="card">
          <span class="label">API</span>
          <span class="value ok">{{ health.status }}</span>
        </div>
        <div class="card">
          <span class="label">环境</span>
          <span class="value">{{ health.env }}</span>
        </div>
        <div class="card">
          <span class="label">数据库</span>
          <span class="value" :class="health.database ? 'ok' : 'warn'">
            {{ health.database ? '已连接' : '未配置' }}
          </span>
        </div>
        <div class="card">
          <span class="label">在线 API</span>
          <span class="value" :class="health.allow_online_api ? 'ok' : 'warn'">
            {{ health.allow_online_api ? '已启用' : '已禁用' }}
          </span>
        </div>
      </div>
    </section>

    <p v-if="loading && !checked" class="loading">检查中…</p>
    <p v-if="ragError" class="error">{{ ragError }}</p>
    <p v-if="reindexMessage" class="success">{{ reindexMessage }}</p>

    <section v-if="ragStatus" class="section">
      <div class="section-head">
        <h2>Embedding & 索引</h2>
        <span class="badge" :class="statusClass(ragStatus.status)">
          {{ statusLabel(ragStatus.status) }}
        </span>
      </div>

      <ul v-if="ragStatus.warnings.length" class="warnings">
        <li v-for="(item, i) in ragStatus.warnings" :key="i">{{ item }}</li>
      </ul>

      <div class="cards">
        <div class="card">
          <span class="label">对话模型</span>
          <span class="value">{{ ragStatus.chat_model }}</span>
        </div>
        <div class="card">
          <span class="label">Embedding 来源</span>
          <span class="value">{{ providerLabel(ragStatus.embedding.provider) }}</span>
        </div>
        <div class="card">
          <span class="label">Embedding 模型</span>
          <span class="value mono">{{ ragStatus.embedding.model }}</span>
        </div>
        <div class="card">
          <span class="label">版本标识</span>
          <span class="value mono">{{ ragStatus.embedding.version }}</span>
        </div>
        <div class="card">
          <span class="label">向量维度</span>
          <span class="value">{{ ragStatus.embedding.dim }}</span>
        </div>
        <div class="card">
          <span class="label">设备</span>
          <span class="value">{{ ragStatus.embedding.device }}</span>
        </div>
        <div class="card">
          <span class="label">Embedding 就绪</span>
          <span class="value" :class="ragStatus.embedding.ready ? 'ok' : 'warn'">
            {{ ragStatus.embedding.ready ? '是' : '否' }}
          </span>
        </div>
        <div class="card">
          <span class="label">FAISS 索引</span>
          <span class="value" :class="ragStatus.index.exists ? 'ok' : 'muted'">
            {{ ragStatus.index.exists ? '已存在' : '未创建' }}
          </span>
        </div>
        <div class="card">
          <span class="label">索引向量数</span>
          <span class="value">{{ ragStatus.index.vector_count }}</span>
        </div>
        <div class="card">
          <span class="label">DB 文档 / 分块</span>
          <span class="value">
            {{ ragStatus.database.document_count }} / {{ ragStatus.database.chunk_count }}
          </span>
        </div>
        <div class="card">
          <span class="label">索引版本</span>
          <span class="value mono">{{ ragStatus.index.stored_embedding_version || '-' }}</span>
        </div>
        <div class="card">
          <span class="label">索引维度</span>
          <span class="value">{{ ragStatus.index.stored_dim ?? '-' }}</span>
        </div>
      </div>

      <p class="path">索引路径：{{ ragStatus.index.path }}</p>

      <div v-if="Object.keys(ragStatus.database.chunk_versions).length" class="versions">
        <span class="versions-label">DB 分块版本分布：</span>
        <span
          v-for="(count, version) in ragStatus.database.chunk_versions"
          :key="version"
          class="version-tag"
        >
          {{ version }} ({{ count }})
        </span>
      </div>

      <div class="actions">
        <button
          type="button"
          class="reindex-btn"
          :disabled="reindexing || !ragStatus.database.enabled"
          @click="handleReindex"
        >
          {{ reindexing ? '重建中…' : '重建索引' }}
        </button>
        <span v-if="!ragStatus.database.enabled" class="hint">需要配置数据库后才能从 DB 重建</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.panel {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem 2rem;
  max-width: 52rem;
}

.hint-top {
  font-size: 0.8125rem;
  color: #6e6e80;
  margin-bottom: 1rem;
}

.toolbar {
  margin-bottom: 1rem;
}

.refresh-btn,
.reindex-btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--main-bg);
  font-size: 0.875rem;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled),
.reindex-btn:hover:not(:disabled) {
  background: var(--assistant-bg);
}

.refresh-btn:disabled,
.reindex-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reindex-btn {
  border-color: var(--accent);
  color: var(--accent);
}

.section {
  margin-top: 1.5rem;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.section h2 {
  font-size: 0.9375rem;
  font-weight: 600;
  margin: 0;
}

.badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--border);
}

.badge.ok {
  color: var(--accent);
  border-color: var(--accent);
}

.badge.warn {
  color: #e67e22;
  border-color: #e67e22;
}

.badge.muted {
  color: #8e8e8e;
}

.warnings {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem 0.75rem 2rem;
  background: rgba(230, 126, 34, 0.08);
  border: 1px solid rgba(230, 126, 34, 0.25);
  border-radius: 0.75rem;
  font-size: 0.8125rem;
  color: #9a6700;
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

.label {
  font-size: 0.875rem;
  color: #6e6e80;
  flex-shrink: 0;
}

.value {
  font-size: 0.875rem;
  font-weight: 500;
  text-align: right;
}

.value.mono {
  font-family: ui-monospace, monospace;
  font-size: 0.8125rem;
}

.value.ok {
  color: var(--accent);
}

.value.warn {
  color: #e67e22;
}

.value.muted {
  color: #8e8e8e;
}

.path {
  margin-top: 0.75rem;
  font-size: 0.75rem;
  color: #8e8e8e;
  word-break: break-all;
}

.versions {
  margin-top: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.versions-label {
  font-size: 0.8125rem;
  color: #6e6e80;
}

.version-tag {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 0.375rem;
  background: var(--assistant-bg);
  border: 1px solid var(--border);
  font-family: ui-monospace, monospace;
}

.actions {
  margin-top: 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.hint {
  font-size: 0.75rem;
  color: #8e8e8e;
}

.error {
  color: var(--error);
}

.success {
  color: var(--accent);
  margin-bottom: 0.75rem;
}

.loading {
  color: #6e6e80;
}
</style>
