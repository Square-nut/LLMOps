<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getHealth, getLogs, getModels, getRagStatus, type HealthResponse, type LogsResponse, type ModelConfig, type RagStatusResponse } from '@/api/client'

const router = useRouter()
const health = ref<HealthResponse | null>(null)
const logs = ref<LogsResponse | null>(null)
const rag = ref<RagStatusResponse | null>(null)
const models = ref<ModelConfig[]>([])
const loading = ref(false)
const autoRefresh = ref(true)
const lastRefreshedAt = ref<Date | null>(null)
const errors = ref<string[]>([])
let refreshTimer: ReturnType<typeof setInterval> | undefined

const activeChat = computed(() => models.value.find((model) => model.model_type === 'chat' && model.is_active))
const activeEmbedding = computed(() => models.value.find((model) => model.model_type === 'embedding' && model.is_active))
const localModels = computed(() => models.value.filter((model) => model.source === 'local'))
const todayChats = computed(() => {
  const today = new Date().toDateString()
  return logs.value?.chat_logs.filter((item) => new Date(item.created_at).toDateString() === today) ?? []
})
const todayTokens = computed(() => todayChats.value.reduce((sum, item) => sum + item.tokens, 0))
const recentLatency = computed(() => {
  const values = logs.value?.chat_logs.map((item) => item.latency).filter((value) => value >= 0) ?? []
  if (!values.length) return null
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length)
})
const trend = computed(() => {
  const buckets = Array.from({ length: 7 }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() - (6 - index))
    const key = date.toDateString()
    return { key, label: `${date.getMonth() + 1}/${date.getDate()}`, count: 0, tokens: 0 }
  })
  for (const item of logs.value?.chat_logs ?? []) {
    const bucket = buckets.find((entry) => entry.key === new Date(item.created_at).toDateString())
    if (bucket) {
      bucket.count += 1
      bucket.tokens += item.tokens
    }
  }
  const max = Math.max(...buckets.map((item) => item.count), 1)
  return buckets.map((item) => ({ ...item, height: Math.max(item.count ? 14 : 3, Math.round((item.count / max) * 100)) }))
})
const hasTrend = computed(() => trend.value.some((item) => item.count > 0))
const healthState = computed(() => {
  if (!health.value || !rag.value) return { label: '数据未完整', tone: 'muted', text: '部分监控源暂不可用' }
  if (!health.value.database || rag.value.status === 'needs_reindex') return { label: '需要关注', tone: 'warning', text: rag.value.warnings[0] || '请检查系统状态' }
  if (rag.value.status === 'empty' || !rag.value.embedding.ready) return { label: '异常', tone: 'danger', text: rag.value.warnings[0] || 'Embedding 或索引未就绪' }
  return { label: '运行正常', tone: 'success', text: '核心服务和索引状态正常' }
})
const alerts = computed(() => {
  const triggeredAt = lastRefreshedAt.value ? formatTime(lastRefreshedAt.value) : '—'
  const items = errors.value.map((message) => ({ level: '关注', object: '监控数据源', status: '未恢复', message, triggeredAt }))
  if (health.value && !health.value.database) items.push({ level: '异常', object: 'PostgreSQL', status: '未恢复', message: 'PostgreSQL 当前不可连接，请检查数据库服务和连接配置。', triggeredAt })
  if (rag.value?.status === 'needs_reindex') items.push({ level: '关注', object: 'FAISS 索引', status: '待处理', message: rag.value.warnings[0] || 'FAISS 索引与当前 Embedding 配置不一致，需要重建索引。', triggeredAt })
  if (rag.value && (!rag.value.index.exists || !rag.value.embedding.ready)) items.push({ level: '异常', object: !rag.value.index.exists ? 'FAISS 索引' : 'Embedding', status: '未恢复', message: rag.value.warnings[0] || 'FAISS 索引或 Embedding 服务未就绪。', triggeredAt })
  return items
})

function formatNumber(value: number | null | undefined) {
  return value == null ? '—' : value.toLocaleString('zh-CN')
}

function formatTime(value: Date | null) {
  return value ? value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '尚未刷新'
}

function statusText(ok: boolean | undefined, ready = '正常', failed = '异常') {
  if (ok === undefined) return '未采集'
  return ok ? ready : failed
}

