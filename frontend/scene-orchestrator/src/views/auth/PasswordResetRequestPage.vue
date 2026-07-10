<template>
  <div class="password-reset-page">
    <div class="auth-header">
      <h2 class="auth-title">重置密码</h2>
      <p class="auth-subtitle">此功能正在开发中，请暂使用旧的密码重置页面</p>
    </div>
    <div class="notice-card">
      <el-result icon="info" title="功能开发中" sub-title="密码重置的 Vue 页面将在下一阶段完成">
        <template #extra>
          <a href="/password-reset/" class="el-button el-button--primary">
            前往旧版重置页面
          </a>
          <router-link to="/login" class="el-button el-button--default">
            返回登录
          </router-link>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup>
// PasswordResetRequestPage — Phase 2 实现
</script>

<style scoped>
.password-reset-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.auth-header {
  text-align: center;
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
.notice-card {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px;
}
</style>
