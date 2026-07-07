import { defineStore } from 'pinia'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  meta?: string
}

export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: number
}

const STORAGE_KEY = 'llmops_conversations'

function loadState(): { conversations: Conversation[]; activeId: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        conversations: Array.isArray(parsed.conversations) ? parsed.conversations : [],
        activeId: parsed.activeId ?? null,
      }
    }
  } catch {
    // ignore
  }
  return { conversations: [], activeId: null }
}

function saveState(conversations: Conversation[], activeId: string | null) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ conversations, activeId }))
}

function makeTitle(text: string) {
  const t = text.trim().replace(/\s+/g, ' ')
  if (!t) return '新对话'
  return t.length > 28 ? t.slice(0, 28) + '…' : t
}

export const useChatStore = defineStore('chat', {
  state: () => {
    const saved = loadState()
    return {
      conversations: saved.conversations,
      activeId: saved.activeId,
    }
  },
  getters: {
    activeConversation(state): Conversation | null {
      if (!state.activeId) return null
      return state.conversations.find((c) => c.id === state.activeId) ?? null
    },
    sortedConversations(state): Conversation[] {
      return [...state.conversations].sort((a, b) => b.updatedAt - a.updatedAt)
    },
  },
  actions: {
    persist() {
      saveState(this.conversations, this.activeId)
    },

    newChat() {
      const conv: Conversation = {
        id: crypto.randomUUID(),
        title: '新对话',
        messages: [],
        updatedAt: Date.now(),
      }
      this.conversations.unshift(conv)
      this.activeId = conv.id
      this.persist()
    },

    ensureActive() {
      if (!this.activeId || !this.conversations.some((c) => c.id === this.activeId)) {
        const first = this.sortedConversations[0]
        if (first) {
          this.activeId = first.id
        } else {
          this.newChat()
        }
      }
      this.persist()
    },

    selectConversation(id: string) {
      if (this.conversations.some((c) => c.id === id)) {
        this.activeId = id
        this.persist()
      }
    },

    deleteConversation(id: string) {
      const idx = this.conversations.findIndex((c) => c.id === id)
      if (idx === -1) return

      this.conversations.splice(idx, 1)
      if (this.activeId === id) {
        this.activeId = this.conversations[0]?.id ?? null
        if (!this.activeId && this.conversations.length === 0) {
          this.newChat()
        }
      }
      this.persist()
    },

    setMessages(id: string, messages: ChatMessage[]) {
      const conv = this.conversations.find((c) => c.id === id)
      if (!conv) return
      conv.messages = messages
      conv.updatedAt = Date.now()
      this.persist()
    },

    appendMessages(id: string, items: ChatMessage[]) {
      const conv = this.conversations.find((c) => c.id === id)
      if (!conv) return
      conv.messages.push(...items)
      const firstUser = conv.messages.find((m) => m.role === 'user')
      if (firstUser && conv.title === '新对话') {
        conv.title = makeTitle(firstUser.content)
      }
      conv.updatedAt = Date.now()
      this.persist()
    },
  },
})
