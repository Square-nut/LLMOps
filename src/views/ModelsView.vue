<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import {
  activateModel,
  createModel,
  deployModel,
  deleteModel,
  getXinferenceRegistrations,
  getXinferenceCached,
  getXinferenceRunning,
  getModels,
  queryXinferenceCatalog,
  terminateModel,
  updateModel,
  type ModelConfig,
  type ModelConfigInput,
  type ModelType,
} from '@/api/client'

type FormState = Omit<ModelConfigInput, 'dimension' | 'runtime_config'> & {
  dimension: string
  runtime_config_json: string
}

function emptyForm(): FormState {
  return {
    model_key: '',
    display_name: '',
    model_type: 'chat',
    provider: 'geekai',
    model_name: '',
    endpoint: '',
    dimension: '',
    enabled: true,
    notes: '',
    runtime_config_json: '{}',
  }
}

const models = ref<ModelConfig[]>([])
const loading = ref(true)
const saving = ref(false)
const activatingId = ref<string | null>(null)
const error = ref('')
const activationMessage = ref('')
const editingId = ref<string | null>(null)
const form = reactive<FormState>(emptyForm())
const runtimeEndpoint = ref('')
const runtimeType = ref<'LLM' | 'embedding'>('embedding')
const runtimeModels = ref<Array<Record<string, unknown>>>([])
const runningModels = ref<Array<Record<string, unknown>>>([])
const cachedModels = ref<Array<Record<string, unknown>>>([])
const runtimeLoading = ref(false)
const deployingId = ref<string | null>(null)
const formOpen = ref(false)
const catalogItems = ref<Array<{
  model_name: string
  model_type: string
  downloaded: boolean
  running: boolean
  parameters: Record<string, unknown>
}>>([])
const catalogTotal = ref(0)
const catalogPage = ref(1)
const catalogPageSize = 10
const catalogNameQuery = ref('')
const catalogParamQuery = ref('')
const catalogDownloaded = ref<'all' | 'yes' | 'no'>('all')

function resetForm() {
  Object.assign(form, emptyForm())
  editingId.value = null
}

function closeForm() {
  resetForm()
  formOpen.value = false
}

function typeLabel(type: ModelType) {
  return { chat: '对话', embedding: 'Embedding', vision: '视觉' }[type]
}

const providerOptions: Record<ModelType, Array<{ value: string; label: string }>> = {
  chat: [
    { value: 'geekai', label: 'GeekAI 中转站' },
    { value: 'openai', label: 'OpenAI 官方 API' },
    { value: 'xinference', label: 'Xinference 本地模型' },
    { value: 'ollama', label: 'Ollama 本地模型' },
  ],
  embedding: [
    { value: 'xinference', label: 'Xinference 本地模型' },
    { value: 'tei', label: 'TEI 本地服务' },
    { value: 'geekai', label: 'GeekAI 中转站' },
    { value: 'openai', label: 'OpenAI 官方 API' },
    { value: 'mock', label: 'Mock（联调）' },
  ],
  vision: [{ value: 'xinference', label: 'Xinference（预留）' }],
}

function providerLabel(provider: string) {
  for (const options of Object.values(providerOptions)) {
    const item = options.find((option) => option.value === provider)
    if (item) return item.label
  }
  return provider
}

function endpointRequired() {
  return ['xinference', 'tei', 'ollama'].includes(form.provider)
}

function endpointPlaceholder() {
  if (form.provider === 'ollama') return 'http://localhost:11434/v1'
  if (form.provider === 'xinference' || form.provider === 'tei') return 'http://winpc:9997/v1'
  if (form.provider === 'openai') return '默认 https://api.openai.com/v1'
  return '留空则使用 .env 中的 GeekAI 地址'
}

function credentialHint() {
  if (form.provider === 'openai') return '凭据读取 .env 中的 OPENAI_API_KEY。'
  if (form.provider === 'geekai') return '凭据读取 .env 中的 GEEKAI_API_KEY。'
  if (form.provider === 'mock') return 'Mock 不会请求外部模型服务。'
  return '本地服务不在页面保存密钥；如服务需要认证，读取 .env 中的 EMBEDDING_API_KEY。'
}

watch(
  () => form.model_type,
  (modelType) => {
    const options = providerOptions[modelType]
    if (!options.some((option) => option.value === form.provider)) {
      form.provider = options[0]!.value
    }
  },
)

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    models.value = await getModels()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法加载模型列表'
  } finally {
    loading.value = false
  }
}

function runtimeModelName(item: Record<string, unknown>) {
  return String(item.model_name || item.model_uid || item.id || '-')
}

