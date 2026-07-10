<template>
  <div class="login-page">
    <!-- 标题 -->
    <div class="auth-header">
      <span class="auth-badge">SECURE LOGIN</span>
      <h2 class="auth-title">欢迎回来</h2>
      <p class="auth-subtitle">登录您的账户以继续</p>
    </div>

    <!-- 错误提示 -->
    <transition name="el-fade-in-linear">
      <div v-if="errorMsg" class="error-banner">
        <div class="error-accent"></div>
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <span>{{ errorMsg }}</span>
        <button class="error-close" @click="errorMsg = ''">&times;</button>
      </div>
    </transition>

    <!-- 登录表单 -->
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      size="large"
      @submit.prevent="handleLogin"
      class="login-form"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          placeholder="请输入用户名"
          :prefix-icon="User"
          autocomplete="username"
          clearable
          @keyup.enter="handleLogin"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          placeholder="请输入密码"
          :prefix-icon="Lock"
          show-password
          autocomplete="current-password"
          @keyup.enter="handleLogin"
        />
      </el-form-item>

      <!-- 记住我 & 忘记密码 -->
      <div class="form-options">
        <el-checkbox v-model="form.remember" class="tech-checkbox">记住我</el-checkbox>
        <router-link to="/password-reset" class="forgot-link">
          <span class="link-dot"></span>
          忘记密码?
        </router-link>
      </div>

      <!-- 提交按钮 -->
      <el-form-item class="submit-item">
        <div class="btn-container">
          <el-button
            type="primary"
            class="submit-btn"
            :loading="loading"
            native-type="submit"
          >
            <span class="btn-text">{{ loading ? '登录中...' : '登 录' }}</span>
            <span v-if="!loading" class="btn-arrow">&rarr;</span>
          </el-button>
          <div class="btn-glow"></div>
        </div>
      </el-form-item>
    </el-form>

    <!-- 分隔线 -->
    <div class="auth-divider"></div>

    <!-- 注册链接 -->
    <div class="auth-footer-links">
      <span class="footer-text">还没有账户?</span>
      <router-link to="/register" class="register-link">
        立即注册
        <span class="link-arrow">&rarr;</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock, WarningFilled } from '@element-plus/icons-vue'
import { loginApi, fetchCurrentUser } from '../../api/auth'
import { msgSuccess } from '../../utils/uiMessage.js'

const router = useRouter()
const route = useRoute()

const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: '',
  remember: false,
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''

  try {
    await loginApi(form.username, form.password)

    try {
      const user = await fetchCurrentUser()
      window.__APP_STATE__ = window.__APP_STATE__ || {}
      window.__APP_STATE__.userAuthenticated = true
      window.__APP_STATE__.userName = user.username
    } catch {
      // 即使获取用户信息失败也不影响登录流程
    }

    msgSuccess('登录成功')

    const redirectPath = route.query.redirect || route.query.next || '/dashboard'
    router.push(redirectPath)
  } catch (e) {
    errorMsg.value = e?.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ============ 页面容器 ============ */
.login-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ============ 标题 ============ */
.auth-header {
  text-align: center;
  margin-bottom: 2px;
}

.auth-badge {
  display: inline-block;
  font-size: 0.6rem;
  font-family: 'Fira Code', Consolas, monospace;
  letter-spacing: 3px;
  color: rgba(59, 130, 246, 0.55);
  background: rgba(59, 130, 246, 0.06);
  padding: 3px 12px;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.08);
  margin-bottom: 14px;
  text-transform: uppercase;
}

.auth-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 6px;
  letter-spacing: -0.3px;
}

.auth-subtitle {
  font-size: 0.9rem;
  color: #94A3B8;
  margin: 0;
}

/* ============ 错误提示 ============ */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: 8px;
  color: #DC2626;
  font-size: 0.85rem;
  line-height: 1.4;
  position: relative;
  overflow: hidden;
}

.error-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #DC2626;
  border-radius: 0 2px 2px 0;
}

.error-icon {
  font-size: 1rem;
  flex-shrink: 0;
  color: #DC2626;
}

