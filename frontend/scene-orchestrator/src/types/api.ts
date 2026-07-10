/**
 * 核心 API 类型定义
 * 对应 Django REST Framework 序列化器输出结构
 */

// === 通用响应类型 ===

export interface ApiListResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiError {
  detail?: string
  error?: string
  [key: string]: any
}

// === 项目 ===

export interface Project {
  id: number
  name: string
  description: string
  created_at: string
  updated_at: string
  created_by: number
}

// === API 项目 ===

export interface ApiProject {
  id: number
  platform_project: number | null
  name: string
  description: string
  created_by: number
  created_at: string
  updated_at: string
}

// === API 分组 ===

export interface ApiGroup {
  id: number
  project: number
  parent: number | null
  name: string
  sort_order: number
  created_at: string
  updated_at: string
}

// === API 资产 ===

export interface ApiAsset {
  id: number
  project: number
  group: number | null
  name: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  url: string
  interface_desc: string
  request_headers: Record<string, string>
  request_params: ApiParam[]
  request_body_format: 'json' | 'form-data'
  request_body: any
  response_schema: any
  error_code: any[]
  auth_config: Record<string, any>
  status: 'draft' | 'active' | 'deprecated'
  source: 'manual' | 'postman' | 'apifox' | 'openapi' | 'goreplay' | 'ai_document'
  external_id: string
  required: boolean
  param_type: string
  sort: number
  param_status: 'enabled' | 'disabled'
  is_deleted: boolean
  created_by: number
  created_at: string
  updated_at: string
}

export interface ApiParam {
  key: string
  type: string
  value: string
  required?: boolean
  default?: string
  desc?: string
  validation?: string
}

// === 环境 ===

export interface Environment {
  id: number
  project: number
  name: string
  base_url: string
  variables: Record<string, string>
  headers: Record<string, string>
  pre_script: string
  category: string
  created_at: string
  updated_at: string
}

// === 测试场景 ===

export interface TestScene {
  id: number
  project: number
  name: string
  description: string
  variables: Record<string, any>
  runtime_config: Record<string, any>
  is_active: boolean
  is_deleted: boolean
  created_by: number
  created_at: string
  updated_at: string
}

export interface TestSceneNode {
  id: number
  scene: number
  api_asset: number | null
  node_key: string
  name: string
  description: string
  request_headers: Record<string, string>
  request_params: Record<string, string>
  request_body: Record<string, any>
  param_type: 'json' | 'form-data'
  body_type: 'json' | 'form-data'
  assert_rules: AssertRule[]
  [key: string]: any
}

export interface AssertRule {
  source: 'status_code' | 'response_time' | 'header' | 'json'
  path?: string
  operator: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'regex'
  expected: any
}

// === 测试用例 ===

export interface TestCase {
  id: number
  project: number
  name: string
  request_method: string
  request_url: string
  request_headers: Record<string, string>
  request_params: Record<string, string>
  request_body: any
  request_body_type: string
  validation: any
  extract: any
  created_at: string
  updated_at: string
}

// === 测试套件 ===

export interface TestSuite {
  id: number
  project: number
  name: string
  description: string
  test_cases: number[]
  created_at: string
  updated_at: string
}

// === AI 相关 ===

export interface AIModelProvider {
  id: number
  name: string
  base_url: string
  api_path: string
  api_key: string
  model_name: string
  is_enabled: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface PromptTemplate {
  id: number
  name: string
  content: string
  is_enabled: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface AICaseDraft {
  id: number
  draft_group: number
  method: string
  url: string
  request_headers: Record<string, string>
  request_params: any[]
  request_body: any
  description: string
  created_at: string
}

// === 性能测试 ===

export interface PerformanceTestTask {
  id: number
  name: string
  project: number
  environment: number
  interface: number
  total_users: number
  spawn_rate: number
  run_time: number
  status: 'draft' | 'running' | 'stopped' | 'completed' | 'failed'
  created_at: string
  executed_at: string | null
  finished_at: string | null
}

// === Mock 数据 ===

export interface MockData {
  id: number
  project: number
  name: string
  method: string
  url: string
  response_status: number
  response_headers: Record<string, string>
  response_body: any
  is_active: boolean
  created_at: string
  updated_at: string
}
