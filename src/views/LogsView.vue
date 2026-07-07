<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getLogs, type LogsResponse } from '@/api/client'

const data = ref<LogsResponse | null>(null)
const error = ref('')
const loading = ref(true)
const activeTab = ref<'chat' | 'ingest'>('chat')

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

function truncate(text: string, max = 80) {
  if (text.length <= max) return text
  return text.slice(0, max) + '…'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getLogs(100)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="logs-page">
    <div class="toolbar">
      <button type="button" class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="data" class="summary-cards">
      <div class="summary-card">
        <span class="num">{{ data.summary.chat_count }}</span>
        <span class="label">对话次数</span>
      </div>
      <div class="summary-card highlight">
        <span class="num">{{ data.summary.total_tokens.toLocaleString() }}</span>
        <span class="label">对话 Token 合计</span>
      </div>
      <div class="summary-card">
        <span class="num">{{ data.summary.total_prompt_tokens.toLocaleString() }}</span>
        <span class="label">Prompt Tokens</span>
      </div>
      <div class="summary-card">
        <span class="num">{{ data.summary.total_completion_tokens.toLocaleString() }}</span>
        <span class="label">Completion Tokens</span>
      </div>
      <div class="summary-card">
        <span class="num">{{ data.summary.document_count }}</span>
        <span class="label">入库文档</span>
      </div>
      <div class="summary-card">
        <span class="num">{{ data.summary.chunk_count }}</span>
        <span class="label">向量分块</span>
      </div>
    </div>

    <div v-if="data" class="tabs">
      <button
        type="button"
        class="tab"
        :class="{ active: activeTab === 'chat' }"
        @click="activeTab = 'chat'"
      >
        对话记录 ({{ data.chat_logs.length }})
      </button>
      <button
        type="button"
        class="tab"
        :class="{ active: activeTab === 'ingest' }"
        @click="activeTab = 'ingest'"
      >
        入库记录 ({{ data.ingest_logs.length }})
      </button>
    </div>

    <div v-if="data && activeTab === 'chat'" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>模型</th>
            <th>Tokens</th>
            <th>延迟</th>
            <th>输入</th>
            <th>输出</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="data.chat_logs.length === 0">
            <td colspan="6" class="empty">暂无对话记录</td>
          </tr>
          <tr v-for="row in data.chat_logs" :key="row.id">
            <td class="time">{{ formatTime(row.created_at) }}</td>
            <td class="model">{{ row.model }}</td>
            <td class="tokens">
              <span class="total">{{ row.tokens }}</span>
              <span class="detail">{{ row.prompt_tokens }}+{{ row.completion_tokens }}</span>
            </td>
            <td>{{ row.latency }}ms</td>
            <td class="text" :title="row.input">{{ truncate(row.input) }}</td>
            <td class="text" :title="row.output">{{ truncate(row.output) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="data && activeTab === 'ingest'" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>来源</th>
            <th>字符数</th>
            <th>分块数</th>
            <th>Embedding</th>
            <th>文档 ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="data.ingest_logs.length === 0">
            <td colspan="6" class="empty">暂无入库记录</td>
          </tr>
          <tr v-for="row in data.ingest_logs" :key="row.id">
            <td class="time">{{ formatTime(row.created_at) }}</td>
            <td>{{ row.source }}</td>
            <td>{{ row.content_length.toLocaleString() }}</td>
            <td>{{ row.chunk_count }}</td>
            <td>{{ row.embedding_version || '-' }}</td>
            <td class="id" :title="row.id">{{ truncate(row.id, 12) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="!data && !error && loading" class="loading-hint">加载日志中…</p>
  </div>
</template>

<style scoped>
.logs-page {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem 2rem;
}

.toolbar {
  margin-bottom: 1.25rem;
}

.refresh-btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: var(--main-bg);
  font-size: 0.875rem;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--assistant-bg);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: var(--error);
  margin-bottom: 1rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  padding: 1rem;
  border-radius: 0.75rem;
  background: var(--assistant-bg);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-card.highlight {
  border-color: var(--accent);
  background: rgba(16, 163, 127, 0.08);
}

.summary-card .num {
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--main-text);
}

.summary-card .label {
  font-size: 0.75rem;
  color: #6e6e80;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}

.tab {
  padding: 0.625rem 1rem;
  border: none;
  background: none;
  font-size: 0.875rem;
  color: #6e6e80;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab.active {
  color: var(--main-text);
  font-weight: 500;
  border-bottom-color: var(--accent);
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 0.75rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

th {
  text-align: left;
  padding: 0.75rem 1rem;
  background: var(--assistant-bg);
  color: #6e6e80;
  font-weight: 500;
  white-space: nowrap;
}

td {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border);
  vertical-align: top;
}

tr:hover td {
  background: rgba(0, 0, 0, 0.02);
}

.empty {
  text-align: center;
  color: #8e8e8e;
  padding: 2rem !important;
}

.time {
  white-space: nowrap;
  color: #6e6e80;
}

.model {
  white-space: nowrap;
}

.tokens .total {
  font-weight: 600;
  display: block;
}

.tokens .detail {
  font-size: 0.75rem;
  color: #8e8e8e;
}

.text {
  max-width: 240px;
}

.id {
  font-family: ui-monospace, monospace;
  font-size: 0.75rem;
  color: #6e6e80;
}

.loading-hint {
  color: #6e6e80;
}
</style>
