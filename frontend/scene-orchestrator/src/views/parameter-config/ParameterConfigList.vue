<template>
  <div class="param-config-page">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">参数配置</h2>
      </div>
      <div class="page-header-right">
        <el-button :loading="testingAi" @click="handleTestAi">
          <el-icon><Connection /></el-icon> 测试 AI 接口
        </el-button>
      </div>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="panel-card">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 空状态 -->
    <el-empty v-else-if="!list.length" description="暂无参数配置" :image-size="80">
      <template #image>
        <el-icon :size="64" color="#c0c4cc"><Setting /></el-icon>
      </template>
      <p class="text-muted">系统将自动初始化 AI 相关参数配置</p>
    </el-empty>

    <!-- 表格 -->
    <template v-else>
      <div class="panel-card">
        <el-table :data="list" stripe class="data-table">
          <el-table-column label="参数键" min-width="200">
            <template #default="{ row }">
              <code class="param-key">{{ row.key }}</code>
            </template>
          </el-table-column>
          <el-table-column label="参数值" min-width="260">
            <template #default="{ row }">
              <span class="param-value" :title="row.value">{{ truncateValue(row.value) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.description || '-' }}</template>
          </el-table-column>
          <el-table-column label="分类" width="100">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.category || 'general' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="150">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="handleEdit(row)">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <!-- AI 测试结果对话框 -->
    <el-dialog v-model="testResult.visible" title="AI 接口测试结果" width="480px">
      <el-alert
        v-if="testResult.success"
        title="测试成功"
        :description="testResult.message"
        type="success"
        show-icon
      />
      <el-alert
        v-else
        title="测试失败"
        :description="testResult.message"
        type="error"
        show-icon
      />
      <template #footer>
        <el-button @click="testResult.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialog.visible" title="编辑参数" width="640px">
      <el-form label-position="top">
        <el-form-item label="参数键">
          <el-input :model-value="editDialog.key" disabled />
        </el-form-item>
        <el-form-item label="参数值">
          <el-input
            v-model="editDialog.value"
            type="textarea"
            :rows="4"
            placeholder="请输入参数值"
          />
        </el-form-item>
        <el-form-item label="说明">
          <el-input :model-value="editDialog.description" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="confirmEdit">
          <el-icon><Check /></el-icon> 保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Setting, Connection, Edit, Check } from "@element-plus/icons-vue";
import { parameterConfigApi } from "../../api/parameterConfig";

const list = ref([]);
const loading = ref(false);
const testingAi = ref(false);

const testResult = reactive({
  visible: false,
  success: false,
  message: "",
});

const editDialog = reactive({
  visible: false,
  configId: null,
  key: "",
  value: "",
  description: "",
  saving: false,
});

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function truncateValue(val) {
  if (!val) return "-";
  return val.length > 60 ? val.substring(0, 60) + "..." : val;
}

async function fetchList() {
  loading.value = true;
  try {
    list.value = await parameterConfigApi.list();
  } catch { /* ignore */ }
  finally { loading.value = false; }
}

async function handleTestAi() {
  testingAi.value = true;
  try {
    const res = await parameterConfigApi.testAi();
    testResult.success = res.success;
    testResult.message = res.message;
  } catch (e) {
    testResult.success = false;
    testResult.message = e.message || "测试请求失败";
  } finally {
    testingAi.value = false;
    testResult.visible = true;
  }
}

function handleEdit(row) {
  editDialog.visible = true;
  editDialog.configId = row.id;
  editDialog.key = row.key;
  editDialog.value = row.value || "";
  editDialog.description = row.description || "";
  editDialog.saving = false;
}

async function confirmEdit() {
  editDialog.saving = true;
  try {
    await parameterConfigApi.update(editDialog.configId, { value: editDialog.value });
    ElMessage.success(`参数「${editDialog.key}」已更新`);
    editDialog.visible = false;
    await fetchList();
  } catch (e) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    editDialog.saving = false;
  }
}

onMounted(() => {
  fetchList();
});
</script>

<style scoped>
.param-config-page {
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

.param-key {
  font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
  font-size: 13px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #303133;
}

.param-value {
  font-size: 13px;
  color: #606266;
  word-break: break-all;
}

.text-muted { color: #909399; }
</style>
