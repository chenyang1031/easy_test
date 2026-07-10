/**
 * 邮件配置 API
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

export const emailConfigApi = {
  list: (params = {}) => {
    const q = buildQuery(params);
    const url = q ? `/api/v1/email-config/?${q}` : "/api/v1/email-config/";
    return http.get(url);
  },
  get: (id) => http.get(`/api/v1/email-config/${id}/`),
  create: (data) => http.post("/api/v1/email-config/", data),
  update: (id, data) => http.put(`/api/v1/email-config/${id}/`, data),
  remove: (id) => http.delete(`/api/v1/email-config/${id}/`),

  /** 发送测试邮件 */
  testEmail: (id, email) =>
    http.post(`/api/v1/email-config/${id}/test_email/`, { email }),

  /** 测试连接 */
  testConnection: (id) =>
    http.post(`/api/v1/email-config/${id}/test_connection/`),

  /** 激活配置 */
  activate: (id) =>
    http.post(`/api/v1/email-config/${id}/activate/`),
};
