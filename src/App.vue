<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

const conversations = computed(() => chatStore.sortedConversations)

function pageTitle() {
  if (route.name === 'ingest') return '文档入库'
  if (route.name === 'logs') return '使用日志'
  if (route.name === 'status') return '系统状态'
  if (route.name === 'settings') return '运行配置'
  return 'LLMOps'
}

function startNewChat() {
  chatStore.newChat()
  if (route.name !== 'chat') {
    router.push('/')
  }
}

function openConversation(id: string) {
  chatStore.selectConversation(id)
  if (route.name !== 'chat') {
    router.push('/')
  }
}

function onDeleteConversation(e: Event, id: string) {
  e.stopPropagation()
  chatStore.deleteConversation(id)
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <button type="button" class="new-chat-btn" @click="startNewChat">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          新对话
        </button>
      </div>

      <div class="conversation-section">
        <div v-if="conversations.length > 0" class="section-label">最近</div>
        <div class="conversation-list">
          <button
            v-for="conv in conversations"
            :key="conv.id"
            type="button"
            class="conversation-item"
            :class="{ active: conv.id === chatStore.activeId && route.name === 'chat' }"
            :title="conv.title"
            @click="openConversation(conv.id)"
          >
            <svg class="conv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M8 10h8M8 14h5M5 4h14a2 2 0 0 1 2 2v11l-3-2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />
            </svg>
            <span class="conv-title">{{ conv.title }}</span>
            <span
              class="conv-delete"
              role="button"
              aria-label="删除对话"
              @click="onDeleteConversation($event, conv.id)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </span>
          </button>
        </div>
      </div>

      <div class="sidebar-bottom">
        <nav class="sidebar-nav">
          <RouterLink to="/ingest" class="nav-item" active-class="active">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
              <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
            </svg>
            文档入库
          </RouterLink>
          <RouterLink to="/logs" class="nav-item" active-class="active">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 19h16M4 15h16M4 11h16M4 7h10" />
            </svg>
            使用日志
          </RouterLink>
          <RouterLink to="/status" class="nav-item" active-class="active">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </svg>
            系统状态
          </RouterLink>
          <RouterLink to="/settings" class="nav-item" active-class="active">
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 6h16M4 12h16M4 18h16" />
              <circle cx="8" cy="6" r="1.5" />
              <circle cx="15" cy="12" r="1.5" />
              <circle cx="11" cy="18" r="1.5" />
            </svg>
            运行配置
          </RouterLink>
        </nav>
        <div class="sidebar-footer">
          <span class="brand">LLMOps</span>
        </div>
      </div>
    </aside>

    <div class="main">
      <header v-if="route.name !== 'chat'" class="main-header">
        <h1>{{ pageTitle() }}</h1>
      </header>
      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  width: 100%;
  height: 100vh;
  min-width: 1024px;
}

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  padding: 0.5rem;
  min-height: 0;
}

.sidebar-top {
  flex-shrink: 0;
  padding: 0.25rem;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.625rem 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.625rem;
  background: transparent;
  color: var(--sidebar-text);
  font-size: 0.875rem;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.new-chat-btn:hover {
  background: var(--sidebar-hover);
}

.btn-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

.conversation-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 0.5rem;
  padding: 0 0.25rem;
}

.section-label {
  flex-shrink: 0;
  padding: 0.5rem 0.625rem 0.375rem;
  font-size: 0.75rem;
  color: var(--sidebar-muted);
  font-weight: 500;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding-bottom: 0.5rem;
}

.conversation-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.5rem 0.625rem;
  border: none;
  border-radius: 0.625rem;
  background: transparent;
  color: var(--sidebar-text);
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.conversation-item:hover {
  background: var(--sidebar-hover);
}

.conversation-item.active {
  background: var(--sidebar-hover);
}

.conv-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  opacity: 0.7;
}

.conv-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-delete {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  opacity: 0;
  color: var(--sidebar-muted);
  transition: opacity 0.15s, background 0.15s, color 0.15s;
}

.conv-delete svg {
  width: 0.875rem;
  height: 0.875rem;
}

.conversation-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.sidebar-bottom {
  flex-shrink: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 0.5rem;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.625rem;
  border-radius: 0.625rem;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.15s;
}

.nav-item:hover {
  background: var(--sidebar-hover);
}

.nav-item.active {
  background: var(--sidebar-hover);
}

.nav-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  opacity: 0.85;
}

.sidebar-footer {
  padding: 0.625rem 0.75rem 0.5rem;
  font-size: 0.75rem;
  color: var(--sidebar-muted);
}

.brand {
  font-weight: 600;
  letter-spacing: 0.02em;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--main-bg);
  height: 100vh;
}

.main-header {
  flex-shrink: 0;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
}

.main-header h1 {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}
</style>
