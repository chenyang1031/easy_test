/**
 * 测试报告 API（与后端 DRF TestReportViewSet 对齐）
 */
import { http } from "./http";

const BASE = "/api/v1/reports";

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

export function fetchReports(params = {}) {
  const q = buildQuery(params);
  const url = q ? `${BASE}/?${q}` : `${BASE}/`;
  return http.get(url);
}

export function fetchReportDetail(reportId) {
  return http.get(`${BASE}/${reportId}/`);
}

export function createReport(payload) {
  return http.post(`${BASE}/`, payload);
}

export function updateReport(reportId, payload) {
  return http.put(`${BASE}/${reportId}/`, payload);
}

export function deleteReport(reportId) {
  return http.delete(`${BASE}/${reportId}/`);
}

/** 场景执行报告生成 */
export function generateSceneReport(executionId, payload) {
  return http.post(`/api/v1/scene-executions/${executionId}/generate-report/`, payload);
}

/** 测试运行报告生成 */
export function generateTestRunReport(testRunId, payload) {
  return http.post(`/api/v1/test-runs/${testRunId}/generate-report/`, payload);
}
