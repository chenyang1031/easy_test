import { defineStore } from 'pinia'
import { testSuiteApi } from '../api/index.js'

export const useTestSuiteStore = defineStore('testSuite', {
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
        const data = await testSuiteApi.list(p)
        this.list = data.results || data
        this.total = data.count || 0
      } catch (e) { this.error = e.message; this.list = [] }
      finally { this.loading = false }
    },
    async loadDetail(id) {
      this.loading = true
      try { this.current = await testSuiteApi.get(id) }
      catch (e) { this.error = e.message; this.current = null }
      finally { this.loading = false }
    },
    async create(data) { return await testSuiteApi.create(data) },
    async update(id, data) { return await testSuiteApi.update(id, data) },
    async remove(id) { await testSuiteApi.remove(id) },
    async addTestCase(id, data) { return await testSuiteApi.addTestCase(id, data) },
    async removeTestCase(id, data) { return await testSuiteApi.removeTestCase(id, data) },
    async updateTestCaseEnv(id, data) { return await testSuiteApi.updateTestCaseEnv(id, data) },
    async run(id, data) { return await testSuiteApi.run(id, data) },
    async batchRun(ids, envId) { return await testSuiteApi.batchRun(ids, envId) },
  }
})
