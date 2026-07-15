<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  createModel,
  deleteModel,
  getModels,
  updateModel,
  type ModelConfig,
  type ModelConfigInput,
  type ModelType,
} from '@/api/client'

type FormState = Omit<ModelConfigInput, 'dimension'> & { dimension: string }

function emptyForm(): FormState {
  return {
    model_key: '',
    display_name: '',
    model_type: 'chat',
    provider: 'xinference',
    model_name: '',
    endpoint: '',
    dimension: '',
    enabled: true,
    notes: '',
  }
}

const models = ref<ModelConfig[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const editingId = ref<string | null>(null)
const form = reactive<FormState>(emptyForm())

function resetForm() {
  Object.assign(form, emptyForm())
  editingId.value = null
}

function typeLabel(type: ModelType) {
  return { chat: '对话', embedding: 'Embedding', vision: '视觉' }[type]
}

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

function edit(item: ModelConfig) {
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

onMounted(load)
</script>

<template>
  <div class="models-page">
    <div class="intro">
      <p>维护 LLMOps 可使用的模型目录。这里保存业务侧的非敏感配置，不会启动、停止或管理 Xinference 的模型进程。</p>
      <button type="button" class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? '刷新中…' : '刷新列表' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="content-grid">
      <section class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>模型</th>
              <th>类型</th>
              <th>运行时</th>
              <th>模型名称</th>
              <th>端点</th>
              <th>状态</th>
              <th>更新时间</th>
              <th aria-label="操作" />
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && models.length === 0">
              <td colspan="8" class="empty">暂无模型。可从右侧新增 GeekAI、Xinference、Ollama 等模型。</td>
            </tr>
            <tr v-for="item in models" :key="item.id">
              <td>
                <strong>{{ item.display_name }}</strong>
                <span class="sub mono">{{ item.model_key }}</span>
              </td>
              <td><span class="type-tag">{{ typeLabel(item.model_type) }}</span></td>
              <td>{{ item.provider }}</td>
              <td class="mono">{{ item.model_name }}</td>
              <td class="endpoint mono" :title="item.endpoint || ''">{{ item.endpoint || '-' }}</td>
              <td><span class="state" :class="item.enabled ? 'enabled' : 'disabled'">{{ item.enabled ? '启用' : '停用' }}</span></td>
              <td class="time">{{ formatTime(item.updated_at) }}</td>
              <td class="actions">
                <button type="button" @click="edit(item)">编辑</button>
                <button type="button" class="danger" @click="remove(item)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="form-card">
        <div class="form-title">
          <h2>{{ editingId ? '编辑模型' : '新增模型' }}</h2>
          <button v-if="editingId" type="button" class="text-btn" @click="resetForm">取消编辑</button>
        </div>
        <form @submit.prevent="save">
          <label>
            <span>显示名称</span>
            <input v-model="form.display_name" required placeholder="例如：中文向量模型" />
          </label>
          <label>
            <span>模型标识</span>
            <input v-model="form.model_key" required pattern="[A-Za-z0-9._-]+" placeholder="bge-base-zh" />
            <small>字母、数字、点、下划线或连字符。</small>
          </label>
          <div class="two-col">
            <label>
              <span>类型</span>
              <select v-model="form.model_type">
                <option value="chat">对话 LLM</option>
                <option value="embedding">Embedding</option>
                <option value="vision">视觉模型</option>
              </select>
            </label>
            <label>
              <span>运行时 / Provider</span>
              <input v-model="form.provider" required placeholder="xinference、geekai、ollama…" />
            </label>
          </div>
          <label>
            <span>模型名称</span>
            <input v-model="form.model_name" required placeholder="BAAI/bge-base-zh-v1.5" />
          </label>
          <label>
            <span>服务端点（可选）</span>
            <input v-model="form.endpoint" type="url" placeholder="http://winpc:9997/v1" />
          </label>
          <label>
            <span>向量维度（Embedding 可填）</span>
            <input v-model="form.dimension" type="number" min="1" step="1" placeholder="768" />
          </label>
          <label>
            <span>备注</span>
            <textarea v-model="form.notes" rows="3" placeholder="用途、显存需求或部署说明" />
          </label>
          <label class="toggle">
            <input v-model="form.enabled" type="checkbox" />
            <span>在模型目录中启用</span>
          </label>
          <button type="submit" class="save-btn" :disabled="saving">
            {{ saving ? '保存中…' : editingId ? '保存修改' : '新增模型' }}
          </button>
        </form>
      </section>
    </div>
  </div>
</template>

<style scoped>
.models-page { flex: 1; overflow-y: auto; padding: 1.5rem 2rem 2rem; }
.intro { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.25rem; color: #6e6e80; font-size: .875rem; }
.intro p { margin: 0; max-width: 48rem; line-height: 1.5; }
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
.state.disabled { background: #eee; color: #777; }
.time { color: #6e6e80; white-space: nowrap; }
.actions { display: flex; gap: .35rem; white-space: nowrap; }
.actions button { padding: .3rem .55rem; font-size: .75rem; }
.actions .danger { color: var(--error); }
.empty { text-align: center; color: #8e8e8e; padding: 2rem !important; }
.form-card { padding: 1.25rem; }
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
@media (max-width: 1250px) { .content-grid { grid-template-columns: 1fr; } .form-card { max-width: 42rem; } }
</style>
