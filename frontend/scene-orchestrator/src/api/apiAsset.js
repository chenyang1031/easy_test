import { http } from "./http";

/**
 * 获取 API 项目列表（用于回放导入等场景） */
export function fetchApiProjects(params = {}) {
  const query = new URLSearchParams({ page_size: "1000" });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return http.get(`/api/v1/api-projects/?${query.toString()}`);
}

/**
 * 获取 API 分组树（与 API 资产管理分组导航使用相同接口）
 * @param {object} params - 额外参数，如 page_size
 */
export function fetchApiGroups(apiProjectId, params = {}) {
  const query = new URLSearchParams({ project: String(apiProjectId), page_size: "1000" });
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return http.get(`/api/v1/api-groups/?${query.toString()}`);
}

export function fetchApiAssets(apiProjectId, extraParams = {}) {
  const query = new URLSearchParams({
    project: String(apiProjectId),
    page_size: "1000"
  });
  Object.entries(extraParams).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return http.get(`/api/v1/api-assets/?${query.toString()}`);
}

export function fetchApiAssetsLite(apiProjectId) {
  return http.get(`/api/v1/api-assets/lite/?project=${apiProjectId}`);
}

export function fetchApiAssetConfig(apiId) {
  return http.get(`/api/v1/api-assets/${apiId}/config/`);
}
