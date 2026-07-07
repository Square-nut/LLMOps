<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHealth, type HealthResponse } from '@/api/client'

const health = ref<HealthResponse | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    health.value = await getHealth()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法连接后端'
  }
})
</script>

<template>
  <div class="panel">
    <p v-if="error" class="error">{{ error }}</p>

    <div v-else-if="health" class="cards">
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
    </div>

    <p v-else class="loading">检查中…</p>

    <section class="checklist">
      <h2>验收清单</h2>
      <ol>
        <li><code>docker compose up postgres -d</code></li>
        <li><code>npm start</code> 或 <code>npm run start:app</code></li>
        <li>数据库显示「已连接」</li>
        <li>入库后 <code>document_id</code> 有值</li>
        <li>对话后 <code>llm_logs</code> 有新记录</li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.panel {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem 2rem;
  max-width: 48rem;
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
  padding: 1rem 1.25rem;
  border-radius: 0.75rem;
  background: var(--assistant-bg);
  border: 1px solid var(--border);
}

.label {
  font-size: 0.875rem;
  color: #6e6e80;
}

.value {
  font-size: 0.875rem;
  font-weight: 500;
}

.value.ok {
  color: var(--accent);
}

.value.warn {
  color: #e67e22;
}

.error {
  color: var(--error);
}

.loading {
  color: #6e6e80;
}

.checklist {
  margin-top: 2rem;
}

.checklist h2 {
  font-size: 0.9375rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.checklist ol {
  line-height: 2;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: #6e6e80;
}

.checklist code {
  font-size: 0.8125rem;
  background: var(--assistant-bg);
  padding: 0.15rem 0.4rem;
  border-radius: 0.25rem;
  border: 1px solid var(--border);
}
</style>
