<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  activateModel,
  createModel,
  deleteModel,
  deployModel,
  getModels,
  getOllamaCatalog,
  getXinferenceCached,
  getXinferenceRunning,
  queryXinferenceCatalog,
  terminateModel,
  updateModel,
  type LocalDeployment,
  type ModelConfig,
  type ModelConfigInput,
  type ModelSource,
  type ModelType,
} from '@/api/client'

type FormState = Omit<ModelConfigInput, 'dimension' | 'runtime_config'> & {
  source: ModelSource
  deployment: LocalDeployment | null
  credential_ref: string
  dimension: string
  runtime_config_json: string
}

type RuntimeCatalogItem = {
  model_name: string
  model_type: string
  downloaded: boolean
  running: boolean
  parameters: Record<string, unknown>
}

function emptyForm(): FormState {
  return {
    model_key: '',
    display_name: '',
    model_type: 'chat',
    provider: 'geekai',
    model_name: '',
    source: 'gateway',
    deployment: null,
    endpoint: '',
    credential_ref: '',
    dimension: '',
    enabled: true,
    notes: '',
    runtime_config_json: '{}',
  }
}

const models = ref<ModelConfig[]>([])
const activeTab = ref<'catalog' | 'runtime'>('catalog')
const selectedModelId = ref<string | null>(null)
const loading = ref(true)
const saving = ref(false)
const activatingId = ref<string | null>(null)
const deployingId = ref<string | null>(null)
const error = ref('')
const successMessage = ref('')
const editingId = ref<string | null>(null)
const formOpen = ref(false)
const form = reactive<FormState>(emptyForm())

const filterQuery = ref('')
const filterType = ref<'all' | ModelType>('all')
const filterSource = ref<'all' | ModelSource>('all')
const filterDeployment = ref<'all' | LocalDeployment>('all')
const onlyActive = ref(false)

const runtimeEndpoint = ref('')
const runtimeType = ref<'LLM' | 'embedding'>('LLM')
const runtimeStatus = ref<'all' | 'running' | 'cached' | 'not-running'>('all')
const runtimeLoading = ref(false)
const runningModels = ref<Array<Record<string, unknown>>>([])
const cachedModels = ref<Array<Record<string, unknown>>>([])
const catalogItems = ref<RuntimeCatalogItem[]>([])
const catalogTotal = ref(0)
const catalogPage = ref(1)
const catalogPageSize = 10
const catalogNameQuery = ref('')
const catalogParamQuery = ref('')
const catalogDownloaded = ref<'all' | 'yes' | 'no'>('all')

const formCatalogLoading = ref(false)
const formCatalogItems = ref<Array<{
  model_name: string
  model_type: string
  parameters: Record<string, unknown>
}>>([])
const formCatalogSelection = ref('')

function sourceFor(item: Pick<ModelConfig, 'source' | 'provider'>): ModelSource {
  if (item.source) return item.source
  if (item.provider === 'openai') return 'official'
  if (['xinference', 'ollama', 'tei'].includes(item.provider)) return 'local'
  return 'gateway'
}

function sourceLabel(source: ModelSource) {
  return { official: '官方 API', gateway: '中转站', local: '本地' }[source]
}

function typeLabel(type: ModelType | string) {
  return { chat: 'Chat', embedding: 'Embedding', vision: 'Vision', LLM: 'Chat' }[type] || type
}

function deploymentLabel(deployment?: string | null) {
  return deployment === 'xinference' ? 'Xinference' : deployment === 'ollama' ? 'Ollama' : '—'
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function shortId(value: string) {
  return `${value.slice(0, 4)}…${value.slice(-4)}（自动生成，只读）`
}

function modelKeyFrom(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80)
}

function findDimension(value: unknown): string {
  if (!value || typeof value !== 'object') return ''
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (['dimension', 'dimensions', 'embedding_dim'].includes(key.toLowerCase()) && Number.isInteger(Number(item))) return String(item)
    const nested = findDimension(item)
    if (nested) return nested
  }
  return ''
}

function endpointPlaceholder() {
  if (form.source === 'local' && form.deployment === 'ollama') return 'http://localhost:11434/v1'
  if (form.source === 'local') return 'http://winpc:9997/v1'
  if (form.source === 'official') return 'https://api.openai.com/v1'
  return 'https://api.example.com/v1'
}

