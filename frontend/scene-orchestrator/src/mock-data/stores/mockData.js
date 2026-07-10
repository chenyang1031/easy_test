import { defineStore } from 'pinia'
import { mockDataApi } from '../api/index.js'

export const useMockDataStore = defineStore('mockData', {
  state: () => ({
    list: [],
    current: null,
    loading: false,
    error: null,
    total: 0,
    page: 1,
    pageSize: 10,
  }),
  actions: {
    async loadList(params = {}) {
      this.loading = true; this.error = null
      try {
        const p = { page: this.page, page_size: this.pageSize, ...params }
        const data = await mockDataApi.list(p)
        this.list = data.results || data
        this.total = data.count || 0
      } catch (e) {
        this.error = e.message
        this.list = []
      } finally {
        this.loading = false
      }
    },
    async remove(id) {
      await mockDataApi.remove(id)
      this.total -= 1
      await this.loadList()
    },
  },
})
