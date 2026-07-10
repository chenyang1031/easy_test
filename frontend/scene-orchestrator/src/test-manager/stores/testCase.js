import { defineStore } from 'pinia'
import { testCaseApi } from '../api/index.js'

export const useTestCaseStore = defineStore('testCase', {
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
        const data = await testCaseApi.list(p)
        this.list = data.results || data
        this.total = data.count || 0
      } catch (e) { this.error = e.message; this.list = [] }
      finally { this.loading = false }
    },
    async loadDetail(id) {
      this.loading = true
      try { this.current = await testCaseApi.get(id) }
      catch (e) { this.error = e.message; this.current = null }
      finally { this.loading = false }
    },
    async create(data) { return await testCaseApi.create(data) },
    async update(id, data) { return await testCaseApi.update(id, data) },
    async remove(id) { await testCaseApi.remove(id) },
    async batchDelete(ids) {
      const data = await testCaseApi.batchDelete(ids)
      this.total -= data.deleted_count || 0
      await this.loadList()
      return data
    },
    async run(id, envId) { return await testCaseApi.run(id, { environment_id: envId }) },
  }
})