function credentialHint() {
  if (form.source === 'official') return '只填写环境变量名称，例如 OPENAI_API_KEY；密钥本身不会保存。'
  if (form.source === 'gateway') return '只填写环境变量名称，例如 GEEKAI_API_KEY；密钥本身不会保存。'
  return '本地服务的认证信息只保留在服务端环境变量中。'
}

function runningFor(item: ModelConfig) {
  return runningModels.value.find((runtime) => runtime.model_name === item.model_name || runtime.id === item.model_name || runtime.model_uid === item.model_name)
}

function modelHealth(item: ModelConfig) {
  return sourceFor(item) === 'local' ? '未检查' : '不适用'
}

function runtimeParameters(item: ModelConfig) {
  const parts = []
  if (item.dimension) parts.push(`维度 ${item.dimension}`)
  const config = item.runtime_config || {}
  if (config.quantization) parts.push(String(config.quantization))
  if (Array.isArray(config.gpu_idx)) parts.push(`GPU ${config.gpu_idx.join(', ')}`)
  if (config.download_hub) parts.push(String(config.download_hub))
  return parts.join(' · ') || '—'
}

const filteredModels = computed(() => models.value.filter((item) => {
  const keyword = filterQuery.value.trim().toLowerCase()
  const source = sourceFor(item)
  if (keyword && !`${item.display_name} ${item.model_key} ${item.model_name}`.toLowerCase().includes(keyword)) return false
  if (filterType.value !== 'all' && item.model_type !== filterType.value) return false
  if (filterSource.value !== 'all' && source !== filterSource.value) return false
  if (filterDeployment.value !== 'all' && item.deployment !== filterDeployment.value) return false
  return !onlyActive.value || item.is_active
}))

const selectedModel = computed(() => {
  const selected = models.value.find((item) => item.id === selectedModelId.value)
  return selected || filteredModels.value[0] || null
})

const runtimeRows = computed(() => catalogItems.value.filter((item) => {
  if (runtimeStatus.value === 'running') return item.running
  if (runtimeStatus.value === 'cached') return item.downloaded && !item.running
  if (runtimeStatus.value === 'not-running') return !item.running
  return true
}))

watch(() => form.source, (source) => {
  if (source === 'local') form.deployment ||= 'xinference'
  else {
    form.deployment = null
    form.runtime_config_json = '{}'
  }
})

