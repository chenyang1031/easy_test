/**
 * 认证相关 API（与 DRF AuthLoginView / AuthRegisterView 等对齐）
 */
import { http } from './http'

const BASE = '/api/v1/auth'

/**
 * POST /api/v1/auth/login/
 * @param {string} username
 * @param {string} password
 * @returns {Promise<{detail: string, user: object}>}
 */
export function loginApi(username, password) {
  return http.post(`${BASE}/login/`, { username, password })
}

/**
 * POST /api/v1/auth/logout/
 */
export function logoutApi() {
  return http.post(`${BASE}/logout/`)
}

/**
 * GET /api/v1/auth/user/
 * @returns {Promise<{id: number, username: string, email: string, first_name: string, last_name: string}>}
 */
export function fetchCurrentUser() {
  return http.get(`${BASE}/user/`)
}

/**
 * POST /api/v1/auth/register/
 * @param {object} payload - { username, email, password, password2 }
 * @returns {Promise<{detail: string, user: object}>}
 */
export function registerApi(payload) {
  return http.post(`${BASE}/register/`, payload)
}

/**
 * GET /api/v1/auth/profile/  — 获取个人资料
 */
export function fetchProfile() {
  return http.get(`${BASE}/profile/`)
}

/**
 * PUT /api/v1/auth/profile/  — 更新个人资料
 * @param {object} payload - { first_name?, last_name?, email? }
 */
export function updateProfile(payload) {
  return http.put(`${BASE}/profile/`, payload)
}

/**
 * POST /api/v1/auth/password-change/  — 修改密码
 * @param {object} payload - { old_password, new_password, new_password2 }
 */
export function changePassword(payload) {
  return http.post(`${BASE}/password-change/`, payload)
}
