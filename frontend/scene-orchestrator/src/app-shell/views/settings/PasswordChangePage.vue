<template>
  <div class="password-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">修改密码</h2>
      </div>
    </div>

    <div class="panel-card">
      <div class="card-header-row">
        <el-icon><Lock /></el-icon>
        <span>修改登录密码</span>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="password-form"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="当前密码" prop="old_password">
          <el-input
            v-model="form.old_password"
            type="password"
            placeholder="请输入当前密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            placeholder="请输入新密码（至少8位）"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="new_password2">
          <el-input
            v-model="form.new_password2"
            type="password"
            placeholder="请再次输入新密码"
            show-password
            clearable
          />
        </el-form-item>

        <div class="form-footer">
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            <el-icon><Check /></el-icon> 修改密码
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { Lock, Check } from "@element-plus/icons-vue";
import { changePassword } from '../../../api/auth';

const formRef = ref(null);
const submitting = ref(false);

const form = reactive({
  old_password: "",
  new_password: "",
  new_password2: "",
});

const rules = {
  old_password: [
    { required: true, message: "请输入当前密码", trigger: "blur" },
  ],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 8, message: "新密码长度不能少于 8 个字符", trigger: "blur" },
  ],
  new_password2: [
    { required: true, message: "请再次输入新密码", trigger: "blur" },
    {
      validator: (rule, value, callback) => {
        if (value !== form.new_password) {
          callback(new Error("两次输入的新密码不一致"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const res = await changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
      new_password2: form.new_password2,
    });
    ElMessage.success(res.detail || "密码修改成功");
    // 清空表单
    form.old_password = "";
    form.new_password = "";
    form.new_password2 = "";
    formRef.value.resetFields();
  } catch (e) {
    ElMessage.error(e.message || "密码修改失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.password-page {
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
  max-width: 560px;
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

.password-form :deep(.el-form-item) {
  margin-bottom: 22px;
}
.password-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #303133;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
</style>