async function loadDashboard() {
  loading.value = true
  errors.value = []
  const [healthResult, logsResult, ragResult, modelsResult] = await Promise.allSettled([
    getHealth(), getLogs(200), getRagStatus(), getModels(),
  ])
  const resultMap = [
    ['系统状态', healthResult, health],
    ['使用日志', logsResult, logs],
    ['RAG 状态', ragResult, rag],
    ['模型目录', modelsResult, models],
  ] as const
  for (const [name, result, target] of resultMap) {
    if (result.status === 'fulfilled') {
      target.value = result.value as never
    } else {
      errors.value.push(`${name}：${result.reason instanceof Error ? result.reason.message : '加载失败'}`)
    }
  }
  lastRefreshedAt.value = new Date()
  loading.value = false
}

function openLogs() {
  router.push('/logs')
}

function resetTimer() {
  if (refreshTimer) clearInterval(refreshTimer)
  if (autoRefresh.value) refreshTimer = setInterval(loadDashboard, 30_000)
}

watch(autoRefresh, resetTimer)
onMounted(() => {
  loadDashboard()
  resetTimer()
})
onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <main class="monitor-page">
    <div class="monitor-toolbar">
      <div>
        <p class="page-kicker">SYSTEM OBSERVABILITY</p>
        <h2>系统运行概览</h2>
      </div>
      <div class="toolbar-actions">
        <span class="refresh-time">最近刷新：{{ formatTime(lastRefreshedAt) }}</span>
        <el-switch v-model="autoRefresh" inline-prompt active-text="自动" inactive-text="手动" />
        <el-button :loading="loading" @click="loadDashboard">刷新</el-button>
      </div>
    </div>

    <el-alert
      v-for="error in errors"
      :key="error"
      class="source-error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <section class="hero-grid">
      <article class="health-card" :class="healthState.tone">
        <span class="eyebrow">整体健康度</span>
        <div class="health-main">
          <span class="pulse-dot"></span>
          <strong>{{ healthState.label }}</strong>
        </div>
        <p>{{ healthState.text }}</p>
        <div class="health-models">
          <span>Chat：{{ activeChat?.display_name || rag?.chat_model || '未配置' }}</span>
          <span>Embedding：{{ activeEmbedding?.display_name || rag?.embedding.model || '未配置' }}</span>
        </div>
      </article>

      <article class="metric-card"><span>今日请求数</span><strong>{{ formatNumber(todayChats.length) }}</strong><small>来自已记录的 Chat 日志</small></article>
      <article class="metric-card"><span>今日 Chat Token</span><strong>{{ formatNumber(todayTokens) }}</strong><small>输入与输出合计</small></article>
      <article class="metric-card"><span>平均响应耗时</span><strong>{{ recentLatency == null ? '—' : `${recentLatency} ms` }}</strong><small>最近 {{ logs?.chat_logs.length || 0 }} 条记录</small></article>
      <article class="metric-card"><span>GPU 显存</span><strong>—</strong><small>尚未接入资源采集</small></article>
    </section>

    <section class="dashboard-grid">
      <article class="dashboard-card request-card">
        <header><div><span class="eyebrow">请求与 RAG</span><h3>近 7 日请求趋势</h3></div><span class="card-note">聚合日志</span></header>
        <div v-if="hasTrend" class="bar-chart" aria-label="近七日请求量">
          <div v-for="item in trend" :key="item.key" class="bar-column">
            <span class="bar-value">{{ item.count }}</span>
            <span class="bar" :style="{ height: `${item.height}%` }"></span>
            <span>{{ item.label }}</span>
          </div>
        </div>
        <div v-else class="chart-empty">暂无可绘制的请求趋势</div>
        <div class="rag-stats">
          <div><span>RAG 索引</span><strong :class="rag?.index.exists ? 'success-text' : 'warning-text'">{{ rag?.index.exists ? '已就绪' : '未创建' }}</strong></div>
          <div><span>索引向量数</span><strong>{{ formatNumber(rag?.index.vector_count) }}</strong></div>
          <div><span>平均检索耗时</span><strong>—</strong></div>
          <div><span>空检索率</span><strong>—</strong></div>
        </div>
      </article>

      <article class="dashboard-card model-card">
        <header><div><span class="eyebrow">模型与资源</span><h3>运行状态</h3></div><span class="card-note">实时状态</span></header>
        <div class="status-list">
          <div class="status-row"><span>FastAPI</span><b :class="health ? 'success-text' : 'muted-text'">{{ health ? '可连接' : '未采集' }}</b></div>
          <div class="status-row"><span>PostgreSQL</span><b :class="health?.database ? 'success-text' : 'warning-text'">{{ statusText(health?.database, '已连接', '不可连接') }}</b></div>
          <div class="status-row"><span>FAISS 索引</span><b :class="rag?.index.exists ? 'success-text' : 'warning-text'">{{ statusText(rag?.index.exists, '已就绪', '未创建') }}</b></div>
          <div class="status-row"><span>Embedding</span><b :class="rag?.embedding.ready ? 'success-text' : 'warning-text'">{{ statusText(rag?.embedding.ready, '已就绪', '不可用') }}</b></div>
          <div class="status-row"><span>本地模型登记</span><b>{{ localModels.length }} 个</b></div>
          <div class="status-row"><span>Xinference / GPU</span><b class="muted-text">尚未接入采集</b></div>
        </div>
      </article>

      <article class="dashboard-card token-card">
        <header><div><span class="eyebrow">模型性能</span><h3>Token 与调用</h3></div><span class="card-note">当前已记录</span></header>
        <div class="token-summary">
          <div><strong>{{ formatNumber(logs?.summary.total_prompt_tokens) }}</strong><span>输入 Token</span></div>
          <div><strong>{{ formatNumber(logs?.summary.total_completion_tokens) }}</strong><span>输出 Token</span></div>
          <div><strong>{{ formatNumber(logs?.summary.total_tokens) }}</strong><span>总 Token</span></div>
        </div>
        <p class="muted-copy">模型占比、P95 耗时、失败率将在指标快照接入后展示。</p>
      </article>

      <article class="dashboard-card knowledge-card">
        <header><div><span class="eyebrow">知识库概览</span><h3>索引与入库</h3></div><span class="card-note">当前存量</span></header>
        <div class="knowledge-grid">
          <div><span>文档数</span><strong>{{ formatNumber(logs?.summary.document_count) }}</strong></div>
          <div><span>Chunk 数</span><strong>{{ formatNumber(logs?.summary.chunk_count) }}</strong></div>
          <div><span>今日入库</span><strong>{{ formatNumber(logs?.ingest_logs.filter((item) => new Date(item.created_at).toDateString() === new Date().toDateString()).length) }}</strong></div>
          <div><span>最近重建</span><strong class="small-value">{{ rag?.index.updated_at ? new Date(rag.index.updated_at).toLocaleString('zh-CN') : '—' }}</strong></div>
        </div>
      </article>
    </section>

    <section class="alerts-card">
      <header><div><span class="eyebrow">需要处理</span><h3>告警列表</h3></div><span class="alert-count">{{ alerts.length }} 条待关注</span></header>
      <div v-if="alerts.length" class="alert-list">
        <div v-for="alert in alerts" :key="alert.message" class="alert-row">
          <el-tag :type="alert.level === '异常' ? 'danger' : 'warning'" effect="light">{{ alert.level }}</el-tag>
          <div class="alert-detail"><strong>{{ alert.object }}</strong><span>{{ alert.message }}</span></div>
          <span class="alert-meta">{{ alert.triggeredAt }} · {{ alert.status }}</span>
          <el-button text type="primary" @click="openLogs">查看日志</el-button>
        </div>
      </div>
      <div v-else class="alert-empty"><span class="empty-mark">✓</span><span>当前没有由已接入数据源产生的告警</span><el-button text type="primary" @click="openLogs">查看使用日志</el-button></div>
    </section>
  </main>