watch(() => form.deployment, () => {
  formCatalogItems.value = []
  formCatalogSelection.value = ''
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    models.value = await getModels()
    if (!selectedModelId.value || !models.value.some((item) => item.id === selectedModelId.value)) {
      selectedModelId.value = models.value[0]?.id || null
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法加载模型目录'
  } finally {
    loading.value = false
  }
}

async function refreshRuntime() {
  runtimeLoading.value = true
  error.value = ''
  try {
    const [running, cached] = await Promise.all([
      getXinferenceRunning(runtimeEndpoint.value || undefined),
      getXinferenceCached(runtimeEndpoint.value || undefined),
    ])
    runningModels.value = running.models
    cachedModels.value = cached.models
    await queryCatalog(false)
  } catch (e) {
    error.value = 'Xinference 运行时不可连接，请检查服务地址和启动状态。'
  } finally {
    runtimeLoading.value = false
  }
}

async function queryCatalog(resetPage = false) {
  if (resetPage) catalogPage.value = 1
  runtimeLoading.value = true
  try {
    const result = await queryXinferenceCatalog({
      modelType: runtimeType.value,
      query: catalogNameQuery.value,
      paramQuery: catalogParamQuery.value,
      downloaded: catalogDownloaded.value,
      page: catalogPage.value,
      pageSize: catalogPageSize,
      endpoint: runtimeEndpoint.value || undefined,
    })
    catalogItems.value = result.items
    catalogTotal.value = result.total
  } catch (e) {
    error.value = '无法查询 Xinference 模型，请检查服务地址、模型类型和运行状态。'
  } finally {
    runtimeLoading.value = false
  }
}

function resetForm() {
  Object.assign(form, emptyForm())
  editingId.value = null
  formCatalogItems.value = []
  formCatalogSelection.value = ''
}

function openCreate() {
  activeTab.value = 'catalog'
  resetForm()
  formOpen.value = true
}

function closeForm() {
  resetForm()
  formOpen.value = false
}

function edit(item: ModelConfig) {
  activeTab.value = 'catalog'
  selectedModelId.value = item.id
  editingId.value = item.id
  Object.assign(form, {
    model_key: item.model_key,
    display_name: item.display_name,
    model_type: item.model_type,
    provider: item.provider,
    model_name: item.model_name,
    source: sourceFor(item),
    deployment: item.deployment || (item.provider === 'xinference' || item.provider === 'ollama' ? item.provider : null),
    endpoint: item.endpoint || '',
    credential_ref: item.credential_ref || '',
    dimension: item.dimension?.toString() || '',
    enabled: item.enabled,
    notes: item.notes,
    runtime_config_json: JSON.stringify(item.runtime_config || {}, null, 2),
  })
  formOpen.value = true
  error.value = ''
}

function applyFormCatalogModel(item: { model_name: string; model_type: string; parameters: Record<string, unknown> }) {
  const type = item.model_type.toLowerCase()
  if (type === 'llm' || type === 'chat') form.model_type = 'chat'
  else if (type === 'embedding') form.model_type = 'embedding'
  form.model_name = item.model_name
  form.display_name = item.model_name
  form.model_key = modelKeyFrom(item.model_name)
  form.dimension = findDimension(item.parameters)
  form.runtime_config_json = form.deployment === 'xinference' ? JSON.stringify(item.parameters || {}, null, 2) : '{}'
}

function selectFormCatalogModel(name: string) {
  const item = formCatalogItems.value.find((model) => model.model_name === name)
  if (item) applyFormCatalogModel(item)
}

async function fetchFormCatalog() {
  if (!form.endpoint?.trim()) {
    error.value = '请先填写本地服务端点，再读取模型列表'
    return
  }
  formCatalogLoading.value = true
  formCatalogSelection.value = ''
  error.value = ''
  try {
    if (form.deployment === 'xinference') {
      const result = await queryXinferenceCatalog({
        modelType: form.model_type === 'embedding' ? 'embedding' : 'LLM',
        page: 1,
        pageSize: 100,
        endpoint: form.endpoint.trim(),
      })
      formCatalogItems.value = result.items.map((item) => ({
        model_name: item.model_name,
        model_type: item.model_type,
        parameters: item.parameters,
      }))
    } else if (form.deployment === 'ollama') {
      const result = await getOllamaCatalog(form.endpoint.trim())
      formCatalogItems.value = result.models
    }
  } catch (e) {
    error.value = `${deploymentLabel(form.deployment)} 模型列表读取失败，请检查服务地址和运行状态。`
  } finally {
    formCatalogLoading.value = false
  }
}

async function save() {
  const dimension = form.dimension.trim() ? Number(form.dimension) : null
  if (!Number.isInteger(dimension) && dimension !== null) {
    error.value = '向量维度必须是正整数'
    return
  }
  const payload: ModelConfigInput = {
    model_key: form.model_key.trim(),
    display_name: form.display_name.trim(),
    model_type: form.model_type,
    provider: form.deployment || (form.source === 'official' ? 'openai' : form.source === 'gateway' ? 'geekai' : 'xinference'),
    model_name: form.model_name.trim(),
    source: form.source,
    deployment: form.source === 'local' ? form.deployment : null,
    endpoint: form.endpoint?.trim() || null,
    credential_ref: form.credential_ref.trim() || null,
    dimension,
    enabled: form.enabled,
    notes: form.notes.trim(),
  }
  try {
    payload.runtime_config = form.runtime_config_json.trim() ? JSON.parse(form.runtime_config_json) : {}
    if (!payload.runtime_config || Array.isArray(payload.runtime_config) || typeof payload.runtime_config !== 'object') throw new Error('运行参数必须是 JSON 对象')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '运行参数 JSON 格式错误'
    return
  }
  if (!payload.model_key || !payload.display_name || !payload.model_name) {
    error.value = '请填写名称、Code 和模型标识'
    return
  }
  if (form.source === 'local' && (!form.deployment || !payload.endpoint)) {
    error.value = '本地模型必须选择部署方式并填写 Endpoint'
    return
  }
  if (dimension !== null && dimension <= 0) {
    error.value = '向量维度必须大于 0'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const saved = editingId.value ? await updateModel(editingId.value, payload) : await createModel(payload)
    selectedModelId.value = saved.id
    successMessage.value = `模型「${saved.display_name}」已保存`
    closeForm()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function activate(item: ModelConfig) {
  const caution = item.model_type === 'embedding' ? '切换后必须重建本机 FAISS 索引。仍要继续吗？' : '后续新对话将使用该模型。仍要继续吗？'
  if (!confirm(`设「${item.display_name}」为当前${typeLabel(item.model_type)}模型？${caution}`)) return
  activatingId.value = item.id
  error.value = ''
  successMessage.value = ''
  try {
    const result = await activateModel(item.id)
    successMessage.value = result.message
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '模型切换失败'
  } finally {
    activatingId.value = null
  }
}

async function deploy(item: ModelConfig) {
  deployingId.value = item.id
  error.value = ''
  try {
    await deployModel(item.id, {
      endpoint: runtimeEndpoint.value || item.endpoint,
      model_engine: item.model_type === 'embedding' ? 'sentence_transformers' : undefined,
      model_format: item.model_type === 'embedding' ? 'pytorch' : undefined,
      download_hub: 'modelscope',
      gpu_idx: [0],
      n_gpu: 'auto',
      enable_virtual_env: false,
      ...(item.runtime_config || {}),
    })
    successMessage.value = `${item.display_name} 已提交给 Xinference 部署/下载`
    await refreshRuntime()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '模型部署失败'
  } finally {
    deployingId.value = null
  }
}

async function stopRuntime(item: ModelConfig) {
  const runtime = runningFor(item)
  const uid = runtime && String(runtime.id || runtime.model_uid || item.model_name)
  if (!uid || !confirm(`停止 Xinference 模型「${item.display_name}」？`)) return
  try {
    await terminateModel(item.id, uid)
    successMessage.value = `${item.display_name} 已停止`
    await refreshRuntime()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '停止模型失败'
  }
}

async function remove(item: ModelConfig) {
  try {
    await ElMessageBox.confirm(
      `删除模型「${item.display_name}」只会移除 LLMOps 中的登记记录，不会停止 Xinference 进程或删除本地缓存。`,
      '确认删除模型？',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  error.value = ''
  try {
    await deleteModel(item.id)
    if (selectedModelId.value === item.id) selectedModelId.value = null
    closeForm()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

function matchingCatalogModel(item: RuntimeCatalogItem) {
  return models.value.find((model) => model.provider === 'xinference' && model.model_name === item.model_name)
}

async function selectTab(tab: 'catalog' | 'runtime') {
  activeTab.value = tab
  if (tab === 'runtime' && !catalogItems.value.length && !runtimeLoading.value) await refreshRuntime()
}

onMounted(async () => {
  await load()
})
</script>

<template>
  <main class="models-page">
    <div class="page-tabs" role="tablist" aria-label="模型管理视图">
      <button class="tab-button" :class="{ active: activeTab === 'catalog' }" type="button" role="tab" :aria-selected="activeTab === 'catalog'" @click="selectTab('catalog')">模型登记</button>
      <button class="tab-button" :class="{ active: activeTab === 'runtime' }" type="button" role="tab" :aria-selected="activeTab === 'runtime'" @click="selectTab('runtime')">Xinference 运行时</button>
      <button class="primary-button" type="button" @click="openCreate">新增模型</button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="notice" />
    <el-alert v-if="successMessage" :title="successMessage" type="success" show-icon :closable="false" class="notice" />

    <section v-show="activeTab === 'catalog'" class="catalog-panel">
      <div class="toolbar" aria-label="模型登记筛选">
        <label>搜索 <el-input v-model="filterQuery" clearable placeholder="名称或 Code" /></label>
        <label>类型 <el-select v-model="filterType"><el-option label="全部" value="all" /><el-option label="Chat" value="chat" /><el-option label="Embedding" value="embedding" /><el-option label="Vision" value="vision" /></el-select></label>
        <label>来源 <el-select v-model="filterSource"><el-option label="全部" value="all" /><el-option label="官方 API" value="official" /><el-option label="中转站" value="gateway" /><el-option label="本地" value="local" /></el-select></label>
        <label>部署 <el-select v-model="filterDeployment"><el-option label="全部" value="all" /><el-option label="Xinference" value="xinference" /><el-option label="Ollama" value="ollama" /></el-select></label>
        <label class="checkbox-label"><el-checkbox v-model="onlyActive" /> 仅当前使用</label>
      </div>

      <div class="catalog-layout">
        <section class="table-panel" aria-label="模型登记列表">
          <div class="table-scroll">
            <table class="model-table">
              <thead><tr><th>名称 / Code</th><th>类型</th><th>来源</th><th>部署方式</th><th>登记与启用</th><th>运行 / 健康</th><th>当前</th></tr></thead>
              <tbody v-loading="loading">
                <tr v-for="item in filteredModels" :key="item.id" :class="{ selected: selectedModel?.id === item.id }" @click="selectedModelId = item.id">
                  <td><strong>{{ item.display_name }}</strong><small>{{ item.model_key }}</small></td>
                  <td>{{ typeLabel(item.model_type) }}</td>
                  <td>{{ sourceLabel(sourceFor(item)) }}</td>
                  <td>{{ sourceFor(item) === 'local' ? deploymentLabel(item.deployment || item.provider) : '—' }}</td>
                  <td><span class="status-tag ok">已登记</span> <span class="status-tag" :class="item.enabled ? 'ok' : ''">{{ item.enabled ? '已启用' : '已停用' }}</span></td>
                  <td><span class="status-tag" :class="{ ok: Boolean(runningFor(item)) }">{{ sourceFor(item) === 'local' ? (runningFor(item) ? '运行中' : '未运行') : '不适用' }}</span> <span class="status-tag">{{ modelHealth(item) }}</span></td>
                  <td><span v-if="item.is_active" class="status-tag current">{{ typeLabel(item.model_type) }} 当前</span><span v-else>—</span></td>
                </tr>
                <tr v-if="!loading && !filteredModels.length"><td colspan="7" class="empty-row">暂无匹配的模型登记。</td></tr>
              </tbody>
            </table>
          </div>
          <p class="table-note">{{ filteredModels.length }} 条记录 · 第 1 / 1 页</p>
        </section>

        <aside class="detail-card" aria-live="polite">
          <template v-if="selectedModel">
            <strong>{{ selectedModel.display_name }}</strong>
            <dl>
              <dt>UUID</dt><dd class="mono">{{ shortId(selectedModel.id) }}</dd>
              <dt>类型</dt><dd>{{ typeLabel(selectedModel.model_type) }}</dd>
              <dt>来源</dt><dd>{{ sourceLabel(sourceFor(selectedModel)) }}</dd>
              <dt>部署方式</dt><dd>{{ sourceFor(selectedModel) === 'local' ? deploymentLabel(selectedModel.deployment || selectedModel.provider) : '—' }}</dd>
              <dt>模型标识</dt><dd class="mono">{{ selectedModel.model_name }}</dd>
              <dt>Endpoint</dt><dd class="mono">{{ selectedModel.endpoint || '—' }}</dd>
              <dt>密钥引用</dt><dd>{{ selectedModel.credential_ref || '—' }}</dd>
              <dt>运行参数</dt><dd>{{ runtimeParameters(selectedModel) }}</dd>
            </dl>
            <div class="detail-actions">
              <button type="button" @click="edit(selectedModel)">编辑</button>
              <button type="button" disabled title="健康检查接口尚未接入">健康检查</button>
              <button type="button" :disabled="!selectedModel.enabled || selectedModel.is_active || activatingId === selectedModel.id" @click="activate(selectedModel)">{{ selectedModel.is_active ? '当前使用' : activatingId === selectedModel.id ? '切换中…' : '设为当前' }}</button>
              <button v-if="sourceFor(selectedModel) === 'local' && selectedModel.deployment === 'xinference' && !runningFor(selectedModel)" type="button" @click="deploy(selectedModel)">{{ deployingId === selectedModel.id ? '部署中…' : '部署' }}</button>
              <button v-if="sourceFor(selectedModel) === 'local' && selectedModel.deployment === 'xinference' && runningFor(selectedModel)" type="button" @click="stopRuntime(selectedModel)">停止</button>
              <button class="danger" type="button" @click="remove(selectedModel)">删除</button>
            </div>
            <p class="updated-at">更新于 {{ formatTime(selectedModel.updated_at) }}</p>
          </template>
          <p v-else class="empty-detail">选择一条模型登记查看详情。</p>
        </aside>
      </div>
    </section>

    <section v-show="activeTab === 'runtime'" class="runtime-panel">
      <div class="toolbar runtime-toolbar">
        <label>Xinference API <el-input v-model="runtimeEndpoint" placeholder="http://winpc:9997/v1" /></label>
        <label>状态 <el-select v-model="runtimeStatus"><el-option label="全部" value="all" /><el-option label="运行中" value="running" /><el-option label="已缓存" value="cached" /><el-option label="未运行" value="not-running" /></el-select></label>
        <label>类型 <el-select v-model="runtimeType" @change="queryCatalog(true)"><el-option label="Chat" value="LLM" /><el-option label="Embedding" value="embedding" /></el-select></label>
        <button type="button" @click="refreshRuntime">{{ runtimeLoading ? '刷新中…' : '刷新运行时' }}</button>
      </div>
      <div class="toolbar runtime-search">
        <label>名称 <el-input v-model="catalogNameQuery" placeholder="按模型名称查询" @keyup.enter="queryCatalog(true)" /></label>
        <label>参数 <el-input v-model="catalogParamQuery" placeholder="如 transformers / Q4 / 768" @keyup.enter="queryCatalog(true)" /></label>
        <label>缓存 <el-select v-model="catalogDownloaded"><el-option label="全部" value="all" /><el-option label="已下载" value="yes" /><el-option label="未下载" value="no" /></el-select></label>
        <button type="button" @click="queryCatalog(true)">查询</button>
      </div>
      <div class="table-scroll runtime-table-wrap">
        <table class="model-table">
          <thead><tr><th>模型</th><th>类型</th><th>实例 UID</th><th>缓存</th><th>运行状态</th><th>操作</th></tr></thead>
          <tbody v-loading="runtimeLoading">
            <tr v-for="item in runtimeRows" :key="item.model_name">
              <td>{{ item.model_name }}</td><td>{{ typeLabel(item.model_type) }}</td><td class="mono">{{ item.model_name }}</td><td>{{ item.downloaded ? '已缓存' : '未缓存' }}</td>
              <td><span class="status-tag" :class="{ ok: item.running }">{{ item.running ? '运行中' : '未运行' }}</span></td>
              <td><button v-if="matchingCatalogModel(item) && item.running" type="button" @click="stopRuntime(matchingCatalogModel(item)!)">停止</button><span v-else>—</span></td>
            </tr>
            <tr v-if="!runtimeLoading && !runtimeRows.length"><td colspan="6" class="empty-row">暂无匹配的 Xinference 模型。</td></tr>
          </tbody>
        </table>
      </div>
      <div class="runtime-footer"><span>共 {{ catalogTotal }} 个模型</span><el-pagination v-model:current-page="catalogPage" :page-size="catalogPageSize" :total="catalogTotal" layout="prev, pager, next" @current-change="queryCatalog" /></div>
    </section>

    <el-dialog v-model="formOpen" class="model-dialog" :title="editingId ? '编辑模型' : '新增模型'" width="760px" :close-on-click-modal="false" @closed="closeForm">
      <form class="editor-grid" @submit.prevent="save">
        <label>名称 <el-input v-model="form.display_name" required placeholder="例如：Qwen 2.5 7B Instruct" /></label>
        <label>Code <el-input v-model="form.model_key" required placeholder="唯一且稳定，例如 qwen2.5-7b" /></label>
        <label>类型 <el-select v-model="form.model_type"><el-option label="Chat" value="chat" /><el-option label="Embedding" value="embedding" /><el-option label="Vision" value="vision" /></el-select></label>
        <label>来源 <el-select v-model="form.source"><el-option label="本地" value="local" /><el-option label="官方 API" value="official" /><el-option label="中转站" value="gateway" /></el-select></label>
        <label v-if="form.source === 'local'">部署方式 <el-select v-model="form.deployment"><el-option label="Xinference" value="xinference" /><el-option label="Ollama" value="ollama" /></el-select></label>
        <label>Endpoint <el-input v-model="form.endpoint" :placeholder="endpointPlaceholder()" /></label>
        <label v-if="form.source === 'local'" class="wide-field">本地模型
          <span class="local-import"><button type="button" :disabled="formCatalogLoading" @click="fetchFormCatalog">{{ formCatalogLoading ? '获取中…' : '获取可用模型' }}</button><el-select v-model="formCatalogSelection" placeholder="先获取模型列表" :disabled="!formCatalogItems.length" @change="selectFormCatalogModel"><el-option v-for="item in formCatalogItems" :key="item.model_name" :label="`${item.model_name} · ${typeLabel(item.model_type)}`" :value="item.model_name" /></el-select></span>
          <small>选择模型后自动回填名称、Code、类型、模型标识、维度与运行参数。</small>
        </label>
        <label>模型标识 <el-input v-model="form.model_name" required :readonly="form.source === 'local'" placeholder="模型 UID / API model 名称" /></label>
        <label v-if="form.source !== 'local'">密钥引用 <el-input v-model="form.credential_ref" placeholder="环境变量名，例如 GEEKAI_API_KEY" /><small>{{ credentialHint() }}</small></label>
        <label v-if="form.model_type === 'embedding'">Embedding 维度 <el-input v-model="form.dimension" placeholder="768" /></label>
        <label v-if="form.source === 'local' && form.deployment === 'xinference'" class="wide-field">本地启动与 Chat 调用参数 <el-input v-model="form.runtime_config_json" type="textarea" :rows="4" placeholder='{"quantization":"Q4","gpu_idx":[0],"temperature":0.2,"max_tokens":2048}' /><small>启动参数用于 Xinference 部署；Chat 调用支持 temperature、top_p、max_tokens、presence_penalty、frequency_penalty。</small></label>
        <label v-else-if="form.model_type === 'chat'" class="wide-field">Chat 调用参数 <el-input v-model="form.runtime_config_json" type="textarea" :rows="4" placeholder='{"temperature":0.2,"max_tokens":2048}' /><small>仅保存允许的生成参数：temperature、top_p、max_tokens、presence_penalty、frequency_penalty。</small></label>
        <label class="wide-field">备注 <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="用途、显存需求或部署说明" /></label>
        <label class="enabled-toggle"><el-switch v-model="form.enabled" /> 在模型目录中启用</label>
        <div class="editor-actions"><button type="button" @click="closeForm">取消</button><button class="primary-button" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存模型' }}</button></div>
      </form>
    </el-dialog>
  </main>
</template>

<style scoped>
.models-page { flex: 1; overflow-y: auto; padding: 1.5rem 2rem 2rem; color: var(--main-text); }
.page-tabs { display: flex; align-items: center; gap: .5rem; margin-bottom: 1rem; }
button { border: 1px solid var(--border); border-radius: .45rem; padding: .48rem .75rem; color: var(--main-text); background: var(--main-bg); font: inherit; font-size: .8125rem; cursor: pointer; }
button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
button:disabled { cursor: not-allowed; opacity: .5; }
.tab-button { border-color: transparent; }
.tab-button.active { border-color: var(--accent); background: rgba(16, 163, 127, .1); color: var(--accent); font-weight: 600; }
.primary-button { margin-left: auto; border-color: var(--accent); background: var(--accent); color: #fff; }
.primary-button:hover:not(:disabled) { background: var(--accent-hover); color: #fff; }
.notice { margin: 0 0 1rem; }
.toolbar { display: flex; flex-wrap: wrap; align-items: end; gap: .6rem; margin-bottom: 1rem; }
.toolbar label { display: flex; align-items: center; gap: .35rem; color: #6e6e80; font-size: .8125rem; white-space: nowrap; }
.toolbar :deep(.el-input), .toolbar :deep(.el-select) { width: 9rem; }
.toolbar label:first-child :deep(.el-input) { width: 14rem; }
.checkbox-label { height: 2rem; color: var(--main-text) !important; }
.catalog-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(16rem, 25%); gap: 1rem; align-items: start; }
.table-panel, .detail-card, .runtime-panel { border: 1px solid var(--border); border-radius: .7rem; background: var(--main-bg); }
.table-scroll { overflow-x: auto; }
.model-table { width: 100%; min-width: 860px; border-collapse: collapse; font-size: .8125rem; }
.model-table th, .model-table td { padding: .7rem .55rem; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
.model-table th { color: #6e6e80; font-weight: 500; white-space: nowrap; }
.model-table tbody tr:not(.empty-row) { cursor: pointer; }
.model-table tbody tr:not(.empty-row):hover { background: rgba(16, 163, 127, .05); }
.model-table tbody tr.selected { background: rgba(16, 163, 127, .11); }
.model-table strong { display: block; font-size: .875rem; }
.model-table small { display: block; margin-top: .2rem; color: #8e8e8e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.status-tag { display: inline-block; margin: .12rem .1rem .12rem 0; padding: .13rem .4rem; border: 1px solid var(--border); border-radius: .35rem; color: #6e6e80; font-size: .75rem; white-space: nowrap; }
.status-tag.ok { border-color: rgba(16, 163, 127, .35); background: rgba(16, 163, 127, .1); color: #08775a; }
.status-tag.current { border-color: var(--accent); background: var(--accent); color: #fff; }
.table-note, .updated-at { margin: .65rem .75rem; color: #8e8e8e; font-size: .75rem; }
.empty-row { padding: 2rem !important; color: #8e8e8e; text-align: center !important; }
.detail-card { padding: 1rem; }
.detail-card > strong { font-size: .9375rem; }
.detail-card dl { display: grid; grid-template-columns: 5.4rem minmax(0, 1fr); gap: .6rem; margin: 1rem 0; font-size: .8125rem; }
.detail-card dt { color: #8e8e8e; }
.detail-card dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .75rem; }
.detail-actions { display: flex; flex-wrap: wrap; gap: .45rem; }
.detail-actions .danger { color: var(--error); }
.empty-detail { margin: 0; color: #8e8e8e; font-size: .8125rem; }
.runtime-panel { padding: 1rem; }
.runtime-toolbar label:first-child :deep(.el-input) { width: 19rem; }
.runtime-search { margin-bottom: .75rem; }
.runtime-search label:first-child :deep(.el-input), .runtime-search label:nth-child(2) :deep(.el-input) { width: 14rem; }
.runtime-table-wrap { border: 1px solid var(--border); border-radius: .45rem; }
.runtime-footer { display: flex; align-items: center; justify-content: flex-end; gap: .7rem; margin-top: .65rem; color: #8e8e8e; font-size: .75rem; }
.editor-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .85rem; }
.model-dialog :deep(.el-dialog__body) { padding-top: .75rem; }
.editor-grid > label { display: flex; flex-direction: column; gap: .35rem; color: #4f4f5c; font-size: .8125rem; font-weight: 500; }
.editor-grid small { color: #8e8e8e; font-weight: 400; line-height: 1.4; }
.wide-field { grid-column: 1 / -1; }
.local-import { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: .5rem; align-items: center; }
.enabled-toggle { flex-direction: row !important; align-items: center; grid-column: 1 / -1; }
.editor-actions { display: flex; justify-content: flex-end; gap: .5rem; grid-column: 1 / -1; }
.editor-actions .primary-button { margin-left: 0; }
@media (max-width: 980px) { .catalog-layout { grid-template-columns: 1fr; } .detail-card { max-width: none; } }
@media (max-width: 680px) { .models-page { padding: 1rem; } .page-tabs { flex-wrap: wrap; } .primary-button { margin-left: 0; } .toolbar label, .toolbar :deep(.el-input), .toolbar :deep(.el-select), .toolbar label:first-child :deep(.el-input), .runtime-toolbar label:first-child :deep(.el-input), .runtime-search label:first-child :deep(.el-input), .runtime-search label:nth-child(2) :deep(.el-input) { width: 100%; } .toolbar label { align-items: stretch; flex-direction: column; width: 100%; } .editor-grid { grid-template-columns: 1fr; } .local-import { grid-template-columns: 1fr; } }
</style>
