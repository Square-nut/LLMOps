import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', {
  state: () => ({
    resetSignal: 0,
  }),
  actions: {
    newChat() {
      this.resetSignal += 1
    },
  },
})
