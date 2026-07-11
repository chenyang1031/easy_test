import { http } from "./http";

export function fetchProjects() {
  return http.get("/api/v1/projects/?page_size=1000");
}

export function resolveApiProjectId(platformProjectId) {
  return http.post("/api/v1/api-projects/resolve-platform-project/", {
    platform_project_id: platformProjectId
  });
}

export function fetchScenes(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return http.get(`/api/v1/test-scenes/?${query.toString()}`);
}

export function fetchSceneDetail(sceneId) {
  return http.get(`/api/v1/test-scenes/${sceneId}/`);
}

export function fetchSceneDesignerInit(sceneId) {
  if (!sceneId) {
    throw new Error("sceneId不能为空");
  }
  return http.get(`/api/v1/test-scenes/${sceneId}/designer-init/`);
}

export function createScene(payload) {
  return http.post("/api/v1/test-scenes/", payload);
}

export function updateScene(sceneId, payload) {
  return http.put(`/api/v1/test-scenes/${sceneId}/`, payload);
}

export function deleteScene(sceneId) {
  return http.delete(`/api/v1/test-scenes/${sceneId}/`);
}

export function copyScene(sceneId, name) {
  return http.post(`/api/v1/test-scenes/${sceneId}/copy/`, { name });
}

/**
 * 执行场景。场景执行可能包含文件上传等长耗时操作，使用 5 分钟超时以覆盖节点配置的超时时间。
 */
export function executeScene(sceneId, payload) {
  const EXECUTE_TIMEOUT_MS = 5 * 60 * 1000; // 5 分钟
  return http.post(`/api/v1/test-scenes/${sceneId}/execute/`, payload, {
    timeoutMs: EXECUTE_TIMEOUT_MS
  });
}

/**
 * 客户端请求超时时，通知后端将场景下仍在 running 的执行标记为失败，避免状态一直显示「执行中」。
 */
export function markSceneExecutionTimeout(sceneId) {
  return http.post(`/api/v1/test-scenes/${sceneId}/mark-execution-timeout/`, {});
}

export function fetchSceneExecutions(sceneId, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  const qs = query.toString();
  const url = qs ? `/api/v1/test-scenes/${sceneId}/executions/?${qs}` : `/api/v1/test-scenes/${sceneId}/executions/`;
  return http.get(url);
}

export function fetchEnvironments(projectId) {
  if (!projectId) return Promise.resolve([]);
  return http.get(`/api/v1/environments/?project=${projectId}&page_size=200`);
}

export function fetchSceneNodes(sceneId) {
  return http.get(`/api/v1/test-scene-nodes/?scene_id=${sceneId}`);
}

export function getApiDetail(apiId) {
  const parsedId = Number(apiId);
  if (!parsedId) {
    throw new Error("apiId不能为空");
  }
  return http.get(`/api/v1/api-assets/${parsedId}/config/`);
}

export function createSceneNode(payload) {
  const sceneId = payload?.scene || payload?.scene_id || payload?.sceneId;
  const apiId = payload?.api_asset || payload?.api || payload?.apiId;
  if (!sceneId) {
    throw new Error("创建节点失败：scene不能为空");
  }
  if (!apiId) {
    throw new Error("创建节点失败：api不能为空");
  }
  // 允许最小入参，后端自动补齐配置；保留兼容字段
  return http.post("/api/v1/test-scene-nodes/", {
    ...payload,
    scene: sceneId,
    api_asset: apiId
  });
}

export function updateSceneNode(nodeId, payload, options = {}) {
  return http.put(`/api/v1/test-scene-nodes/${nodeId}/`, payload, { timeoutMs: 10000, ...options });
}

export function deleteSceneNode(nodeId) {
  return http.delete(`/api/v1/test-scene-nodes/${nodeId}/`);
}

export function reorderSceneNodes(sceneId, orderedNodeIds) {
  return http.post("/api/v1/test-scene-nodes/reorder/", {
    scene_id: sceneId,
    ordered_node_ids: orderedNodeIds
  });
}

