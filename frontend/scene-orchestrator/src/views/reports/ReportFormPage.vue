<template>
  <div class="report-form-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button size="default" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <h2 class="page-title">{{ isEdit ? '编辑报告' : '新建报告' }}</h2>
      </div>
      <div class="page-header-right">
        <el-button size="default" @click="goBack">取消</el-button>
        <el-button size="default" type="primary" :loading="submitting" @click="submitForm">
          {{ isEdit ? '保存修改' : '创建报告' }}
        </el-button>
      </div>
    </div>

    <!-- 表单 -->
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
          <el-input v-model="form.name" placeholder="请输入报告名称" maxlength="255" clearable />
        </el-form-item>

        <el-form-item label="所属项目" prop="project">
          <el-select v-model="form.project" placeholder="请选择项目" class="full-width">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="报告类型" prop="report_type">
          <el-select v-model="form.report_type" placeholder="请选择报告类型" class="full-width">
            <el-option label="测试运行" value="test_run" />
            <el-option label="测试套件" value="test_suite_run" />
            <el-option label="场景执行" value="scene_execution" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="报告格式" prop="report_format">
          <el-radio-group v-model="form.report_format">
            <el-radio value="html">
              <el-tooltip content="渲染为可读性好的 HTML 页面">
                <span>HTML <el-icon style="vertical-align:middle"><InfoFilled /></el-icon></span>
              </el-tooltip>
            </el-radio>
            <el-radio value="json">
              <el-tooltip content="保存为结构化 JSON 数据">
                <span>JSON <el-icon style="vertical-align:middle"><InfoFilled /></el-icon></span>
              </el-tooltip>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="报告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="12"
            placeholder="请输入报告内容（HTML 或 JSON 文本）"
            class="content-input"
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入报告描述（可选）"
            maxlength="500"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="submitting" @click="submitForm" size="large">
              <el-icon><Document /></el-icon>
              {{ isEdit ? '保存修改' : '创建报告' }}
            </el-button>
            <el-button @click="goBack" size="large">取消</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Document, InfoFilled } from "@element-plus/icons-vue";
import { fetchReportDetail, createReport, updateReport } from "../../api/report";
import { fetchProjects } from "../../api/scene";
import { msgSuccess, msgError } from "../../utils/uiMessage.js";

const route = useRoute();
const router = useRouter();

const isEdit = computed(() => !!route.params.id);
const formRef = ref(null);
const submitting = ref(false);
const projects = ref([]);

const form = ref({
  name: "",
  project: "",
  report_type: "custom",
  report_format: "html",
  content: "",
  description: "",
});

const rules = {
  name: [{ required: true, message: "请输入报告名称", trigger: "blur" }],
  project: [{ required: true, message: "请选择项目", trigger: "change" }],
  report_type: [{ required: true, message: "请选择报告类型", trigger: "change" }],
  content: [{ required: true, message: "请输入报告内容", trigger: "blur" }],
};

function goBack() {
  router.push({ name: "reportList" });
}

async function loadProjects() {
  try {
    const res = await fetchProjects();
    projects.value = res.results || res.data || res || [];
    if (Array.isArray(res)) projects.value = res;
  } catch (e) {
    msgError(e?.message || "加载项目列表失败");
  }
}

async function loadReportForEdit() {
  if (!isEdit.value) return;
  try {
    const res = await fetchReportDetail(route.params.id);
    form.value = {
      name: res.name || "",
      project: res.project || "",
      report_type: res.report_type || "custom",
      report_format: res.report_format || "html",
      content: res.content || "",
      description: res.description || "",
    };
  } catch (e) {
    msgError(e?.message || "加载报告信息失败");
  }
}

async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const payload = {
      name: form.value.name,
      project: form.value.project,
      report_type: form.value.report_type,
      report_format: form.value.report_format,
      content: form.value.content,
      description: form.value.description || "",
    };

    if (isEdit.value) {
      await updateReport(route.params.id, payload);
      msgSuccess("报告已更新");
    } else {
      await createReport(payload);
      msgSuccess("报告已创建");
    }
    router.push({ name: "reportList" });
  } catch (e) {
    msgError(e?.message || (isEdit.value ? "更新失败" : "创建失败"));
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  loadProjects();
  if (isEdit.value) loadReportForEdit();
});
</script>

<style scoped>
.report-form-page {
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
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  line-height: 1.3;
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
  max-width: 800px;
}

/* ---- 表单 ---- */
.full-width { width: 100%; }

.content-input :deep(textarea) {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 13px;
  line-height: 1.5;
}

.form-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}
</style>
