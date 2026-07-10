<template>
  <div class="tc-run" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h3 class="page-title">运行测试用例</h3>
      </div>
    </div>

    <el-row :gutter="20" v-if="testCase">
      <!-- 左侧：用例详情 -->
      <el-col :xs="24" :md="16" :lg="16">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header-row">
              <span class="card-title"><el-icon><InfoFilled /></el-icon> 用例详情</span>
              <el-tag size="small" effect="plain">{{ testCase.name }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="项目">
              <el-tag size="small" effect="plain">{{ testCase.project_name || testCase.project }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="请求方式"><RequestMethodBadge :method="testCase.request_method" /></el-descriptions-item>
            <el-descriptions-item label="URL"><code class="url-text">{{ testCase.request_url }}</code></el-descriptions-item>
            <el-descriptions-item label="预期状态码"><el-tag size="small" type="info" effect="plain">{{ testCase.expected_status_code }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="描述">{{ testCase.description || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 右侧：运行配置 -->
      <el-col :xs="24" :md="8" :lg="8">
        <el-card shadow="never" class="config-card">
          <template #header><span class="card-title"><el-icon><Setting /></el-icon> 运行配置</span></template>
          <el-form label-position="top" class="run-form">
            <el-form-item label="测试环境" required>
              <el-select v-model="selectedEnv" placeholder="选择环境" style="width:100%">
                <el-option v-for="env in environments" :key="env.id" :label="`${env.name} (${env.base_url})`" :value="env.id" />
              </el-select>
            </el-form-item>
            <div v-if="selectedEnvObj" class="env-preview">
              <div class="env-row"><span class="env-label">基础URL：</span><code>{{ selectedEnvObj.base_url }}</code></div>
              <div class="env-row"><span class="env-label">完整URL：</span><code class="url-highlight">{{ fullUrl }}</code></div>
            </div>
            <el-button
              type="success"
              :disabled="!selectedEnv"
              :loading="running"
              @click="doRun"
              class="run-btn"
              size="large"
            >
              <el-icon><CaretRight /></el-icon> 立即运行
            </el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行结果 -->
    <transition name="fade">
      <el-card v-if="result" shadow="never" class="result-card">
        <template #header>
          <div class="card-header-row">
            <span class="card-title"><el-icon><DataBoard /></el-icon> 运行结果</span>
            <div class="header-actions">
              <StatusBadge :status="result.status" />
              <el-button
                v-if="result.test_run"
                type="primary"
                size="small"
                link
                @click="goToTestRun(result.test_run)"
              >
                <el-icon><View /></el-icon> 查看测试运行详情
              </el-button>
            </div>
          </div>
        </template>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="状态">
            <StatusBadge :status="result.status" />
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            <span :class="result.response_time > 1000 ? 'text-warning' : ''">{{ Math.round(result.response_time) }}ms</span>
          </el-descriptions-item>
          <el-descriptions-item label="响应状态码">
            <el-tag size="small" :type="result.response_status_code >= 400 ? 'danger' : 'success'" effect="plain">
              {{ result.response_status_code }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="错误信息">
            {{ result.error_message || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { View } from '@element-plus/icons-vue'
import { useTestCaseStore } from '../stores/testCase.js'
import { environmentApi, testCaseApi } from '../api/index.js'
import RequestMethodBadge from '../components/common/RequestMethodBadge.vue'
import StatusBadge from '../components/common/StatusBadge.vue'

const props = defineProps({ id: [String, Number] })
const store = useTestCaseStore()
const loading = ref(false)
const running = ref(false)
const selectedEnv = ref(null)
const environments = ref([])
const result = ref(null)
const testCase = ref(null)

const selectedEnvObj = computed(() => environments.value.find(e => e.id === selectedEnv.value))
const fullUrl = computed(() => selectedEnvObj.value ? `${selectedEnvObj.value.base_url}${testCase.value?.request_url||''}` : '')

onMounted(async () => {
  loading.value = true
  try {
    testCase.value = await testCaseApi.get(props.id)
    environments.value = (await environmentApi.list(testCase.value.project)).results || []
    const saved = localStorage.getItem(`tc_run_env_${testCase.value.project}`)
    if (saved) selectedEnv.value = Number(saved)
  } catch (e) { ElMessage.error('加载失败') }
  finally { loading.value = false }
})

watch(selectedEnv, (v) => { if (v && testCase.value) localStorage.setItem(`tc_run_env_${testCase.value.project}`, v) })

function goToTestRun(testRunId) {
  window.open(`/test-runs/${testRunId}/`, '_blank')
}

async function doRun() {
  running.value = true
  try {
    result.value = await store.run(props.id, selectedEnv.value)
    ElMessage.success(result.value.status === 'passed' ? '测试通过' : '测试失败')
  } catch (e) { ElMessage.error(e.message) }
  finally { running.value = false }
}
</script>

<style scoped>
.tc-run { padding:0; }

/* ---- 页面标题 ---- */
.page-header {
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:20px;
}
.page-header-left { display:flex; align-items:center; gap:8px; }
.back-btn { font-size:14px; color:#606266; }
.page-title { font-size:22px; font-weight:600; color:#303133; margin:0; line-height:1.3; }

/* ---- 信息卡片 ---- */
.info-card { border:1px solid #ebeef5; border-radius:8px; margin-bottom:20px; }
.info-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.card-title { font-size:16px; font-weight:600; color:#303133; display:flex; align-items:center; gap:6px; }
.card-header-row { display:flex; justify-content:space-between; align-items:center; }
.header-actions { display:flex; align-items:center; gap:12px; }

.url-text {
  font-size:13px; color:#409eff; background:#ecf5ff;
  padding:2px 8px; border-radius:4px; word-break:break-all;
}

/* ---- 运行配置 ---- */
.config-card { border:1px solid #ebeef5; border-radius:8px; margin-bottom:20px; }
.config-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.run-form :deep(.el-form-item) { margin-bottom:16px; }
.env-preview {
  background:#f6f8fa; border-radius:6px; padding:10px 12px; margin-bottom:16px;
  font-size:13px; line-height:1.8;
}
.env-row { display:flex; gap:6px; align-items:baseline; }
.env-label { color:#606266; font-weight:500; white-space:nowrap; font-size:13px; }
.env-row code {
  font-size:13px; background:transparent; color:#303133; word-break:break-all;
}
.url-highlight { color:#409eff !important; }
.run-btn { width:100%; }

/* ---- 运行结果 ---- */
.result-card { margin-top:20px; border:1px solid #ebeef5; border-radius:8px; }
.result-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.text-warning { color:#e6a23c; font-weight:600; }

.fade-enter-active, .fade-leave-active { transition:opacity .3s; }
.fade-enter-from, .fade-leave-to { opacity:0; }
</style>
