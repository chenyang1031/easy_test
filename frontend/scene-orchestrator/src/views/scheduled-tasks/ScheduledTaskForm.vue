<template>
  <div class="st-form" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h3 class="page-title">{{ isEdit ? '编辑定时任务' : '新建定时任务' }}</h3>
      </div>
    </div>

    <div class="panel-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="default"
        @submit.prevent="handleSubmit"
      >
        <!-- 基本信息 -->
        <h4 class="section-title"><el-icon><InfoFilled /></el-icon> 基本信息</h4>
        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="任务名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入任务名称" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="所属项目" prop="project">
              <el-select
                v-model="form.project"
                placeholder="先选择项目"
                filterable
                style="width: 100%"
                @change="onProjectChange"
                :disabled="isEdit"
              >
                <el-option
                  v-for="p in projects"
                  :key="p.id"
                  :label="p.name"
                  :value="p.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 任务类型切换 -->
        <el-row :gutter="24">
          <el-col :xs="24" :md="24">
            <el-form-item label="任务类型">
              <el-radio-group v-model="form.task_type" @change="onTaskTypeChange" :disabled="isEdit">
                <el-radio value="suite">测试套件</el-radio>
                <el-radio value="scene">场景编排</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="24">
          <!-- 测试套件选择 -->
          <el-col :xs="24" :md="12" v-if="form.task_type === 'suite'">
            <el-form-item label="测试套件" prop="test_suite">
              <el-select v-model="form.test_suite" placeholder="选择测试套件" filterable style="width: 100%">
                <el-option
                  v-for="suite in suites"
                  :key="suite.id"
                  :label="suite.name"
                  :value="suite.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 场景编排选择 -->
          <el-col :xs="24" :md="12" v-if="form.task_type === 'scene'">
            <el-form-item label="场景编排" prop="test_scene">
              <el-select v-model="form.test_scene" placeholder="选择场景编排" filterable style="width: 100%">
                <el-option
                  v-for="scene in scenes"
                  :key="scene.id"
                  :label="scene.name"
                  :value="scene.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="执行环境" prop="environment">
              <el-select v-model="form.environment" placeholder="选择执行环境" filterable style="width: 100%">
                <el-option
                  v-for="env in environments"
                  :key="env.id"
                  :label="env.name"
                  :value="env.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="任务描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选，输入任务描述" />
        </el-form-item>

        <el-divider />

        <!-- 调度配置 -->
        <h4 class="section-title"><el-icon><Timer /></el-icon> 调度配置</h4>
        <el-row :gutter="24">
          <el-col :xs="24" :md="8">
            <el-form-item label="调度类型" prop="schedule_type">
              <el-select v-model="form.schedule_type" placeholder="选择调度类型" style="width: 100%" @change="onScheduleTypeChange">
                <el-option label="单次执行" value="once" />
                <el-option label="每日执行" value="daily" />
                <el-option label="每周执行" value="weekly" />
                <el-option label="每月执行" value="monthly" />
                <el-option label="Cron表达式" value="cron" />
              </el-select>
            </el-form-item>
          </el-col>

          <!-- ===== 单次 ===== -->
          <template v-if="form.schedule_type === 'once'">
            <el-col :xs="24" :md="8">
              <el-form-item label="执行日期" prop="scheduled_date">
                <el-date-picker v-model="form.scheduled_date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="8">
              <el-form-item label="执行时间" prop="scheduled_time">
                <el-time-picker v-model="form.scheduled_time" placeholder="选择时间" style="width: 100%" value-format="HH:mm:ss" />
              </el-form-item>
            </el-col>
          </template>

          <!-- ===== 每日 ===== -->
          <template v-if="form.schedule_type === 'daily'">
            <el-col :xs="24" :md="8">
              <el-form-item label="执行时间" prop="scheduled_time">
                <el-time-picker v-model="form.scheduled_time" placeholder="选择时间" style="width: 100%" value-format="HH:mm:ss" />
              </el-form-item>
            </el-col>
          </template>

          <!-- ===== 每周 ===== -->
          <template v-if="form.schedule_type === 'weekly'">
            <el-col :xs="24" :md="8">
              <el-form-item label="星期几" prop="weekday">
                <el-select v-model="form.weekday" placeholder="选择星期" style="width: 100%">
                  <el-option label="周一" :value="1" />
                  <el-option label="周二" :value="2" />
                  <el-option label="周三" :value="3" />
                  <el-option label="周四" :value="4" />
                  <el-option label="周五" :value="5" />
                  <el-option label="周六" :value="6" />
                  <el-option label="周日" :value="7" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="8">
              <el-form-item label="执行时间" prop="scheduled_time">
                <el-time-picker v-model="form.scheduled_time" placeholder="选择时间" style="width: 100%" value-format="HH:mm:ss" />
              </el-form-item>
            </el-col>
          </template>

          <!-- ===== 每月 ===== -->
          <template v-if="form.schedule_type === 'monthly'">
            <el-col :xs="24" :md="8">
              <el-form-item label="每月第几天" prop="day_of_month">
                <el-input-number v-model="form.day_of_month" :min="1" :max="31" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="8">
              <el-form-item label="执行时间" prop="scheduled_time">
                <el-time-picker v-model="form.scheduled_time" placeholder="选择时间" style="width: 100%" value-format="HH:mm:ss" />
              </el-form-item>
            </el-col>
          </template>

          <!-- ===== Cron ===== -->
          <template v-if="form.schedule_type === 'cron'">
            <el-col :xs="24" :md="12">
              <el-form-item label="Cron表达式" prop="cron_expression">
                <el-input v-model="form.cron_expression" placeholder="分 时 日 月 周，如: 0 9 * * 1-5" />
                <template #help>
                  <div class="form-help">
                    格式: 分 时 日 月 周
                    <el-link type="primary" href="https://crontab.guru/" target="_blank" :underline="false">在线生成器</el-link>
                  </div>
                </template>
              </el-form-item>
            </el-col>
          </template>
        </el-row>

        <el-divider />

        <!-- 通知配置 -->
        <h4 class="section-title"><el-icon><Message /></el-icon> 通知配置</h4>
        <el-form-item>
          <el-switch v-model="form.send_email_notification" active-text="发送邮件通知" />
        </el-form-item>

        <template v-if="form.send_email_notification">
          <el-form-item label="通知邮箱" prop="notification_emails">
            <el-input v-model="form.notification_emails" placeholder="多个邮箱用逗号分隔" />
            <template #help><div class="form-help">多个邮箱地址用逗号分隔</div></template>
          </el-form-item>
          <el-row :gutter="24">
            <el-col :xs="24" :md="12">
              <el-form-item>
                <el-checkbox v-model="form.notify_on_success">成功时通知</el-checkbox>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-form-item>
                <el-checkbox v-model="form.notify_on_failure">失败时通知</el-checkbox>
              </el-form-item>
            </el-col>
          </el-row>
        </template>

        <el-divider />

        <!-- 重试配置 -->
        <h4 class="section-title"><el-icon><Refresh /></el-icon> 重试配置</h4>
        <el-row :gutter="24">
          <el-col :xs="24" :md="12">
            <el-form-item label="最大重试次数" prop="max_retries">
              <el-input-number v-model="form.max_retries" :min="0" :max="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="重试间隔(秒)" prop="retry_delay">
              <el-input-number v-model="form.retry_delay" :min="10" :max="3600" :step="30" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 提交 -->
        <div class="form-footer">
          <el-button @click="$router.back()">取消</el-button>
          <el-button type="primary" native-type="submit" :loading="submitting">
            {{ isEdit ? '保存修改' : '创建任务' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import {
  ArrowLeft, InfoFilled, Timer, Message, Refresh,
} from "@element-plus/icons-vue";
import { useScheduledTaskStore } from "../../test-manager/stores/scheduledTask";
import { scheduledTaskApi } from "../../api/scheduledTask";
import { projectApi, testSuiteApi, environmentApi } from "../../test-manager/api/index.js";
import { fetchScenes, resolveApiProjectId, fetchEnvironments } from "../../api/scene";

const router = useRouter();
const route = useRoute();
const store = useScheduledTaskStore();

const isEdit = computed(() => !!route.params.id);
const taskId = computed(() => route.params.id);
const formRef = ref(null);
const submitting = ref(false);
const loading = ref(false);

// 下拉选项数据
const projects = ref([]);
const suites = ref([]);
const scenes = ref([]);
const environments = ref([]);

const form = reactive({
  name: "",
  description: "",
  project: null,
  task_type: "suite",
  test_suite: null,
  test_scene: null,
  environment: null,
  schedule_type: "daily",
  scheduled_time: null,
  scheduled_date: null,
  weekday: null,
  day_of_month: null,
  cron_expression: "",
  send_email_notification: true,
  notification_emails: "",
  notify_on_success: false,
  notify_on_failure: true,
  max_retries: 3,
  retry_delay: 300,
});

const rules = {
  name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
  project: [{ required: true, message: "请选择所属项目", trigger: "change" }],
  test_suite: [
    {
      validator: (rule, value, callback) => {
        if (form.task_type === "suite" && !value) {
          callback(new Error("请选择测试套件"));
        } else {
          callback();
        }
      },
      trigger: "change",
    },
  ],
  test_scene: [
    {
      validator: (rule, value, callback) => {
        if (form.task_type === "scene" && !value) {
          callback(new Error("请选择场景编排"));
        } else {
          callback();
        }
      },
      trigger: "change",
    },
  ],
  environment: [{ required: true, message: "请选择执行环境", trigger: "change" }],
  schedule_type: [{ required: true, message: "请选择调度类型", trigger: "change" }],
  cron_expression: [
    {
      validator: (rule, value, callback) => {
        if (form.schedule_type === "cron" && !value) {
          callback(new Error("请输入Cron表达式"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

// ── 生命周期 ──

onMounted(async () => {
  // 1. 加载项目列表
  try {
    const projectData = await projectApi.list();
    projects.value = projectData.results || projectData || [];
  } catch (e) {
    ElMessage.error("加载项目列表失败");
  }

  if (isEdit.value) {
    await loadEditData();
  }
});

async function loadEditData() {
  loading.value = true;
  try {
    const task = await scheduledTaskApi.get(taskId.value);

    // 判断任务类型
    const taskType = task.test_scene ? "scene" : "suite";

    // 加载关联数据
    form.project = task.project_id;
    form.task_type = taskType;

    // 加载项目下的套件/场景
    if (taskType === "suite") {
      await loadSuites(task.project_id);
    } else {
      await loadScenes(task.project_id);
    }

    // 加载环境
    await loadEnvironments(task.project_id);

    Object.assign(form, {
      name: task.name,
      description: task.description || "",
      test_suite: task.test_suite,
      test_scene: task.test_scene,
      environment: task.environment,
      schedule_type: task.schedule_type,
      scheduled_time: task.scheduled_time,
      scheduled_date: task.scheduled_date,
      weekday: task.weekday,
      day_of_month: task.day_of_month,
      cron_expression: task.cron_expression || "",
      send_email_notification: task.send_email_notification,
      notification_emails: task.notification_emails || "",
      notify_on_success: task.notify_on_success,
      notify_on_failure: task.notify_on_failure,
      max_retries: task.max_retries,
      retry_delay: task.retry_delay,
    });
  } catch (e) {
    ElMessage.error("加载任务信息失败");
  } finally {
    loading.value = false;
  }
}

// ── 项目联动 ──

async function onProjectChange(projectId) {
  // 重置类型相关字段
  form.test_suite = null;
  form.test_scene = null;
  form.environment = null;
  suites.value = [];
  scenes.value = [];
  environments.value = [];

  if (!projectId) return;

  await Promise.all([
    loadSuites(projectId),
    loadScenes(projectId),
    loadEnvironments(projectId),
  ]);
}

async function loadSuites(projectId) {
  try {
    const data = await testSuiteApi.list({ project: projectId });
    suites.value = data.results || data || [];
  } catch (e) {
    suites.value = [];
  }
}

async function loadScenes(projectId) {
  try {
    // 先通过 Project ID 找到 ApiProject ID
    const apiProject = await resolveApiProjectId(projectId);
    const apiProjectId = apiProject?.api_project_id;
    if (apiProjectId) {
      const data = await fetchScenes({ project: apiProjectId });
      scenes.value = data.results || data || [];
    } else {
      scenes.value = [];
    }
  } catch (e) {
    scenes.value = [];
  }
}

async function loadEnvironments(projectId) {
  try {
    const data = await fetchEnvironments(projectId);
    environments.value = data.results || data || [];
  } catch (e) {
    environments.value = [];
  }
}

function onTaskTypeChange() {
  form.test_suite = null;
  form.test_scene = null;
}

function onScheduleTypeChange() {
  form.cron_expression = "";
  form.scheduled_time = null;
  form.scheduled_date = null;
  form.weekday = null;
  form.day_of_month = null;
}

// ── 提交 ──

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const payload = { ...form };
    delete payload.task_type;
    delete payload.project;

    // 根据类型清理
    if (payload.test_scene) {
      delete payload.test_suite;
    }
    if (payload.test_suite) {
      delete payload.test_scene;
    }

    // 清理调度类型无关字段
    if (payload.schedule_type !== "once") delete payload.scheduled_date;
    if (!["once", "daily", "weekly", "monthly"].includes(payload.schedule_type)) {
      delete payload.scheduled_time;
    }
    if (payload.schedule_type !== "weekly") delete payload.weekday;
    if (payload.schedule_type !== "monthly") delete payload.day_of_month;
    if (payload.schedule_type !== "cron") delete payload.cron_expression;
    if (!payload.send_email_notification) {
      payload.notification_emails = "";
      payload.notify_on_success = false;
      payload.notify_on_failure = true;
    }

    if (isEdit.value) {
      await store.update(taskId.value, payload);
      ElMessage.success("已更新");
      router.push(`/scheduled-tasks/${taskId.value}`);
    } else {
      const result = await store.create(payload);
      ElMessage.success("创建成功");
      router.push(`/scheduled-tasks/${result.id}`);
    }
  } catch (e) {
    ElMessage.error(e.message || "操作失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.st-form {
  width: 100%;
  max-width: 900px;
  align-self: center;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #0f172a);
}

.back-btn {
  padding: 0 4px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 16px;
  color: var(--text-primary, #0f172a);
}

.form-help {
  font-size: 0.8rem;
  color: var(--text-secondary, #64748b);
  margin-top: 4px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e2e8f0);
}
</style>
