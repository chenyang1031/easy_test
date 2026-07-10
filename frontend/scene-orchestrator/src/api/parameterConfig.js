/**
 * 参数配置 API
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

export const parameterConfigApi = {
  list: (params = {}) => {
    const q = buildQuery(params);
    const url = q ? `/api/v1/parameter-config/?${q}` : "/api/v1/parameter-config/";
    return http.get(url);
  },
  get: (id) => http.get(`/api/v1/parameter-config/${id}/`),
  update: (id, data) => http.patch(`/api/v1/parameter-config/${id}/`, data),

  /** 测试 AI 接口 */
  testAi: () => http.post("/api/v1/parameter-config/test_ai/"),
};
