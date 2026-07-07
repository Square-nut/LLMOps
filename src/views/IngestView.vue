<script setup lang="ts">
import { ref } from 'vue'
import { postIngestText, type IngestResponse } from '@/api/client'

const content = ref('')
const source = ref('manual')
const loading = ref(false)
const error = ref('')
const result = ref<IngestResponse | null>(null)

async function submit() {
  const text = content.value.trim()
  if (!text || loading.value) return

  error.value = ''
  result.value = null
  loading.value = true

  try {
    result.value = await postIngestText({
      content: text,
      source: source.value.trim() || 'manual',
    })
    content.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : '入库失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="panel">
    <p class="desc">文本将分块、向量化并写入 FAISS，供 RAG 检索使用。</p>

    <div class="form">
      <label>
        <span class="label-text">来源标识</span>
        <input v-model="source" type="text" placeholder="例如 hr、manual" />
      </label>

      <label>
        <span class="label-text">文档内容</span>
        <textarea
          v-model="content"
          rows="16"
          placeholder="粘贴要入库的文本内容…"
          :disabled="loading"
        />
      </label>

      <button type="button" class="primary-btn" :disabled="loading || !content.trim()" @click="submit">
        {{ loading ? '入库中…' : '提交入库' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="result" class="result-card">
      <h2>入库成功</h2>
      <dl>
        <dt>来源</dt>
        <dd>{{ result.source }}</dd>
        <dt>分块数</dt>
        <dd>{{ result.chunks_indexed }}</dd>
        <dt>Embedding 版本</dt>
        <dd>{{ result.embedding_version }}</dd>
        <dt>文档 ID</dt>
        <dd>{{ result.document_id || '未写入数据库（检查 DATABASE_URL）' }}</dd>
      </dl>
    </div>
  </div>
</template>

<style scoped>
.panel {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem 2rem;
  max-width: 48rem;
}

.desc {
  color: #6e6e80;
  margin-bottom: 1.5rem;
  font-size: 0.9375rem;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.label-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--main-text);
}

.form input,
.form textarea {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--input-border);
  font-family: inherit;
  font-size: 0.9375rem;
  background: var(--input-bg);
  color: var(--main-text);
  line-height: 1.5;
}

.form input:focus,
.form textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(16, 163, 127, 0.15);
}

.primary-btn {
  align-self: flex-start;
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.primary-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: var(--error);
  margin-top: 1rem;
  font-size: 0.875rem;
}

.result-card {
  margin-top: 1.5rem;
  padding: 1.25rem;
  border-radius: 0.75rem;
  background: var(--assistant-bg);
  border: 1px solid var(--border);
}

.result-card h2 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.result-card dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1.5rem;
  margin: 0;
  font-size: 0.875rem;
}

.result-card dt {
  color: #6e6e80;
  font-weight: 500;
}

.result-card dd {
  margin: 0;
  word-break: break-all;
}
</style>
