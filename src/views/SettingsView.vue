<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getRuntimeConfig, type RuntimeConfigResponse } from '@/api/client'

const router = useRouter()
const config = ref<RuntimeConfigResponse | null>(null)
const error = ref('')
const loading = ref(false)
const showDetails = ref(false)

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

onMounted(loadConfig)
</script>

<template>
  <main class="settings-page">
    <div class="page-toolbar">
      <div>
        <p class="eyebrow">RUNTIME CONFIGURATION</p>
        <h2>运行配置</h2>
        <p>当前生效的非敏感应用参数。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="showDetails = !showDetails">{{ showDetails ? '收起参数' : '展开全部参数' }}</el-button>
        <el-button :loading="loading" @click="loadConfig">刷新配置</el-button>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />

    <template v-if="config">
      <section class="model-strip">
        <div class="model-summary"><span>当前 Chat</span><strong>{{ config.routing.default_model || '未配置' }}</strong><small>已由模型管理激活</small></div>
        <div class="model-summary"><span>当前 Embedding</span><strong>{{ config.embedding.model }}</strong><small>{{ config.embedding.provider }} · {{ config.embedding.dim }} 维</small></div>
        <div class="model-actions"><el-button type="primary" @click="router.push('/models')">模型管理</el-button><el-button @click="router.push('/monitor?tab=maintenance')">系统维护</el-button></div>
      </section>

      <section class="config-grid">
        <el-card shadow="never" class="config-card">
          <template #header><div class="card-title"><div><span class="eyebrow">APPLICATION</span><h3>应用与连接</h3></div><span class="read-only">只读</span></div></template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="运行环境">{{ config.app.app_env }}</el-descriptions-item>
            <el-descriptions-item label="日志级别">{{ config.app.log_level }}</el-descriptions-item>
            <el-descriptions-item label="在线 API">{{ yesNo(config.app.allow_online_api) }}</el-descriptions-item>
            <el-descriptions-item label="数据库">{{ config.database.enabled ? '已启用' : '未启用' }}</el-descriptions-item>
            <el-descriptions-item v-if="showDetails" label="数据库连接串"><el-tag :type="config.database.database_url.configured ? 'success' : 'info'">{{ secretLabel(config.database.database_url) }}</el-tag></el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" class="config-card">
          <template #header><div class="card-title"><div><span class="eyebrow">RAG BEHAVIOR</span><h3>RAG 行为</h3></div><span class="read-only">只读</span></div></template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="Chunk size">{{ config.rag.chunk_size }}</el-descriptions-item>
            <el-descriptions-item label="Chunk overlap">{{ config.rag.chunk_overlap }}</el-descriptions-item>
            <el-descriptions-item label="检索 Top-K">{{ config.rag.retrieval_top_k }}</el-descriptions-item>
            <el-descriptions-item label="Mock RAG / Chat">{{ yesNo(config.mock.rag_enabled) }} / {{ yesNo(config.mock.chat_enabled) }}</el-descriptions-item>
            <el-descriptions-item v-if="showDetails" label="FAISS 索引路径"><span class="mono">{{ config.rag.faiss_index_path }}</span></el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" class="config-card">
          <template #header><div class="card-title"><div><span class="eyebrow">EFFECTIVE VALUES</span><h3>当前生效摘要</h3></div><span class="read-only">来自运行环境</span></div></template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="Embedding">{{ config.embedding.provider }} / {{ config.embedding.backend }}</el-descriptions-item>
            <el-descriptions-item label="Endpoint"><span class="mono">{{ config.embedding.api_base || '—' }}</span></el-descriptions-item>
            <el-descriptions-item label="默认路由">{{ config.routing.default_model || '—' }}</el-descriptions-item>
            <el-descriptions-item label="模型密钥">由模型管理的密钥引用控制</el-descriptions-item>
            <el-descriptions-item v-if="showDetails" label="Embedding Key"><el-tag :type="config.embedding.api_key.configured ? 'success' : 'info'">{{ secretLabel(config.embedding.api_key) }}</el-tag></el-descriptions-item>
          </el-descriptions>
        </el-card>
      </section>

      <section class="boundary-section">
        <div class="boundary-head"><div><span class="eyebrow">CONFIGURATION BOUNDARY</span><h3>配置边界</h3></div><span class="read-only">避免重复操作</span></div>
        <div class="boundary-grid">
          <div><strong>模型管理</strong><span>登记、编辑、启停、健康检查，以及 Chat / Embedding 切换。</span></div>
          <div><strong>监控大屏 · 系统维护</strong><span>服务连通性、索引一致性和重建索引。</span></div>
          <div><strong>运行配置</strong><span>RAG 参数、应用行为和当前生效的配置摘要。</span></div>
        </div>
      </section>

      <el-alert title="切换 Embedding 模型后，请前往“监控大屏 > 系统维护”确认索引一致性，并在需要时重建索引。" type="warning" show-icon :closable="false" />

      <section v-if="config.notes.length" class="notes-section"><h3>运行说明</h3><ul><li v-for="note in config.notes" :key="note">{{ note }}</li></ul></section>
    </template>
  </main>