</template>

<style scoped>
.monitor-page { flex: 1; overflow-y: auto; padding: 24px 28px 36px; background: #f7f8fa; color: #18202b; }
.monitor-toolbar, .dashboard-card > header, .alerts-card > header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.page-kicker, .eyebrow { margin: 0 0 5px; color: #7c8797; font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
h2, h3 { margin: 0; color: #1d2939; } h2 { font-size: 22px; } h3 { font-size: 16px; }
.toolbar-actions { display: flex; align-items: center; gap: 12px; }.refresh-time, .card-note { color: #7c8797; font-size: 12px; }.source-error { margin-top: 14px; }
.hero-grid { display: grid; grid-template-columns: minmax(280px, 1.45fr) repeat(4, minmax(145px, 1fr)); gap: 14px; margin: 20px 0 14px; }
.health-card, .metric-card, .dashboard-card, .alerts-card { border: 1px solid #e6e9ef; border-radius: 12px; background: #fff; box-shadow: 0 1px 2px rgba(16, 24, 40, .03); }
.health-card { padding: 18px 20px; border-left: 4px solid #98a2b3; }.health-card.success { border-left-color: #12b76a; }.health-card.warning { border-left-color: #f79009; }.health-card.danger { border-left-color: #f04438; }
.health-main { display: flex; align-items: center; gap: 10px; margin-top: 6px; }.health-main strong { font-size: 22px; }.pulse-dot { width: 10px; height: 10px; border-radius: 99px; background: #12b76a; }.warning .pulse-dot { background: #f79009; }.danger .pulse-dot { background: #f04438; }.muted .pulse-dot { background: #98a2b3; }
.health-card p { margin: 8px 0; color: #667085; font-size: 13px; }.health-models { display: flex; flex-direction: column; gap: 4px; color: #475467; font-size: 12px; }
.metric-card { display: flex; flex-direction: column; justify-content: center; min-height: 112px; padding: 16px; }.metric-card > span, .metric-card small { color: #667085; font-size: 12px; }.metric-card strong { margin: 8px 0 4px; color: #101828; font-size: 22px; }
.dashboard-grid { display: grid; grid-template-columns: 1.35fr 1fr; gap: 14px; }.dashboard-card { min-height: 264px; padding: 18px; }.dashboard-card > header, .alerts-card > header { padding-bottom: 15px; border-bottom: 1px solid #eef1f5; }
.bar-chart { display: flex; height: 132px; align-items: end; justify-content: space-between; gap: 12px; padding: 12px 5px 0; }.bar-column { display: flex; flex: 1; min-width: 26px; height: 100%; flex-direction: column; align-items: center; justify-content: end; gap: 5px; color: #7c8797; font-size: 11px; }.bar { width: 100%; max-width: 36px; min-height: 3px; border-radius: 4px 4px 1px 1px; background: linear-gradient(180deg, #4778e8, #88aaf4); }.bar-value { color: #475467; font-size: 11px; }.chart-empty { display: grid; height: 132px; place-items: center; color: #98a2b3; font-size: 13px; }
.rag-stats, .token-summary, .knowledge-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 16px; }.rag-stats div, .knowledge-grid div { display: flex; flex-direction: column; gap: 5px; }.rag-stats span, .knowledge-grid span, .token-summary span { color: #7c8797; font-size: 12px; }.rag-stats strong, .knowledge-grid strong { color: #344054; font-size: 14px; }
.status-list { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 20px; }.status-row { display: flex; justify-content: space-between; padding: 13px 0; border-bottom: 1px solid #f0f2f5; color: #475467; font-size: 13px; }.status-row b { color: #344054; font-weight: 600; }.success-text { color: #079455 !important; }.warning-text { color: #b54708 !important; }.muted-text { color: #98a2b3 !important; }
.token-summary { grid-template-columns: repeat(3, 1fr); margin-top: 24px; }.token-summary div { display: flex; flex-direction: column; gap: 7px; padding: 12px; background: #f8faff; border-radius: 8px; }.token-summary strong { font-size: 19px; }.muted-copy { margin-top: 19px; color: #98a2b3; font-size: 12px; }.knowledge-grid { grid-template-columns: repeat(2, 1fr); margin-top: 22px; gap: 22px; }.knowledge-grid strong { font-size: 21px; }.knowledge-grid .small-value { font-size: 12px; line-height: 1.5; }
.alerts-card { margin-top: 14px; padding: 18px; }.alert-count { color: #b54708; font-size: 12px; }.alert-list { display: flex; flex-direction: column; }.alert-row, .alert-empty { display: flex; align-items: center; gap: 12px; padding-top: 14px; color: #475467; font-size: 13px; }.alert-detail { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 3px; }.alert-detail strong { color: #344054; font-size: 13px; }.alert-detail span { overflow: hidden; color: #667085; text-overflow: ellipsis; white-space: nowrap; }.alert-meta { flex-shrink: 0; color: #98a2b3; font-size: 12px; }.alert-empty { color: #667085; }.empty-mark { display: inline-grid; width: 21px; height: 21px; place-items: center; border-radius: 99px; background: #ecfdf3; color: #079455; font-weight: 700; }
@media (max-width: 1320px) { .hero-grid { grid-template-columns: minmax(280px, 1.4fr) repeat(2, 1fr); }.dashboard-grid { grid-template-columns: 1fr; } }
</style>
