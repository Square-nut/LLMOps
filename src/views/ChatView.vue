<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { postChat, type ChatResponse } from '@/api/client'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const input = ref('')
const useRag = ref(true)
const loading = ref(false)
const error = ref('')
const listRef = ref<HTMLElement | null>(null)

const messages = computed(() => chatStore.activeConversation?.messages ?? [])

onMounted(() => {
  chatStore.ensureActive()
})

watch(
  () => chatStore.activeId,
  async () => {
    error.value = ''
    input.value = ''
    await scrollToBottom()
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
  const convId = chatStore.activeId
  if (!text || loading.value || !convId) return

  error.value = ''
  const userMsg = { role: 'user' as const, content: text }
  chatStore.appendMessages(convId, [userMsg])
  input.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const res = await postChat({ message: text, use_rag: useRag.value })
    chatStore.appendMessages(convId, [
      {
        role: 'assistant',
        content: res.reply,
        meta: formatMeta(res),
      },
    ])
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

      <article
        v-for="(msg, i) in messages"
        :key="i"
        class="message-block"
        :class="msg.role"
      >
        <div class="message-inner">
          <div class="avatar" :class="msg.role">
            <span v-if="msg.role === 'user'" class="avatar-label">你</span>
            <svg v-else class="avatar-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a7 7 0 0 1 7 7v1.5a3.5 3.5 0 0 1-3.5 3.5h-.5v1a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-1h-.5A3.5 3.5 0 0 1 5 10.5V9a7 7 0 0 1 7-7zm-2 16h4v2h-4v-2z" />
            </svg>
          </div>
          <div class="bubble">
            <div class="text">{{ msg.content }}</div>
            <div v-if="msg.meta" class="meta">{{ msg.meta }}</div>
          </div>
        </div>
      </article>

      <article v-if="loading" class="message-block assistant">
        <div class="message-inner">
          <div class="avatar assistant">
            <svg class="avatar-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a7 7 0 0 1 7 7v1.5a3.5 3.5 0 0 1-3.5 3.5h-.5v1a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-1h-.5A3.5 3.5 0 0 1 5 10.5V9a7 7 0 0 1 7-7zm-2 16h4v2h-4v-2z" />
            </svg>
          </div>
          <div class="bubble">
            <div class="text typing">
              <span class="dot" />
              <span class="dot" />
              <span class="dot" />
            </div>
          </div>
        </div>
      </article>
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
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M12 3.5l7 7-1.4 1.4L13 7.3V20h-2V7.3l-4.6 4.6L5 10.5l7-7z" />
            </svg>
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
  font-size: 1.75rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--main-text);
}

.welcome p {
  color: #6e6e80;
  font-size: 0.9375rem;
  max-width: 480px;
}

.message-block {
  width: 100%;
}

.message-block.user {
  background: var(--main-bg);
}

.message-block.assistant {
  background: var(--assistant-bg);
}

.message-inner {
  display: flex;
  gap: 1rem;
  max-width: 46rem;
  margin: 0 auto;
  padding: 1.25rem 1.5rem;
}

.avatar {
  flex-shrink: 0;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.125rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.125rem;
}

.avatar.user {
  background: #5436da;
  color: #fff;
}

.avatar.assistant {
  background: var(--accent);
  color: #fff;
}

.avatar-label {
  font-size: 0.625rem;
  font-weight: 700;
}

.avatar-icon {
  width: 1rem;
  height: 1rem;
}

.bubble {
  flex: 1;
  min-width: 0;
}

.text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
  font-size: 1rem;
  color: var(--main-text);
}

.text.typing {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0;
}

.dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #8e8e8e;
  animation: pulse 1.2s ease-in-out infinite;
}

.dot:nth-child(2) {
  animation-delay: 0.15s;
}

.dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes pulse {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: scale(0.9);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

.meta {
  margin-top: 0.625rem;
  font-size: 0.75rem;
  color: #8e8e8e;
}

.composer-area {
  flex-shrink: 0;
  padding: 0.75rem 1.5rem 1.25rem;
  background: linear-gradient(180deg, transparent, var(--main-bg) 24%);
}

.composer-wrap {
  max-width: 46rem;
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
  padding: 0.625rem 0.625rem 0.625rem 1rem;
  border: 1px solid var(--input-border);
  border-radius: 1.625rem;
  background: var(--input-bg);
  box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.05), 0 4px 16px rgba(0, 0, 0, 0.08);
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
