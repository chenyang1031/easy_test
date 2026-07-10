import { defineStore } from 'pinia'
import { projectApi } from '../api/index.js'

export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [],
    currentProjectId: null,
  }),
  getters: {
    currentProject: (state) => state.projects.find(p => p.id === state.currentProjectId) || null,
  },
  actions: {
    async loadProjects() {
      try {
        const data = await projectApi.list()
        this.projects = data.results || data
      } catch (e) { /* ignore */ }
    },
    setProject(id) {
      this.currentProjectId = id || null
    },
  }
})