.error-close {
  margin-left: auto;
  background: none;
  border: none;
  color: #94A3B8;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}
.error-close:hover { color: #475569; }

/* ============ 表单 ============ */
.login-form {
  width: 100%;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #374151;
  padding-bottom: 6px;
  font-size: 0.85rem;
}

.login-form :deep(.el-form-item__label::before) {
  color: #EF4444 !important;
  margin-right: 3px;
}

/* ============ 输入框 ============ */
.login-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #E2E8F0 inset;
  transition: box-shadow 0.25s ease, border-color 0.25s ease;
  background: #fff;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #CBD5E1 inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 2px rgba(59, 130, 246, 0.25) inset,
    0 0 0 3px rgba(59, 130, 246, 0.06);
  border-color: transparent;
}

.login-form :deep(.el-input__inner) {
  height: 42px;
  color: #1E293B;
  caret-color: #3B82F6;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #94A3B8;
}

.login-form :deep(.el-input__prefix) {
  color: #94A3B8;
  transition: color 0.25s;
}

.login-form :deep(.el-input__wrapper.is-focus .el-input__prefix) {
  color: #3B82F6;
}

.login-form :deep(.el-input__clear) {
  color: #94A3B8;
}
.login-form :deep(.el-input__clear:hover) {
  color: #475569;
}

/* 密码可见切换 */
.login-form :deep(.el-input__suffix-inner .el-input__password) {
  color: #94A3B8;
}

/* ============ 选项行 ============ */
.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.tech-checkbox {
  --el-checkbox-text-color: #64748B;
  --el-checkbox-checked-text-color: #475569;
}
.tech-checkbox :deep(.el-checkbox__label) {
  font-size: 0.85rem;
}
.tech-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #3B82F6;
  border-color: #3B82F6;
}

.forgot-link {
  font-size: 0.85rem;
  color: #94A3B8;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: color 0.2s;
}

.link-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #CBD5E1;
  transition: background 0.2s;
}

.forgot-link:hover {
  color: #3B82F6;
}
.forgot-link:hover .link-dot {
  background: #3B82F6;
}

/* ============ 提交按钮 ============ */
.submit-item {
  margin-bottom: 0 !important;
}

.btn-container {
  position: relative;
  width: 100%;
}

.btn-glow {
  position: absolute;
  inset: -3px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(139, 92, 246, 0.20));
  filter: blur(12px);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.btn-container:hover .btn-glow {
  opacity: 1;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 1px;
  border: none !important;
  background: linear-gradient(135deg, #3B82F6 0%, #6366F1 50%, #8B5CF6 100%) !important;
  background-size: 200% 200% !important;
  animation: btnGradientShift 4s ease infinite;
  position: relative;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.3s ease !important;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.30) !important;
}

.submit-btn:active {
  transform: translateY(0);
}

@keyframes btnGradientShift {
  0%, 100% { background-position: 0% 50%; }
  50%      { background-position: 100% 50%; }
}

.submit-btn :deep(.el-loading-mask) {
  background: transparent;
}

.submit-btn :deep(.el-loading-spinner .circular) {
  color: rgba(255,255,255,0.8);
}

.btn-text {
  display: inline-block;
}

.btn-arrow {
  display: inline-block;
  margin-left: 6px;
  font-size: 1.15rem;
  transition: transform 0.25s ease;
}

.submit-btn:hover .btn-arrow {
  transform: translateX(4px);
}

/* ============ 分隔线 ============ */
.auth-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #E2E8F0, transparent);
}

/* ============ 底部链接 ============ */
.auth-footer-links {
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.footer-text {
  font-size: 0.85rem;
  color: #94A3B8;
}

.register-link {
  font-size: 0.85rem;
  color: #3B82F6;
  text-decoration: none;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: color 0.2s, gap 0.2s;
}

.link-arrow {
  font-size: 1rem;
  transition: transform 0.2s;
}

.register-link:hover {
  color: #2563EB;
  gap: 6px;
}
.register-link:hover .link-arrow {
  transform: translateX(3px);
}
</style>
