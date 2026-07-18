import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import IngestView from '../views/IngestView.vue'
import LogsView from '../views/LogsView.vue'
import MonitorView from '../views/MonitorView.vue'
import ModelsView from '../views/ModelsView.vue'
import SettingsView from '../views/SettingsView.vue'
import StatusView from '../views/StatusView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: ChatView,
    },
    {
      path: '/ingest',
      name: 'ingest',
      component: IngestView,
    },
    {
      path: '/logs',
      name: 'logs',
      component: LogsView,
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: MonitorView,
    },
    {
      path: '/status',
      name: 'status',
      component: StatusView,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
    {
      path: '/models',
      name: 'models',
      component: ModelsView,
    },
  ],
})

export default router
