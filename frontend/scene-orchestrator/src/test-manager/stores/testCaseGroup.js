import { defineStore } from 'pinia'
import { testCaseGroupApi } from '../api/index.js'

export const useTestCaseGroupStore = defineStore('testCaseGroup', {
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
      try {
        this.treeData = await testCaseGroupApi.tree(projectId)
      } catch (e) { this.error = e.message; this.treeData = [] }
      finally { this.loading = false }
    },
    async loadList(projectId) {
      this.loading = true; this.error = null
      try {
        const data = await testCaseGroupApi.list(projectId)
        this.flatList = data.results || data
      } catch (e) { this.error = e.message; this.flatList = [] }
      finally { this.loading = false }
    },
    async create(data) { await testCaseGroupApi.create(data); if (data.project) await this.loadList(data.project) },
    async update(id, data) { await testCaseGroupApi.update(id, data); if (data.project) await this.loadList(data.project) },
    async remove(id, projectId) { await testCaseGroupApi.remove(id); await this.loadList(projectId) },
  }
})
