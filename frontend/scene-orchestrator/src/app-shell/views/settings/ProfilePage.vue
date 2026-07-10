<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">个人资料</h2>
      </div>
    </div>

    <div class="panel-card">
      <div class="card-header-row">
        <el-icon><UserFilled /></el-icon>
        <span>基本信息</span>
      </div>
      <el-form label-position="top" class="profile-form" @submit.prevent="handleSubmit">
        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="用户名">
              <el-input v-model="form.username" disabled />
              <div class="form-help">用户名不可修改</div>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="邮箱" :error="errors.email">
              <el-input v-model="form.email" placeholder="请输入邮箱" maxlength="254" clearable />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="名">
              <el-input v-model="form.first_name" placeholder="请输入名" maxlength="30" clearable />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="姓">
              <el-input v-model="form.last_name" placeholder="请输入姓" maxlength="150" clearable />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="注册时间">
              <el-input v-model="form.date_joined" disabled />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="最后登录">
              <el-input v-model="form.last_login" disabled />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-footer">
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            <el-icon><Check /></el-icon> 保存修改
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { UserFilled, Check } from "@element-plus/icons-vue";
import { fetchProfile, updateProfile } from '../../../api/auth';

const saving = ref(false);
const errors = reactive({ email: "" });

const form = reactive({
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  date_joined: "",
  last_login: "",
});

function clearErrors() {
  errors.email = "";
}

async function loadProfile() {
  try {
    const data = await fetchProfile();
    form.username = data.username || "";
    form.email = data.email || "";
    form.first_name = data.first_name || "";
    form.last_name = data.last_name || "";
    form.date_joined = data.date_joined ? formatTime(data.date_joined) : "-";
    form.last_login = data.last_login ? formatTime(data.last_login) : "-";
  } catch (e) {
    ElMessage.error("加载个人资料失败: " + (e.message || "未知错误"));
  }
}

async function handleSubmit() {
  clearErrors();
  saving.value = true;
  try {
    const res = await updateProfile({
      email: form.email,
      first_name: form.first_name,
      last_name: form.last_name,
    });
    ElMessage.success(res.detail || "个人资料已更新");
  } catch (e) {
    const msg = e.message || "保存失败";
    if (msg.includes("email")) {
      errors.email = msg;
    } else {
      ElMessage.error(msg);
    }
  } finally {
    saving.value = false;
  }
}

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

onMounted(() => {
  loadProfile();
});
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  max-width: 720px;
  align-self: center;
  width: 100%;
}

.card-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f2f3f5;
}

.profile-form :deep(.el-form-item) {
  margin-bottom: 22px;
}
.profile-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
</style>
