/**
 * 性能测试 API（与后端 DRF PerformanceTestTaskViewSet 字段对齐）
 */
import { http } from "./http";

const BASE = "/api/v1/performance/tasks";

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

export function fetchPerformanceTasks(params = {}) {
  const q = buildQuery(params);
  const url = q ? `${BASE}/?${q}` : `${BASE}/`;
  return http.get(url);
}

export function fetchPerformanceTaskDetail(taskId) {
  return http.get(`${BASE}/${taskId}/`);
}

/**
 * 构建 FormData：含文件上传及 extra_config 等 JSON 字符串提交 */
function buildTaskFormData(payload, csvFile) {
  const form = new FormData();
  const keys = ["name", "project", "environment", "interface", "total_users", "spawn_rate", "run_time", "target_rps"];
  keys.forEach((k) => {
    if (k === "target_rps") {
      const v = payload.target_rps;
      if (v !== undefined && v !== null && v !== "") {
        form.append(k, String(v));
      } else {
        form.append(k, "");
      }
      return;
    }
    if (payload[k] !== undefined && payload[k] !== null && payload[k] !== "") {
      form.append(k, String(payload[k]));
    }
  });
  if (payload.extra_config !== undefined && payload.extra_config !== null) {
    const ec =
      typeof payload.extra_config === "string" ? payload.extra_config : JSON.stringify(payload.extra_config);
    form.append("extra_config", ec);
  }
  if (csvFile instanceof File) {
    form.append("csv_file", csvFile);
  }
  return form;
}

export function createPerformanceTask(payload, csvFile) {
  if (csvFile instanceof File) {
    return http.post(`${BASE}/`, buildTaskFormData(payload, csvFile));
  }
  return http.post(`${BASE}/`, payload);
}

export function updatePerformanceTask(taskId, payload, csvFile) {
  if (csvFile instanceof File) {
    return http.put(`${BASE}/${taskId}/`, buildTaskFormData(payload, csvFile));
  }
  return http.put(`${BASE}/${taskId}/`, payload);
}

export function deletePerformanceTask(taskId) {
  return http.delete(`${BASE}/${taskId}/`);
}

export function startPerformanceTest(taskId) {
  return http.post(`${BASE}/${taskId}/start/`, {});
}

/** 手动停止压测（与后端 PerformanceTestTaskViewSet.stop_test 对齐：POST .../stop/） */
export function stopPerformanceTest(taskId, payload = {}) {
  return http.post(`${BASE}/${taskId}/stop/`, payload);
}

export function fetchPerformanceResults(taskId, params = {}) {
  const q = buildQuery(params);
  const suffix = q ? `?${q}` : "";
  return http.get(`${BASE}/${taskId}/results/${suffix}`);
}

/** 实时监控：拉取足够多的采样点 */
export function fetchPerformanceResultsAll(taskId) {
  return http.get(`${BASE}/${taskId}/results/?page_size=2000`);
}

export function fetchPerformanceReport(taskId) {
  return http.get(`${BASE}/${taskId}/report/`);
}

/** 执行中卡顿/无采样排查信息 */
export function fetchPerformanceDiagnostics(taskId) {
  return http.get(`${BASE}/${taskId}/diagnostics/`);
}

// ==================== 批量执行 API ====================

const BATCH_BASE = "/api/v1/performance/batch";

export function fetchBatchTasks(params = {}) {
  const q = buildQuery(params);
  const url = q ? `${BATCH_BASE}/?${q}` : `${BATCH_BASE}/`;
  return http.get(url);
}

export function fetchBatchDetail(batchId) {
  return http.get(`${BATCH_BASE}/${batchId}/`);
}

export function createBatchTask(payload) {
  return http.post(`${BATCH_BASE}/`, payload);
}

export function updateBatchTask(batchId, payload) {
  return http.put(`${BATCH_BASE}/${batchId}/`, payload);
}

export function deleteBatchTask(batchId) {
  return http.delete(`${BATCH_BASE}/${batchId}/`);
}

export function startBatch(batchId) {
  return http.post(`${BATCH_BASE}/${batchId}/start/`, {});
}

export function stopBatch(batchId) {
  return http.post(`${BATCH_BASE}/${batchId}/stop/`, {});
}

export function fetchBatchItems(batchId, params = {}) {
  const q = buildQuery(params);
  const url = q ? `${BATCH_BASE}/${batchId}/items/?${q}` : `${BATCH_BASE}/${batchId}/items/`;
  return http.get(url);
}

export function fetchBatchReport(batchId) {
  return http.get(`${BATCH_BASE}/${batchId}/report/`);
}
