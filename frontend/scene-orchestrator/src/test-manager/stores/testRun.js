import { defineStore } from 'pinia'
import { testRunApi, testResultApi } from '../api/index.js'

export const useTestRunStore = defineStore('testRun', {
  state: () => ({
    // 列表
    list: [],
    loading: false,
    total: 0,
    page: 1,
    pageSize: 10,
    filterProject: '',
    // 详情
    current: null,
    detailLoading: false,
    // 统计
    stats: { total: 0, passed: 0, failed: 0, error: 0, skipped: 0 },
    statsLoading: false,
    // 测试结果（分页）
    results: [],
    resultsLoading: false,
    resultsTotal: 0,
    resultsPage: 1,
    resultsPageSize: 10,
    resultsStatusFilter: '',
    // 结果详情弹窗
    detailResult: null,
    detailResultVisible: false,
  }),

  getters: {
    statsPercent: (state) => {
      const t = state.stats.total || 1
      return {
        passed: (state.stats.passed / t * 100).toFixed(1),
        failed: (state.stats.failed / t * 100).toFixed(1),
        error: (state.stats.error / t * 100).toFixed(1),
        skipped: (state.stats.skipped / t * 100).toFixed(1),
      }
    },
  },

  actions: {
    async loadList(params = {}) {
      this.loading = true
      try {
        const p = { page: this.page, page_size: this.pageSize, ...params }
        if (this.filterProject) p.project = this.filterProject
        const data = await testRunApi.list(p)
        this.list = data.results || data
        this.total = data.count || 0
      } catch (e) {
        this.list = []
        this.total = 0
        throw e
      } finally {
        this.loading = false
      }
    },

    async loadDetail(id) {
      this.detailLoading = true
      try {
        this.current = await testRunApi.get(id)
      } catch (e) {
        // 不抛出异常，避免 Promise.all 中断导致页面显示空状态；
        // 组件内通过 ElMessage 展示错误
        this.current = null
        console.error('加载测试运行详情失败:', e)
      } finally {
        this.detailLoading = false
      }
    },

    async loadStats(id) {
      this.statsLoading = true
      try {
        this.stats = await testRunApi.stats(id)
      } catch (e) {
        this.stats = { total: 0, passed: 0, failed: 0, error: 0, skipped: 0 }
      } finally {
        this.statsLoading = false
      }
    },

    async loadResults(id) {
      this.resultsLoading = true
      try {
        const p = { page: this.resultsPage, page_size: this.resultsPageSize }
        if (this.resultsStatusFilter) p.status = this.resultsStatusFilter
        const data = await testRunApi.results(id, p)
        this.results = data.results || data
        this.resultsTotal = data.count || 0
      } catch (e) {
        this.results = []
        this.resultsTotal = 0
      } finally {
        this.resultsLoading = false
      }
    },

    async remove(id) {
      await testRunApi.remove(id)
    },

    async fetchResultDetail(id) {
      return await testResultApi.get(id)
    },

    openResultDetail(result) {
      this.detailResult = result
      this.detailResultVisible = true
    },

    closeResultDetail() {
      this.detailResultVisible = false
      this.detailResult = null
    },
  },
})
