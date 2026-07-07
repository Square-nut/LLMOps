<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'

const route = useRoute()
const chatStore = useChatStore()

function pageTitle() {
  if (route.name === 'ingest') return '文档入库'
  if (route.name === 'logs') return '使用日志'
  if (route.name === 'status') return '系统状态'
  return 'LLMOps'
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <button
          v-if="route.name === 'chat'"
          type="button"
          class="new-chat-btn"
          @click="chatStore.newChat()"
        >
          <span class="icon">+</span>
          新对话
        </button>

        <nav class="sidebar-nav">
          <RouterLink to="/" class="nav-item" active-class="active">
            <span class="icon">💬</span>
            对话
          </RouterLink>
          <RouterLink to="/ingest" class="nav-item" active-class="active">
            <span class="icon">📄</span>
            文档入库
          </RouterLink>
          <RouterLink to="/logs" class="nav-item" active-class="active">
            <span class="icon">📊</span>
            使用日志
          </RouterLink>
          <RouterLink to="/status" class="nav-item" active-class="active">
            <span class="icon">⚙</span>
            系统状态
          </RouterLink>
        </nav>
      </div>

      <div class="sidebar-footer">
        <span class="brand">LLMOps</span>
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
  justify-content: space-between;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  padding: 0.75rem;
}

.sidebar-top {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 0.5rem;
  background: transparent;
  color: var(--sidebar-text);
  font-size: 0.875rem;
  cursor: pointer;
  text-align: left;
}

.new-chat-btn:hover {
  background: var(--sidebar-hover);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.5rem;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 0.875rem;
}

.nav-item:hover {
  background: var(--sidebar-hover);
}

.nav-item.active {
  background: var(--sidebar-hover);
}

.icon {
  width: 1.25rem;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 0.75rem;
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
