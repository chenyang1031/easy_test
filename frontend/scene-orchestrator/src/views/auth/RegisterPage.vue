<template>
  <div class="register-page">
    <!-- 标题 -->
    <div class="auth-header">
      <h2 class="auth-title">创建账户</h2>
      <p class="auth-subtitle">注册一个新账户开始使用</p>
    </div>

    <!-- 错误提示 -->
    <transition name="el-fade-in-linear">
      <div v-if="errorMsg" class="error-banner">
        <el-icon class="error-icon"><WarningFilled /></el-icon>
        <span>{{ errorMsg }}</span>
      </div>
    </transition>

    <!-- 注册表单 -->
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      size="large"
      @submit.prevent="handleRegister"
      class="register-form"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          placeholder="请设置用户名"
          :prefix-icon="User"
          autocomplete="username"
          clearable
        />
      </el-form-item>

      <el-form-item label="电子邮箱" prop="email">
        <el-input
          v-model="form.email"
          placeholder="请输入邮箱地址"
          :prefix-icon="Message"
          autocomplete="email"
          clearable
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          placeholder="请设置密码（至少8位）"
          :prefix-icon="Lock"
          show-password
          autocomplete="new-password"
        />
      </el-form-item>

      <el-form-item label="确认密码" prop="password2">
        <el-input
          v-model="form.password2"
          type="password"
          placeholder="请再次输入密码"
          :prefix-icon="Lock"
          show-password
          autocomplete="new-password"
        />
      </el-form-item>

      <!-- 提交按钮 -->
      <el-form-item class="submit-item">
        <el-button
          type="primary"
          class="submit-btn"
          :loading="loading"
          native-type="submit"
        >
          {{ loading ? '注册中...' : '创建账户' }}
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 登录链接 -->
    <div class="auth-footer-links">
      <span class="footer-text">已有账户?</span>
      <router-link to="/login" class="login-link">立即登录</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message, WarningFilled } from '@element-plus/icons-vue'
import { registerApi, fetchCurrentUser } from '../../api/auth'
import { msgSuccess } from '../../utils/uiMessage.js'

const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const fieldErrors = ref({})

const form = reactive({
  username: '',
  email: '',
  password: '',
  password2: '',
})

/** 将后端校验错误映射到表单字段 */
function mapServerErrors(errors) {
  fieldErrors.value = {}
  const fieldMap = {
    username: 'username',
    email: 'email',
    password: 'password',
    password2: 'password2',
  }

  const messages = []
  for (const [key, value] of Object.entries(errors)) {
    const msg = Array.isArray(value) ? value[0] : value
    if (fieldMap[key]) {
      fieldErrors.value[fieldMap[key]] = msg
    }
    messages.push(msg)
  }

  // 优先显示字段错误，其次是通用错误
  if (messages.length > 0) {
    errorMsg.value = messages.join('；')
  }
}

/** 自定义校验：两次密码一致 */
const validatePassword2 = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请设置用户名', trigger: 'blur' },
    { min: 2, max: 150, message: '用户名长度为 2-150 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 8, message: '密码长度不能少于 8 个字符', trigger: 'blur' },
  ],
  password2: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validatePassword2, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMsg.value = ''
  fieldErrors.value = {}

  try {
    await registerApi({
      username: form.username,
      email: form.email,
      password: form.password,
      password2: form.password2,
    })

    // 注册成功后刷新全局用户状态
    try {
      const user = await fetchCurrentUser()
      window.__APP_STATE__ = window.__APP_STATE__ || {}
      window.__APP_STATE__.userAuthenticated = true
      window.__APP_STATE__.userName = user.username
    } catch {
      // 即使获取用户信息失败也不影响
    }

    msgSuccess('账户创建成功！')
    router.push('/dashboard')
  } catch (e) {
    // 尝试解析后端返回的字段错误
    try {
      const errData = e.message ? JSON.parse(e.message.replace(/.*?: /, '')) : {}
      if (typeof errData === 'object') {
        mapServerErrors(errData)
      } else {
        errorMsg.value = e?.message || '注册失败，请重试'
      }
    } catch {
      errorMsg.value = e?.message || '注册失败，请重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ============ 页面容器 ============ */
.register-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ============ 标题 ============ */
.auth-header {
  text-align: center;
  margin-bottom: 4px;
}

.auth-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 8px;
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
  padding: 12px 16px;
  background: #FEF2F2;
  border: 1px solid #FECACA;
  border-radius: 8px;
  color: #DC2626;
  font-size: 0.875rem;
  line-height: 1.4;
}

.error-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

/* ============ 表单 ============ */
.register-form {
  width: 100%;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.register-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #374151;
  padding-bottom: 6px;
}

.register-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #E2E8F0 inset;
  transition: box-shadow 0.2s;
}

.register-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #CBD5E1 inset;
}

.register-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--primary-color, #1E40AF) inset;
}

.register-form :deep(.el-input__inner) {
  height: 44px;
}

.register-form :deep(.el-input__prefix) {
  color: #94A3B8;
}

/* ============ 提交按钮 ============ */
.submit-item {
  margin-bottom: 0 !important;
  margin-top: 4px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* ============ 底部链接 ============ */
.auth-footer-links {
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid #F1F5F9;
}

.footer-text {
  font-size: 0.875rem;
  color: #94A3B8;
  margin-right: 4px;
}

.login-link {
  font-size: 0.875rem;
  color: var(--primary-color, #1E40AF);
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.login-link:hover {
  color: var(--secondary-color, #3B82F6);
  text-decoration: underline;
}
</style>