function runningFor(item: ModelConfig) {
  return runningModels.value.find(
    (runtime) => runtime.model_name === item.model_name || runtime.id === item.model_name,
  )
}

async function refreshRuntime() {
  runtimeLoading.value = true
  error.value = ''
  try {
    const [registrations, running, cached] = await Promise.all([
      getXinferenceRegistrations(runtimeType.value, runtimeEndpoint.value || undefined),
      getXinferenceRunning(runtimeEndpoint.value || undefined),
      getXinferenceCached(runtimeEndpoint.value || undefined),
    ])
    runtimeModels.value = registrations.models
    runningModels.value = running.models
    cachedModels.value = cached.models
  } catch (e) {
    error.value = e instanceof Error ? e.message : '无法读取 Xinference 模型状态'
  } finally {
    runtimeLoading.value = false
  }
}

async function queryCatalog() {
  runtimeLoading.value = true
  error.value = ''
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
    error.value = e instanceof Error ? e.message : '无法查询 Xinference 模型'
  } finally {
    runtimeLoading.value = false
  }
}

function changeCatalogFilter() {
  catalogPage.value = 1
  void queryCatalog()
}

function openCreate() {
  resetForm()
  formOpen.value = true
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
    activationMessage.value = `${item.display_name} 已提交给 Xinference 部署/下载`
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
    activationMessage.value = `${item.display_name} 已停止`
    await refreshRuntime()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '停止模型失败'
  }
}

async function activate(item: ModelConfig) {
  const action = item.model_type === 'embedding' ? '切换后必须重建本机 FAISS 索引。仍要继续吗？' : '后续新对话将使用该模型。仍要继续吗？'
  if (!confirm(`设「${item.display_name}」为当前${typeLabel(item.model_type)}模型？${action}`)) return

  activatingId.value = item.id
  error.value = ''
  activationMessage.value = ''
  try {
    const result = await activateModel(item.id)
    activationMessage.value = result.message
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '模型切换失败'
  } finally {
    activatingId.value = null
  }
}

