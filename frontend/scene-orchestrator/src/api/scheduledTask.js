/**
 * 定时任务 API（与后端 Drf ScheduledTaskViewSet 对齐）
 */
import { http } from "./http";

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

/** 定时任务 CRUD */
export const scheduledTaskApi = {
  list: (params = {}) => {
    const q = buildQuery(params);
    const url = q ? `/api/v1/scheduled-tasks/?${q}` : "/api/v1/scheduled-tasks/";
    return http.get(url);
  },
  get: (id) => http.get(`/api/v1/scheduled-tasks/${id}/`),
  create: (data) => http.post("/api/v1/scheduled-tasks/", data),
  update: (id, data) => http.put(`/api/v1/scheduled-tasks/${id}/`, data),
  remove: (id) => http.delete(`/api/v1/scheduled-tasks/${id}/`),

  /** 切换 active / paused */
  toggleStatus: (id) =>
    http.post(`/api/v1/scheduled-tasks/${id}/toggle_status/`),

  /** 立即执行 */
  runNow: (id) => http.post(`/api/v1/scheduled-tasks/${id}/run_now/`),
};

/** 执行日志（只读） */
export const taskExecutionLogApi = {
  list: (params = {}) => {
    const q = buildQuery(params);
    const url = q ? `/api/v1/task-execution-logs/?${q}` : "/api/v1/task-execution-logs/";
    return http.get(url);
  },
  get: (id) => http.get(`/api/v1/task-execution-logs/${id}/`),
  remove: (id) => http.delete(`/api/v1/task-execution-logs/${id}/`),
};

/** 任务监控 */
export const taskMonitorApi = {
  /** 获取监控状态 */
  status: () => http.get("/api/v1/task-monitor/"),
  /** 同步所有任务到 Celery */
  sync: () => http.post("/api/v1/task-monitor/sync/"),
  /** 清理孤立 Celery 任务 */
  cleanup: () => http.post("/api/v1/task-monitor/cleanup/"),
};
