<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { postChat, type ChatResponse } from '@/api/client'
import { useChatStore } from '@/stores/chat'

interface Message {
  role: 'user' | 'assistant'
  content: string
  meta?: string
}

const chatStore = useChatStore()
const messages = ref<Message[]>([])
const input = ref('')
const useRag = ref(true)
const loading = ref(false)
const error = ref('')
const listRef = ref<HTMLElement | null>(null)

watch(
  () => chatStore.resetSignal,
  () => {
    messages.value = []
    error.value = ''
    input.value = ''
  },
)

async function scrollToBottom() {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

function formatMeta(res: ChatResponse) {
  return `${res.model} · ${res.latency_ms}ms · ${res.tokens.total} tokens${res.used_rag ? ' · RAG' : ''}`
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  error.value = ''
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const res = await postChat({ message: text, use_rag: useRag.value })
    messages.value.push({
      role: 'assistant',
      content: res.reply,
      meta: formatMeta(res),
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请求失败'
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="chat-layout">
    <div ref="listRef" class="messages-area">
      <div v-if="messages.length === 0" class="welcome">
        <h2>有什么可以帮忙的？</h2>
        <p>基于 RAG 的知识库问答。在侧栏可切换文档入库与系统状态。</p>
      </div>

      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message-row"
        :class="msg.role"
      >
        <div class="message-inner">
          <div class="avatar">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
          <div class="content">
            <div class="text">{{ msg.content }}</div>
            <div v-if="msg.meta" class="meta">{{ msg.meta }}</div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="message-row assistant">
        <div class="message-inner">
          <div class="avatar">AI</div>
          <div class="content">
            <div class="text typing">思考中…</div>
          </div>
        </div>
      </div>
    </div>

    <div class="composer-area">
      <div class="composer-wrap">
        <label class="rag-toggle">
          <input v-model="useRag" type="checkbox" />
          启用 RAG 检索
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="composer">
          <textarea
            v-model="input"
            rows="1"
            placeholder="发送消息…"
            :disabled="loading"
            @keydown="onKeydown"
          />
          <button
            type="button"
            class="send-btn"
            :disabled="loading || !input.trim()"
            aria-label="发送"
            @click="send"
          >
            ↑
          </button>
        </div>
        <p class="hint">Enter 发送 · Shift+Enter 换行</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  min-height: 0;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  padding: 2rem;
}

.welcome h2 {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--main-text);
}

.welcome p {
  color: #6e6e80;
  font-size: 1rem;
  max-width: 480px;
}

.message-row {
  width: 100%;
  border-bottom: 1px solid transparent;
}

.message-row.user {
  background: var(--main-bg);
}

.message-row.assistant {
  background: var(--assistant-bg);
}

.message-inner {
  display: flex;
  gap: 1.5rem;
  max-width: 48rem;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.avatar {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.user .avatar {
  background: #5436da;
  color: #fff;
}

.assistant .avatar {
  background: var(--accent);
  color: #fff;
}

.content {
  flex: 1;
  min-width: 0;
  padding-top: 0.125rem;
}

.text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  font-size: 1rem;
}

.text.typing {
  color: #6e6e80;
}

.meta {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #8e8e8e;
}

.composer-area {
  flex-shrink: 0;
  padding: 1rem 2rem 1.5rem;
  background: linear-gradient(180deg, transparent, var(--main-bg) 20%);
}

.composer-wrap {
  max-width: 48rem;
  margin: 0 auto;
}

.rag-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #6e6e80;
  margin-bottom: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.error {
  color: var(--error);
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.composer {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 0.75rem 0.75rem 1rem;
  border: 1px solid var(--input-border);
  border-radius: 1.5rem;
  background: var(--input-bg);
  box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.06);
}

.composer textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.5;
  max-height: 200px;
  min-height: 24px;
  background: transparent;
  color: var(--main-text);
}

.send-btn {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 50%;
  background: var(--main-text);
  color: #fff;
  font-size: 1.125rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:hover:not(:disabled) {
  background: #333;
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.hint {
  text-align: center;
  font-size: 0.75rem;
  color: #8e8e8e;
  margin-top: 0.5rem;
}
</style>
