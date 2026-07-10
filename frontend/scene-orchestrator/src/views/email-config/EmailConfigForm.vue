<template>
  <div class="email-config-form-page">
    <div class="page-header">
      <div class="page-header-left">
        <el-button size="default" @click="$router.push('/email-config')">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <h2 class="page-title">{{ isEdit ? '编辑邮件配置' : '添加邮件配置' }}</h2>
      </div>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loadingDetail" class="panel-card">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else>
      <div class="panel-card">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleSubmit">
          <el-row :gutter="24">
            <el-col :xs="24" :md="12">
              <el-form-item label="配置名称" prop="name">
                <el-input v-model="form.name" placeholder="例如：生产环境邮件" maxlength="100" clearable />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item label="邮件后端" prop="email_backend">
                <el-select v-model="form.email_backend" style="width:100%" @change="onBackendChange">
                  <el-option label="SMTP" value="smtp" />
                  <el-option label="SendGrid API" value="sendgrid" />
                  <el-option label="Mailgun API" value="mailgun" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item>
            <el-checkbox v-model="form.is_active" :false-label="false" :true-label="true">
              激活此配置
            </el-checkbox>
          </el-form-item>

          <!-- SMTP 设置 -->
          <div v-if="form.email_backend === 'smtp'" class="section-card">
            <div class="section-title"><el-icon><Setting /></el-icon> SMTP 设置</div>
            <el-row :gutter="24">
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 服务器" prop="smtp_host">
                  <el-input v-model="form.smtp_host" placeholder="smtp.example.com" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 端口" prop="smtp_port">
                  <el-input-number v-model="form.smtp_port" :min="1" :max="65535" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 用户名" prop="smtp_username">
                  <el-input v-model="form.smtp_username" placeholder="user@example.com" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="SMTP 密码" prop="smtp_password">
                  <el-input v-model="form.smtp_password" type="password" placeholder="密码" show-password clearable />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :xs="12" :md="6">
                <el-form-item>
                  <el-checkbox v-model="form.smtp_use_tls" :false-label="false" :true-label="true">使用 TLS</el-checkbox>
                </el-form-item>
              </el-col>
              <el-col :xs="12" :md="6">
                <el-form-item>
                  <el-checkbox v-model="form.smtp_use_ssl" :false-label="false" :true-label="true">使用 SSL</el-checkbox>
                </el-form-item>
              </el-col>
            </el-row>
          </div>

          <!-- API 设置 -->
          <div v-else class="section-card">
            <div class="section-title"><el-icon><Key /></el-icon> API 设置</div>
            <el-form-item label="API 密钥" prop="api_key">
              <el-input v-model="form.api_key" type="password" placeholder="请输入 API 密钥" show-password clearable />
            </el-form-item>
            <div v-if="form.email_backend === 'mailgun'" class="form-help">
              Mailgun 域名请在 SMTP 服务器字段中设置
            </div>
          </div>

          <!-- 发件人设置 -->
          <div class="section-card">
            <div class="section-title"><el-icon><UserFilled /></el-icon> 发件人设置</div>
            <el-row :gutter="24">
              <el-col :xs="24" :md="12">
                <el-form-item label="发件人名称" prop="default_from_name">
                  <el-input v-model="form.default_from_name" placeholder="例如：EasyTesting" maxlength="100" clearable />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="发件人邮箱" prop="default_from_email">
                  <el-input v-model="form.default_from_email" placeholder="noreply@example.com" clearable />
                </el-form-item>
              </el-col>
            </el-row>
          </div>

          <div class="form-footer">
            <el-button @click="$router.push('/email-config')">取消</el-button>
            <el-button type="primary" :loading="saving" native-type="submit">
              <el-icon><Check /></el-icon> {{ isEdit ? '保存修改' : '创建配置' }}
            </el-button>
          </div>
        </el-form>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { ArrowLeft, Check, Setting, Key, UserFilled } from "@element-plus/icons-vue";
import { emailConfigApi } from "../../api/emailConfig";

const router = useRouter();
const route = useRoute();

const isEdit = computed(() => !!route.params.id);
const saving = ref(false);
const loadingDetail = ref(false);
const formRef = ref(null);

const form = ref({
  name: "",
  email_backend: "smtp",
  is_active: false,
  smtp_host: "",
  smtp_port: 587,
  smtp_username: "",
  smtp_password: "",
  smtp_use_tls: true,
  smtp_use_ssl: false,
  api_key: "",
  default_from_name: "",
  default_from_email: "",
});

const rules = {
  name: [{ required: true, message: "请输入配置名称", trigger: "blur" }],
  default_from_email: [
    { required: true, message: "请输入发件人邮箱", trigger: "blur" },
    { type: "email", message: "请输入有效的邮箱地址", trigger: "blur" },
  ],
};

function onBackendChange() {
  // 切换后端类型时清空相关字段
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  saving.value = true;
  try {
    const payload = { ...form.value };

    if (isEdit.value) {
      await emailConfigApi.update(route.params.id, payload);
      ElMessage.success("邮件配置已更新");
    } else {
      await emailConfigApi.create(payload);
      ElMessage.success("邮件配置已创建");
    }
    router.push("/email-config");
  } catch (e) {
    ElMessage.error("保存失败: " + (e.message || "未知错误"));
  } finally {
    saving.value = false;
  }
}

async function loadDetail() {
  if (!isEdit.value) return;
  loadingDetail.value = true;
  try {
    const data = await emailConfigApi.get(route.params.id);
    form.value = {
      name: data.name || "",
      email_backend: data.email_backend || "smtp",
      is_active: !!data.is_active,
      smtp_host: data.smtp_host || "",
      smtp_port: data.smtp_port ?? 587,
      smtp_username: data.smtp_username || "",
      smtp_password: data.smtp_password || "",
      smtp_use_tls: data.smtp_use_tls ?? true,
      smtp_use_ssl: data.smtp_use_ssl ?? false,
      api_key: data.api_key || "",
      default_from_name: data.default_from_name || "",
      default_from_email: data.default_from_email || "",
    };
  } catch (e) {
    ElMessage.error("加载配置信息失败");
  } finally {
    loadingDetail.value = false;
  }
}

onMounted(() => {
  loadDetail();
});
</script>

<style scoped>
.email-config-form-page {
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
  flex-wrap: wrap;
  gap: 12px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  max-width: 860px;
  align-self: center;
  width: 100%;
}

.section-card {
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
</style>
