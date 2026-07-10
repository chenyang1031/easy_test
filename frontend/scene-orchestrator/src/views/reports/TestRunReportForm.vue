<template>
  <div class="tr-report-form-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button size="default" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 class="page-title">生成测试报告</h2>
        <span class="page-subtitle" v-if="testRun">
          测试运行 #{{ testRun.id }} · {{ testRun.name }}
        </span>
      </div>
      <div class="page-header-right">
        <el-button size="default" @click="goBack">取消</el-button>
        <el-button size="default" type="primary" :loading="submitting" @click="submitForm">
          生成报告
        </el-button>
      </div>
    </div>

    <!-- 加载运行信息 -->
    <div v-if="loadingTestRun" class="panel-card" style="text-align:center;padding:60px;">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- 运行信息未找到 -->
    <el-empty
      v-else-if="loadError"
      description="无法加载测试运行信息"
      :image-size="80"
    >
      <template #description>
        <span>{{ loadError }}</span>
      </template>
      <el-button type="primary" @click="fetchTestRun">重新加载</el-button>
      <el-button @click="goBack">返回列表</el-button>
    </el-empty>

    <template v-else-if="testRun">
      <!-- 运行概要信息 -->
      <div class="panel-card info-card">
        <div class="info-card-header">
          <el-icon><InfoFilled /></el-icon>
          <span>测试运行概要</span>
        </div>
        <el-row :gutter="24" class="info-grid">
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">运行名称</span>
              <span class="info-value">{{ testRun.name }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">运行 ID</span>
              <span class="info-value">#{{ testRun.id }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">状态</span>
              <span class="info-value">
                <el-tag :type="statusTag(testRun.status).type" size="small" effect="light" round>
                  {{ statusTag(testRun.status).text }}
                </el-tag>
              </span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">项目</span>
              <span class="info-value">{{ testRun.project_name || '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">环境</span>
              <span class="info-value">{{ testRun.environment_name || '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item" v-if="testRun.test_suite_name">
              <span class="info-label">测试套件</span>
              <span class="info-value">{{ testRun.test_suite_name }}</span>
            </div>
            <div class="info-item" v-else>
              <span class="info-label">测试套件</span>
              <span class="info-value">-</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">开始时间</span>
              <span class="info-value">{{ testRun.start_time ? formatTime(testRun.start_time) : '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="info-item">
              <span class="info-label">结束时间</span>
              <span class="info-value">{{ testRun.end_time ? formatTime(testRun.end_time) : '-' }}</span>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- 生成表单 -->
      <div class="panel-card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="100px"
          label-position="right"
          size="default"
          @submit.prevent="submitForm"
        >
          <el-form-item label="报告名称" prop="name">
            <el-input
              v-model="form.name"
              placeholder="请输入报告名称"
              maxlength="255"
              clearable
            />
          </el-form-item>

          <el-form-item label="报告描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入报告描述（可选）"
              maxlength="500"
              clearable
            />
          </el-form-item>

          <el-form-item label="报告格式" prop="report_format">
            <el-radio-group v-model="form.report_format">
              <el-radio value="html">
                <el-tooltip content="渲染为可读性好的 HTML 页面，包含节点详情、请求/响应等完整信息">
                  <span>HTML <el-icon style="vertical-align:middle"><InfoFilled /></el-icon></span>
                </el-tooltip>
              </el-radio>
              <el-radio value="json">
                <el-tooltip content="保存为结构化 JSON 数据，便于程序化处理">
                  <span>JSON <el-icon style="vertical-align:middle"><InfoFilled /></el-icon></span>
                </el-tooltip>
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="公开报告" prop="is_public">
            <el-checkbox v-model="form.is_public" :false-label="false" :true-label="true">
              公开报告（无需登录即可查看）
            </el-checkbox>
          </el-form-item>

          <el-form-item>
            <div class="form-actions">
              <el-button type="primary" :loading="submitting" @click="submitForm" size="large">
                <el-icon><Document /></el-icon> 生成报告
              </el-button>
              <el-button @click="goBack" size="large">取消</el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, InfoFilled, Document } from "@element-plus/icons-vue";
import { generateTestRunReport } from "../../api/report";
import { msgSuccess, msgError } from "../../utils/uiMessage.js";

const route = useRoute();
const router = useRouter();

const testRunId = computed(() => route.params.testRunId);
const testRun = ref(null);
const loadingTestRun = ref(false);
const loadError = ref("");
const submitting = ref(false);
const formRef = ref(null);

const form = ref({
  name: "",
  description: "",
  report_format: "html",
  is_public: false,
});

const rules = {
  name: [
    { required: true, message: "请输入报告名称", trigger: "blur" },
    { min: 1, max: 255, message: "报告名称不能超过 255 个字符", trigger: "blur" },
  ],
};

function statusTag(status) {
  const map = {
    completed: { type: "success", text: "已完成" },
    failed: { type: "danger", text: "失败" },
    running: { type: "primary", text: "运行中" },
    pending: { type: "info", text: "待执行" },
  };
  return map[status] || { type: "info", text: status || "未知" };
}

function formatTime(val) {
  if (!val) return "-";
  const d = new Date(val);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push(`/test-runs/${testRunId.value}`);
  }
}

async function fetchTestRun() {
  loadingTestRun.value = true;
  loadError.value = "";
  testRun.value = null;
  try {
    const { testRunApi } = await import("../../test-manager/api/index.js");
    const data = await testRunApi.get(testRunId.value);
    testRun.value = data;

    // 预设默认名称
    if (!form.value.name) {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const ts = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
      form.value.name = `${data.name || "测试运行"} - 测试运行报告 - ${ts}`;
    }
  } catch (e) {
    loadError.value = e?.message || "加载测试运行信息失败";
  } finally {
    loadingTestRun.value = false;
  }
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description || "",
      report_format: form.value.report_format,
      is_public: form.value.is_public,
    };

    const report = await generateTestRunReport(testRunId.value, payload);
    msgSuccess(`报告 "${report.name}" 已生成`);
    router.push({ name: "reportDetail", params: { id: report.id } });
  } catch (e) {
    msgError(e?.message || "生成报告失败");
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  fetchTestRun();
});
</script>

<style scoped>
.tr-report-form-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  line-height: 1.3;
}
.page-subtitle {
  font-size: 14px;
  color: #909399;
}
.page-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ---- 卡片 ---- */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  max-width: 860px;
  align-self: center;
  width: 100%;
}

/* ---- 运行信息概要 ---- */
.info-card {
  padding: 20px 24px;
}
.info-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}
.info-grid {
  row-gap: 12px;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-label {
  font-size: 13px;
  font-weight: 500;
  color: #909399;
}
.info-value {
  font-size: 14px;
  color: #303133;
  word-break: break-word;
}

/* ---- 表单按钮 ---- */
.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}
</style>