export function copySceneNode(nodeId) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/copy/`, {});
}

/** 获取节点与关联 API 资产的差异 */
export function fetchNodeApiDiff(nodeId) {
  return http.get(`/api/v1/test-scene-nodes/${nodeId}/api-diff/`);
}

/** 一键同步 URL/Method 到节点 */
export function syncNodeBasic(nodeId) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/sync-basic/`, {});
}

/** 从 API 新增的参数以空值追加到节点 */
export function syncNodeAddParams(nodeId, { param_keys, scope = "request_params" }) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/sync-add-params/`, { param_keys, scope });
}

/** 完整同步请求头到节点（覆盖节点现有请求头） */
export function syncNodeHeaders(nodeId) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/sync-headers/`, {});
}

/** 完整同步请求参数到节点（覆盖节点现有参数，可处理新增/删除） */
export function syncNodeParams(nodeId) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/sync-params/`, {});
}

/** 回滚节点配置到指定同步前 */
export function syncNodeRollback(nodeId, syncLogId) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/sync-rollback/`, { sync_log_id: syncLogId });
}

/** 一键同步场景所有节点（基础信息 + 参数 + 请求头） */
export function syncAllSceneNodes(sceneId) {
  return http.post(`/api/v1/test-scenes/${sceneId}/sync-all-nodes/`, {});
}

/** 测试场景节点的前置脚本（子进程隔离执行） */
export function testSceneNodeScript(nodeId, payload) {
  return http.post(`/api/v1/test-scene-nodes/${nodeId}/test-pre-request-script/`, payload, { timeoutMs: 20000 });
}
export function fetchSceneVariableFields(sceneId, currentNodeId = null, environmentId = null) {
  const base = `/api/v1/test-scenes/${sceneId}/variable-fields-preview/`;
  const params = new URLSearchParams();
  if (currentNodeId) params.set("current_node_id", currentNodeId);
  if (environmentId) params.set("environment_id", environmentId);
  const query = params.toString();
  const url = query ? `${base}?${query}` : base;
  return http.get(url);
}

/**
 * 上传文件，用于节点参数请求体中的 file 类型。
 * 复用 API 资产上传接口，返回 file_path、file_name、file_url。
 */
export function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  return http.post("/api/v1/api-assets/upload/", formData);
}

/**
 * 回放导入 - 预览（GoReplay .gor/.gor.gz 或 Fiddler HAR .har）
 * @param {File} file - 回放文件
 * @param {number} projectId - 目标 API 项目 ID
 * @param {number|null} groupId - 可选，未匹配接口的目标分组
 */
export function replayImportPreview(file, projectId, groupId = null) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("project_id", String(projectId));
  if (groupId) formData.append("group_id", String(groupId));
  return http.post("/api/v1/test-scenes/replay-import/preview", formData, { timeoutMs: 60000 });
}

/**
 * 回放导入 - 确认导入
 */
export function replayImportConfirm(payload) {
  return http.post("/api/v1/test-scenes/replay-import/confirm", payload, { timeoutMs: 60000 });
}

/**
 * 场景编排导出
 * @param {number} projectId - API 项目 ID
 * @param {number[]} [sceneIds] - 可选，指定导出的场景 ID 列表
 * @param {string} [format] - 导出格式：json 或 yaml
 */
export function exportScenes(projectId, sceneIds = null, format = "json") {
  return http.post("/api/v1/test-scenes/export-scenes/", {
    project_id: projectId,
    scene_ids: sceneIds,
    format,
  });
}

/**
 * 场景编排导入 - 预览
 * @param {File} file - 导出的 JSON/YAML 文件
 * @param {number} projectId - 目标平台项目 ID
 */
export function sceneImportPreview(file, projectId) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("project_id", String(projectId));
  return http.post("/api/v1/test-scenes/import-scenes/preview", formData, { timeoutMs: 60000 });
}

/**
 * 场景编排导入 - 确认
 * @param {object} payload - { project_id, data, default_conflict_strategy }
 */
export function sceneImportConfirm(payload) {
  return http.post("/api/v1/test-scenes/import-scenes/confirm", payload, { timeoutMs: 60000 });
}
