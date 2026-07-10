import { defineStore } from 'pinia'
import { environmentApi } from '../api/index.js'

export const useEnvironmentStore = defineStore('environment', {
  state: () => ({
    list: [],
    current: null,
    loading: false,
    error: null,
    total: 0,
    page: 1,
    pageSize: 10,
    filterProjectId: null,
  }),
  actions: {
    async loadList(params = {}) {
      this.loading = true; this.error = null
      try {
        const p = { page: this.page, page_size: this.pageSize, ...params }
        if (this.filterProjectId && !p.project) p.project = this.filterProjectId
        const data = await environmentApi.list(p)
        this.list = data.results || data
        this.total = data.count || 0
      } catch (e) { this.error = e.message; this.list = [] }
      finally { this.loading = false }
    },
    async loadDetail(id) {
      this.loading = true
      try { this.current = await environmentApi.get(id) }
      catch (e) { this.error = e.message; this.current = null }
      finally { this.loading = false }
    },
    async create(data) { return await environmentApi.create(data) },
    async update(id, data) { return await environmentApi.update(id, data) },
    async remove(id) {
      await environmentApi.remove(id)
      this.total = Math.max(0, this.total - 1)
      await this.loadList()
    },
    setProjectFilter(id) {
      this.filterProjectId = id || null
      this.page = 1
    },
  }
})
