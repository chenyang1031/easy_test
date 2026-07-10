import { defineStore } from 'pinia'
import { projectApi } from '../api/index.js'

export const useProjectManageStore = defineStore('projectManage', {
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
        const data = await projectApi.list(p)
        this.list = data.results || data
        this.total = data.count || 0
      } catch (e) { this.error = e.message; this.list = [] }
      finally { this.loading = false }
    },
    async loadDetail(id) {
      this.loading = true
      try { this.current = await projectApi.get(id) }
      catch (e) { this.error = e.message; this.current = null }
      finally { this.loading = false }
    },
    async create(data) { return await projectApi.create(data) },
    async update(id, data) { return await projectApi.update(id, data) },
    async remove(id) {
      await projectApi.remove(id)
      this.total = Math.max(0, this.total - 1)
      await this.loadList()
    },
  }
})
