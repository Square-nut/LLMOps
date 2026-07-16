<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import {
  ChatDotRound,
  Collection,
  Cpu,
  DocumentAdd,
  Plus,
  Setting,
  Tickets,
} from '@element-plus/icons-vue'
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
  if (route.name === 'models') return '模型管理'
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
        <el-button class="new-chat-btn" @click="startNewChat">
          <el-icon><Plus /></el-icon>
          新对话
        </el-button>
      </div>

      <div class="conversation-section">
        <div v-if="conversations.length > 0" class="section-label">最近</div>
        <div class="conversation-list">
          <el-button
            v-for="conv in conversations"
            :key="conv.id"
            text
            class="conversation-item"
            :class="{ active: conv.id === chatStore.activeId && route.name === 'chat' }"
            :title="conv.title"
            @click="openConversation(conv.id)"
          >
            <el-icon class="conv-icon"><ChatDotRound /></el-icon>
            <span class="conv-title">{{ conv.title }}</span>
            <span
              class="conv-delete"
              role="button"
              aria-label="删除对话"
              @click="onDeleteConversation($event, conv.id)"
            >
              ×
            </span>
          </el-button>
        </div>
      </div>

      <div class="sidebar-bottom">
        <el-menu class="sidebar-nav" :default-active="route.path" router background-color="#171717" text-color="#ececec" active-text-color="#ffffff">
          <el-menu-item index="/ingest"><el-icon><DocumentAdd /></el-icon><span>文档入库</span></el-menu-item>
          <el-menu-item index="/logs"><el-icon><Tickets /></el-icon><span>使用日志</span></el-menu-item>
          <el-menu-item index="/status"><el-icon><Collection /></el-icon><span>系统状态</span></el-menu-item>
          <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>运行配置</span></el-menu-item>
          <el-menu-item index="/models"><el-icon><Cpu /></el-icon><span>模型管理</span></el-menu-item>
        </el-menu>
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