function edit(item: ModelConfig) {
  formOpen.value = true
  editingId.value = item.id
  Object.assign(form, {
    model_key: item.model_key,
    display_name: item.display_name,
    model_type: item.model_type,
    provider: item.provider,
    model_name: item.model_name,
    endpoint: item.endpoint || '',
    dimension: item.dimension?.toString() || '',
    enabled: item.enabled,
    notes: item.notes,
    runtime_config_json: JSON.stringify(item.runtime_config || {}, null, 2),
  })
  error.value = ''
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
    provider: form.provider.trim(),
    model_name: form.model_name.trim(),
    endpoint: form.endpoint?.trim() || null,
    dimension,
    enabled: form.enabled,
    notes: form.notes.trim(),
  }
  try {
    payload.runtime_config = form.runtime_config_json.trim()
      ? JSON.parse(form.runtime_config_json)
      : {}
    if (!payload.runtime_config || Array.isArray(payload.runtime_config) || typeof payload.runtime_config !== 'object') {
      throw new Error('Xinference 参数必须是 JSON 对象')
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Xinference 参数 JSON 格式错误'
    return
  }
  if (!payload.model_key || !payload.display_name || !payload.provider || !payload.model_name) {
    error.value = '请填写模型标识、显示名称、运行时和模型名称'
    return
  }
  if (dimension !== null && dimension <= 0) {
    error.value = '向量维度必须大于 0'
    return
  }

  saving.value = true
  error.value = ''
  try {
    if (editingId.value) {
      await updateModel(editingId.value, payload)
    } else {
      await createModel(payload)
    }
    resetForm()
    formOpen.value = false
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove(item: ModelConfig) {
  if (!confirm(`删除模型「${item.display_name}」？此操作不会停止 Xinference 中的模型进程。`)) return
  error.value = ''
  try {
    await deleteModel(item.id)
    if (editingId.value === item.id) resetForm()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

onMounted(async () => {
  await load()
  await Promise.all([refreshRuntime(), queryCatalog()])
})
</script>

<template>
  <div class="models-page">
    <div class="intro">
      <p>维护 LLMOps 可使用的模型目录。这里保存业务侧的非敏感配置，不会启动、停止或管理 Xinference 的模型进程。</p>
      <el-button :loading="loading" @click="load">
        {{ loading ? '刷新中…' : '刷新列表' }}
      </el-button>
      <el-button type="primary" @click="openCreate">新增模型</el-button>
    </div>

    <section class="runtime-card">
      <div class="runtime-head">
        <div>
          <h2>Xinference 运行时</h2>
          <p>查询可用模型，并从模型目录提交下载和启动任务。</p>
        </div>
        <el-button :loading="runtimeLoading" @click="refreshRuntime">
          {{ runtimeLoading ? '查询中…' : '刷新运行时' }}
        </el-button>
      </div>
      <div class="runtime-controls">
        <label>
          <span>Xinference API</span>
          <el-input v-model="runtimeEndpoint" placeholder="http://172.22.39.118:9997/v1" />
        </label>
        <label>
          <span>模型类型</span>
          <el-select v-model="runtimeType" @change="changeCatalogFilter">
            <el-option label="Embedding" value="embedding" />
            <el-option label="LLM / Chat" value="LLM" />
          </el-select>
        </label>
      </div>
      <div class="runtime-filters">
        <el-input v-model="catalogNameQuery" placeholder="按模型名称查询" @keyup.enter="changeCatalogFilter" />
        <el-input v-model="catalogParamQuery" placeholder="按参数查询，如 transformers / Q4 / 768" @keyup.enter="changeCatalogFilter" />
        <el-select v-model="catalogDownloaded" @change="changeCatalogFilter">
          <el-option label="全部状态" value="all" />
          <el-option label="已下载" value="yes" />
          <el-option label="未下载" value="no" />
        </el-select>
        <el-button @click="changeCatalogFilter">查询</el-button>
      </div>
      <div class="runtime-table-wrap">
        <el-table v-loading="runtimeLoading" :data="catalogItems" class="runtime-table" empty-text="暂无匹配模型">
          <el-table-column prop="model_name" label="模型名称" min-width="220" class-name="mono" />
          <el-table-column label="下载状态" width="110">
            <template #default="{ row }"><el-tag :type="row.downloaded ? 'success' : 'info'">{{ row.downloaded ? '已下载' : '未下载' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="运行状态" width="110">
            <template #default="{ row }"><el-tag :type="row.running ? 'primary' : 'info'">{{ row.running ? '运行中' : '未运行' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="参数摘要" min-width="320">
            <template #default="{ row }"><span class="param-cell" :title="JSON.stringify(row.parameters)">{{ JSON.stringify(row.parameters) }}</span></template>
          </el-table-column>
        </el-table>
      </div>
      <div class="pagination"><span>共 {{ catalogTotal }} 个模型</span><el-pagination v-model:current-page="catalogPage" :page-size="catalogPageSize" :total="catalogTotal" layout="prev, pager, next" @current-change="queryCatalog" /></div>
      <div v-if="runningModels.length" class="running-line">
        运行中：<span v-for="item in runningModels" :key="String(item.id || item.model_uid)">{{ runtimeModelName(item) }}</span>
      </div>
      <div class="cached-line">
        已下载缓存：
        <span v-if="!cachedModels.length">暂无</span>
        <span v-for="item in cachedModels" :key="String(item.model_name || item.model_version)">
          {{ String(item.model_name || item.model_version || item.model_path || '-') }}
        </span>
      </div>
    </section>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="notice" />
    <el-alert v-if="activationMessage" :title="activationMessage" type="success" show-icon :closable="false" class="notice" />

    <div class="content-grid">
      <section class="table-wrap">
        <el-table v-loading="loading" :data="models" empty-text="暂无模型。请点击新增模型创建 GeekAI、Xinference、Ollama 等模型。">
          <el-table-column label="模型" min-width="160"><template #default="{ row }"><strong>{{ row.display_name }}</strong><span class="sub mono">{{ row.model_key }}</span></template></el-table-column>
          <el-table-column label="类型" width="100"><template #default="{ row }"><el-tag>{{ typeLabel(row.model_type) }}</el-tag></template></el-table-column>
          <el-table-column label="运行时" width="110"><template #default="{ row }">{{ providerLabel(row.provider) }}</template></el-table-column>
          <el-table-column prop="model_name" label="模型名称" min-width="160" class-name="mono" />
          <el-table-column label="端点" min-width="180"><template #default="{ row }"><span class="endpoint mono" :title="row.endpoint || ''">{{ row.endpoint || '-' }}</span></template></el-table-column>
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.is_active ? 'primary' : row.enabled ? 'success' : 'info'">{{ row.is_active ? '当前使用' : row.enabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
          <el-table-column label="更新时间" width="170"><template #default="{ row }">{{ formatTime(row.updated_at) }}</template></el-table-column>
          <el-table-column label="操作" fixed="right" min-width="310">
            <template #default="{ row }">
              <el-button v-if="row.model_type !== 'vision'" link type="primary" :disabled="!row.enabled || row.is_active || activatingId === row.id" @click="activate(row)">{{ row.is_active ? '当前使用' : activatingId === row.id ? '切换中…' : '设为当前' }}</el-button>
              <el-button link @click="edit(row)">编辑</el-button>
              <el-button v-if="row.provider === 'xinference' && !runningFor(row)" link type="primary" :loading="deployingId === row.id" @click="deploy(row)">部署</el-button>
              <el-button v-if="row.provider === 'xinference' && runningFor(row)" link type="warning" @click="stopRuntime(row)">停止</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <el-dialog v-model="formOpen" :title="editingId ? '编辑模型' : '新增模型'" width="680px" :close-on-click-modal="false" @closed="closeForm">
      <section class="form-card">
        <div class="form-title">
          <h2>{{ editingId ? '编辑模型' : '新增模型' }}</h2>
          <el-button v-if="editingId" link @click="closeForm">取消编辑</el-button>
        </div>
        <form @submit.prevent="save">
          <label>
            <span>显示名称</span>
            <el-input v-model="form.display_name" required placeholder="例如：中文向量模型" />
          </label>
          <label>
            <span>模型标识</span>
            <el-input v-model="form.model_key" required placeholder="bge-base-zh" />
            <small>字母、数字、点、下划线或连字符。</small>
          </label>
          <div class="two-col">
            <label>
              <span>类型</span>
              <el-select v-model="form.model_type"><el-option label="对话 LLM" value="chat" /><el-option label="Embedding" value="embedding" /><el-option label="视觉模型" value="vision" /></el-select>
            </label>
            <label>
              <span>接入方式</span>
              <el-select v-model="form.provider"><el-option v-for="option in providerOptions[form.model_type]" :key="option.value" :label="option.label" :value="option.value" /></el-select>
            </label>
          </div>
          <label>
            <span>模型名称</span>
            <el-input
              v-model="form.model_name"
              required
              :placeholder="form.model_type === 'embedding' ? 'BAAI/bge-base-zh-v1.5' : 'deepseek / qwen / gpt 模型标识'"
            />
          </label>
          <label>
            <span>服务端点{{ endpointRequired() ? '（必填）' : '（可选）' }}</span>
            <el-input v-model="form.endpoint" :placeholder="endpointPlaceholder()" />
            <small>{{ credentialHint() }}</small>
          </label>
          <label v-if="form.model_type === 'embedding'">
            <span>向量维度（Embedding 可填）</span>
            <el-input-number v-model="form.dimension" :min="1" :step="1" placeholder="768" />
          </label>
          <label>
            <span>备注</span>
            <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="用途、显存需求或部署说明" />
          </label>
          <label v-if="form.provider === 'xinference'">
            <span>Xinference 启动参数（JSON）</span>
            <el-input
              v-model="form.runtime_config_json"
              type="textarea"
              :rows="5"
              placeholder='{"model_engine":"sentence_transformers","model_format":"pytorch","download_hub":"modelscope","gpu_idx":[0]}'
            />
            <small>参数会保存到 PostgreSQL，下次部署直接复用。</small>
          </label>
          <label class="toggle">
            <el-switch v-model="form.enabled" />
            <span>在模型目录中启用</span>
          </label>
          <el-button type="primary" native-type="submit" :loading="saving">
            {{ saving ? '保存中…' : editingId ? '保存修改' : '新增模型' }}
          </el-button>
        </form>
      </section>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped>
.models-page { flex: 1; overflow-y: auto; padding: 1.5rem 2rem 2rem; }
.intro { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.25rem; color: #6e6e80; font-size: .875rem; }
.intro p { margin: 0; max-width: 48rem; line-height: 1.5; }
.runtime-card { margin-bottom: 1.25rem; padding: 1rem 1.25rem; border: 1px solid var(--border); border-radius: .75rem; background: var(--main-bg); }
.runtime-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.runtime-head h2 { margin: 0; font-size: 1rem; }
.runtime-head p { margin: .35rem 0 0; color: #6e6e80; font-size: .8125rem; }
.runtime-controls { display: grid; grid-template-columns: minmax(0, 1fr) 12rem; gap: .75rem; margin-top: .9rem; }
.runtime-filters { display: grid; grid-template-columns: 1fr 1.3fr 10rem auto; gap: .5rem; margin-top: .8rem; }
.runtime-table-wrap { overflow-x: auto; margin-top: .8rem; border: 1px solid var(--border); border-radius: .5rem; }
.runtime-table { min-width: 760px; }
.runtime-table th, .runtime-table td { padding: .55rem .7rem; }
.param-cell { max-width: 30rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #6e6e80; }
.pagination { display: flex; align-items: center; justify-content: flex-end; gap: .65rem; margin-top: .7rem; color: #6e6e80; font-size: .75rem; }
.pagination button { border: 1px solid var(--border); border-radius: .4rem; background: var(--main-bg); padding: .3rem .55rem; cursor: pointer; }
.pagination button:disabled { cursor: default; opacity: .5; }
.runtime-list { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .8rem; }
.runtime-chip { padding: .25rem .5rem; border-radius: 99px; background: rgba(84, 54, 218, .1); color: #5436da; font: .75rem ui-monospace, SFMono-Regular, Menlo, monospace; }
.runtime-empty { color: #8e8e8e; font-size: .8125rem; }
.running-line { margin-top: .7rem; color: #08775a; font-size: .8125rem; }
.running-line span { margin-left: .5rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.cached-line { margin-top: .55rem; color: #6e6e80; font-size: .8125rem; }
.cached-line span { display: inline-block; margin-left: .5rem; color: #5436da; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.refresh-btn, .actions button { border: 1px solid var(--border); background: var(--main-bg); border-radius: .5rem; padding: .45rem .75rem; cursor: pointer; white-space: nowrap; }
.refresh-btn:disabled, .save-btn:disabled { cursor: not-allowed; opacity: .55; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr) 22rem; gap: 1.25rem; align-items: start; }
.table-wrap, .form-card { border: 1px solid var(--border); border-radius: .75rem; background: var(--main-bg); overflow: hidden; }
.table-wrap { overflow-x: auto; }
table { width: 100%; min-width: 800px; border-collapse: collapse; font-size: .8125rem; }
th { text-align: left; padding: .75rem 1rem; background: var(--assistant-bg); color: #6e6e80; font-weight: 500; white-space: nowrap; }
td { padding: .75rem 1rem; border-top: 1px solid var(--border); vertical-align: middle; }
tr:hover td { background: rgba(0, 0, 0, .02); }
.sub { display: block; margin-top: .25rem; color: #8e8e8e; font-size: .75rem; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .75rem; }
.endpoint { max-width: 11rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-tag, .state { display: inline-block; border-radius: 99px; padding: .2rem .5rem; font-size: .75rem; white-space: nowrap; }
.type-tag { background: rgba(84, 54, 218, .1); color: #5436da; }
.state.enabled { background: rgba(16, 163, 127, .12); color: #08775a; }
.state.current { background: rgba(84, 54, 218, .13); color: #5436da; font-weight: 600; }
.state.disabled { background: #eee; color: #777; }
.time { color: #6e6e80; white-space: nowrap; }
.actions { display: flex; gap: .35rem; white-space: nowrap; }
.actions button { padding: .3rem .55rem; font-size: .75rem; }
.actions .danger { color: var(--error); }
.actions .activate { border-color: var(--accent); color: var(--accent); }
.actions .activate:disabled { cursor: default; opacity: .6; }
.empty { text-align: center; color: #8e8e8e; padding: 2rem !important; }
.form-card { padding: 1.25rem; }
.modal-card { position: fixed; z-index: 20; top: 8vh; right: 5vw; width: min(34rem, 90vw); max-height: 84vh; overflow-y: auto; box-shadow: 0 1rem 3rem rgba(0, 0, 0, .2); }
.form-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.form-title h2 { margin: 0; font-size: 1rem; }
.text-btn { border: 0; background: transparent; color: #6e6e80; cursor: pointer; }
form { display: flex; flex-direction: column; gap: .85rem; }
label { display: flex; flex-direction: column; gap: .35rem; font-size: .8125rem; font-weight: 500; }
input, select, textarea { box-sizing: border-box; width: 100%; padding: .55rem .65rem; border: 1px solid var(--input-border); border-radius: .45rem; background: var(--input-bg); color: var(--main-text); font: inherit; font-size: .8125rem; }
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(16, 163, 127, .12); }
small { color: #8e8e8e; font-weight: 400; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }
.toggle { flex-direction: row; align-items: center; cursor: pointer; font-weight: 400; }
.toggle input { width: auto; }
.save-btn { border: 0; border-radius: .5rem; padding: .6rem .9rem; background: var(--accent); color: white; cursor: pointer; font: inherit; font-size: .875rem; }
.error { margin: 0 0 1rem; color: var(--error); font-size: .875rem; }
.success { margin: 0 0 1rem; color: #08775a; font-size: .875rem; }
@media (max-width: 1250px) { .content-grid { grid-template-columns: 1fr; } .form-card { max-width: 42rem; } }
</style>