</template>

<style scoped>
.settings-page { flex: 1; overflow-y: auto; padding: 24px 28px 36px; background: #f7f8fa; color: #18202b; }.page-toolbar, .toolbar-actions, .card-title, .model-actions, .boundary-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.page-toolbar { margin-bottom: 20px; }.page-toolbar p { margin: 7px 0 0; color: #667085; font-size: 13px; }.toolbar-actions, .model-actions { flex-wrap: wrap; justify-content: flex-end; }.eyebrow { margin: 0 0 5px; color: #7c8797; font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; } h2, h3 { margin: 0; color: #1d2939; } h2 { font-size: 22px; } h3 { font-size: 16px; }
.model-strip { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; gap: 16px; align-items: center; padding: 16px 0; border-top: 1px solid #e6e9ef; border-bottom: 1px solid #e6e9ef; }.model-summary { display: flex; min-width: 0; flex-direction: column; gap: 4px; }.model-summary span, .model-summary small, .read-only { color: #7c8797; font-size: 12px; }.model-summary strong { color: #344054; overflow-wrap: anywhere; font-size: 14px; }
.config-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 18px; }.config-card { min-width: 0; }.card-title { align-items: flex-start; }.config-card :deep(.el-card__header) { padding: 15px 16px; }.config-card :deep(.el-card__body) { padding: 12px 16px; }.config-card :deep(.el-descriptions__label) { color: #667085; width: 104px; }.config-card :deep(.el-descriptions__content) { color: #344054; overflow-wrap: anywhere; }.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow-wrap: anywhere; }
.boundary-section, .notes-section { margin-top: 18px; border: 1px solid #e6e9ef; border-radius: 12px; background: #fff; padding: 18px; }.boundary-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 14px; }.boundary-grid div { display: flex; flex-direction: column; gap: 6px; padding-right: 16px; border-right: 1px solid #eef1f5; }.boundary-grid div:last-child { border-right: 0; padding-right: 0; }.boundary-grid strong { color: #344054; font-size: 14px; }.boundary-grid span { color: #667085; font-size: 13px; line-height: 1.5; }.settings-page :deep(.el-alert) { margin-top: 18px; }.notes-section ul { margin: 12px 0 0; padding-left: 20px; color: #667085; font-size: 13px; }.notes-section li + li { margin-top: 6px; }
@media (max-width: 980px) { .config-grid, .boundary-grid { grid-template-columns: 1fr; }.boundary-grid div { border-right: 0; border-bottom: 1px solid #eef1f5; padding: 0 0 12px; }.boundary-grid div:last-child { border-bottom: 0; padding-bottom: 0; } } @media (max-width: 700px) { .page-toolbar, .model-strip, .boundary-head { align-items: flex-start; grid-template-columns: 1fr; flex-direction: column; }.model-actions { justify-content: flex-start; } }
</style>
