import { defineStore } from "pinia";
import { scheduledTaskApi, taskExecutionLogApi } from "../../api/scheduledTask";

export const useScheduledTaskStore = defineStore("scheduledTask", {
  state: () => ({
    list: [],
    current: null,
    loading: false,
    error: null,
    total: 0,
    page: 1,
    pageSize: 10,

    /** 执行日志 */
    logs: [],
    logsLoading: false,
    logsTotal: 0,
  }),

  actions: {
    async loadList(params = {}) {
      this.loading = true;
      this.error = null;
      try {
        const p = { page: this.page, page_size: this.pageSize, ...params };
        const data = await scheduledTaskApi.list(p);
        this.list = data.results || data;
        this.total = data.count || 0;
      } catch (e) {
        this.error = e.message;
        this.list = [];
      } finally {
        this.loading = false;
      }
    },

    async loadDetail(id) {
      this.loading = true;
      try {
        this.current = await scheduledTaskApi.get(id);
      } catch (e) {
        this.error = e.message;
        this.current = null;
      } finally {
        this.loading = false;
      }
    },

    async create(data) {
      return await scheduledTaskApi.create(data);
    },

    async update(id, data) {
      return await scheduledTaskApi.update(id, data);
    },

    async remove(id) {
      await scheduledTaskApi.remove(id);
    },

    async toggleStatus(id) {
      return await scheduledTaskApi.toggleStatus(id);
    },

    async runNow(id) {
      return await scheduledTaskApi.runNow(id);
    },

    /** 加载执行日志 */
    async loadLogs(taskId, params = {}) {
      this.logsLoading = true;
      try {
        const p = {
          scheduled_task: taskId,
          page: params.page || 1,
          page_size: params.page_size || 10,
          ...params,
        };
        const data = await taskExecutionLogApi.list(p);
        this.logs = data.results || data;
        this.logsTotal = data.count || 0;
      } catch (e) {
        this.logs = [];
        this.logsTotal = 0;
      } finally {
        this.logsLoading = false;
      }
    },
  },
});
