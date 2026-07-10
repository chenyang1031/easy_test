import { defineStore } from 'pinia'
import { testSuiteGroupApi } from '../api/index.js'

export const useTestSuiteGroupStore = defineStore('testSuiteGroup', {
  state: () => ({
    treeData: [],
    flatList: [],
    loading: false,
    error: null,
  }),
  getters: {
    groupMap: (state) => {
      const map = {}
      const walk = (nodes) => { nodes.forEach(n => { map[n.id] = n; if (n.children) walk(n.children) }) }
      walk(state.treeData)
      return map
    },
  },
  actions: {
    async loadTree(projectId) {
      this.loading = true; this.error = null
      try { this.treeData = await testSuiteGroupApi.tree(projectId) }
      catch (e) { this.error = e.message; this.treeData = [] }
      finally { this.loading = false }
    },
    async loadList(projectId) {
      this.loading = true; this.error = null
      try { const data = await testSuiteGroupApi.list(projectId); this.flatList = data.results || data }
      catch (e) { this.error = e.message; this.flatList = [] }
      finally { this.loading = false }
    },
    async create(data) { await testSuiteGroupApi.create(data); if (data.project) await this.loadList(data.project) },
    async update(id, data) { await testSuiteGroupApi.update(id, data); if (data.project) await this.loadList(data.project) },
    async remove(id, projectId) { await testSuiteGroupApi.remove(id); await this.loadList(projectId) },
  }
})
