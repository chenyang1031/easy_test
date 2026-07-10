<template>
  <div class="email-config-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">邮件配置</h2>
      </div>
      <div class="page-header-right">
        <el-button type="primary" @click="$router.push('/email-config/create')">
          <el-icon><Plus /></el-icon> 添加配置
        </el-button>
      </div>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="panel-card">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="!list.length" description="暂无邮件配置" :image-size="80">
      <template #image>
        <el-icon :size="64" color="#c0c4cc"><Message /></el-icon>
      </template>
      <p class="text-muted">创建邮件配置以启用密码重置等功能</p>
      <el-button type="primary" @click="$router.push('/email-config/create')">添加配置</el-button>
    </el-empty>

    <!-- 表格 -->
    <template v-else>
      <div class="panel-card">
        <el-table :data="list" stripe class="data-table">
          <el-table-column label="名称" min-width="160">
            <template #default="{ row }">
              <router-link :to="`/email-config/${row.id}/edit`" class="name-link">
                {{ row.name }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="120">
            <template #default="{ row }">{{ row.email_backend === 'smtp' ? 'SMTP' : row.email_backend === 'sendgrid' ? 'SendGrid API' : 'Mailgun API' }}</template>
          </el-table-column>
          <el-table-column label="发件人" min-width="200">
            <template #default="{ row }">
              {{ row.default_from_name }} &lt;{{ row.default_from_email }}&gt;
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.is_active" type="success" size="small" effect="light" round>已激活</el-tag>
              <el-tag v-else type="info" size="small" effect="plain" round>未激活</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="160">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-tooltip content="编辑">
                  <el-button size="small" text @click="$router.push(`/email-config/${row.id}/edit`)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="测试邮件">
                  <el-button size="small" text type="primary" @click="handleTestEmail(row)">
                    <el-icon><Message /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="测试连接">
                  <el-button size="small" text type="warning" :loading="testingConn[row.id]" @click="handleTestConnection(row)">
                    <el-icon><Connection /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="!row.is_active" content="激活">
                  <el-button size="small" text type="success" @click="handleActivate(row)">
                    <el-icon><Check /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-popconfirm title="确定删除此邮件配置？" @confirm="handleDelete(row)">
                  <template #reference>
                    <el-tooltip content="删除">
                      <el-button size="small" text type="danger">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </el-tooltip>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <!-- 测试邮件对话框 -->
    <el-dialog v-model="testDialog.visible" title="发送测试邮件" width="480px">
      <div class="test-dialog-body">
        <p>此功能将使用配置 <strong>{{ testDialog.configName }}</strong> 发送一封测试邮件。</p>
        <el-form label-position="top">
          <el-form-item label="测试邮箱" :error="testDialog.error">
            <el-input v-model="testDialog.email" placeholder="请输入测试邮箱地址" clearable />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="testDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="testDialog.sending" @click="confirmTestEmail">
          <el-icon><Message /></el-icon> 发送测试邮件
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Plus, Message, Edit, Delete, Check, Connection } from "@element-plus/icons-vue";
import { emailConfigApi } from "../../api/emailConfig";

const list = ref([]);
const loading = ref(false);
const testingConn = reactive({});

const testDialog = reactive({
  visible: false,
  configId: null,
  configName: "",
  email: "",
  sending: false,
  error: "",
});

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function fetchList() {
  loading.value = true;
  try {
    list.value = await emailConfigApi.list();
  } catch { /* ignore */ }
  finally { loading.value = false; }
}

function handleTestEmail(row) {
  testDialog.visible = true;
  testDialog.configId = row.id;
  testDialog.configName = row.name;
  testDialog.email = "";
  testDialog.error = "";
  testDialog.sending = false;
}

async function confirmTestEmail() {
  if (!testDialog.email.trim()) {
    testDialog.error = "请输入测试邮箱地址";
    return;
  }
  testDialog.error = "";
  testDialog.sending = true;
  try {
    const res = await emailConfigApi.testEmail(testDialog.configId, testDialog.email.trim());
    ElMessage.success(res.detail || "测试邮件发送成功");
    testDialog.visible = false;
  } catch (e) {
    ElMessage.error(e.message || "发送失败");
  } finally {
    testDialog.sending = false;
  }
}

async function handleTestConnection(row) {
  testingConn[row.id] = true;
  try {
    const res = await emailConfigApi.testConnection(row.id);
    ElMessage.success(res.detail || "连接测试成功");
  } catch (e) {
    ElMessage.error(e.message || "连接测试失败");
  } finally {
    testingConn[row.id] = false;
  }
}

async function handleActivate(row) {
  try {
    const res = await emailConfigApi.activate(row.id);
    ElMessage.success(res.detail || "已激活");
    await fetchList();
  } catch (e) {
    ElMessage.error(e.message || "激活失败");
  }
}

async function handleDelete(row) {
  try {
    await emailConfigApi.remove(row.id);
    ElMessage.success(`邮件配置「${row.name}」已删除`);
    await fetchList();
  } catch (e) {
    ElMessage.error(e.message || "删除失败");
  }
}

onMounted(() => {
  fetchList();
});
</script>

<style scoped>
.email-config-page {
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
.page-header-right {
  display: flex;
  gap: 8px;
}

.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  max-width: 1100px;
  align-self: center;
  width: 100%;
}

.data-table { width: 100%; }

.name-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
}
.name-link:hover { text-decoration: underline; }

.table-actions {
  display: flex;
  gap: 2px;
  flex-wrap: nowrap;
}

.text-muted { color: #909399; }

.test-dialog-body p { margin-bottom: 16px; color: #606266; }
.test-dialog-body strong { color: #303133; }
</style>
