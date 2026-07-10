<template>
  <div class="ts-run" v-loading="loading">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.back()" class="back-btn"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
        <h3 class="page-title">运行测试套件</h3>
      </div>
    </div>

    <el-row :gutter="20" v-if="suite">
      <!-- 左侧：用例列表 -->
      <el-col :xs="24" :md="16" :lg="16">
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header-row">
              <span class="card-title"><el-icon><List /></el-icon> 用例列表</span>
              <el-tag size="small" effect="plain">{{ suite.name }}</el-tag>
            </div>
          </template>
          <el-table :data="suiteCases" size="small" border class="sub-table">
            <el-table-column label="顺序" width="65" align="center">
              <template #default="{row}"><el-tag size="small" type="info" effect="plain" round>{{ row.order }}</el-tag></template>
            </el-table-column>
            <el-table-column label="名称" min-width="160">
              <template #default="{row}"><el-link type="primary" :underline="false">{{ row.test_case_name }}</el-link></template>
            </el-table-column>
            <el-table-column label="方法" width="80" align="center">
              <template #default="{row}"><RequestMethodBadge :method="row.request_method" /></template>
            </el-table-column>
            <el-table-column label="URL" min-width="180" show-overflow-tooltip>
              <template #default="{row}"><code class="url-code">{{ row.request_url }}</code></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右侧：运行配置 -->
      <el-col :xs="24" :md="8" :lg="8">
        <el-card shadow="never" class="config-card">
          <template #header><span class="card-title"><el-icon><Setting /></el-icon> 运行配置</span></template>
          <el-form label-position="top" class="run-form">
            <el-form-item label="运行名称">
              <el-input v-model="runName" placeholder="Suite run: ..." />
            </el-form-item>
            <el-form-item label="默认环境" required>
              <el-select v-model="selectedEnv" placeholder="选择环境" style="width:100%">
                <el-option v-for="env in environments" :key="env.id" :label="`${env.name} (${env.base_url})`" :value="env.id" />
              </el-select>
            </el-form-item>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { testSuiteApi, environmentApi } from '../api/index.js'
import { useTestSuiteStore } from '../stores/testSuite.js'
import RequestMethodBadge from '../components/common/RequestMethodBadge.vue'

const props = defineProps({ id: [String, Number] })
const loading = ref(false)
const running = ref(false)
const suite = ref(null)
const suiteCases = ref([])
const environments = ref([])
const selectedEnv = ref(null)
const runName = ref('')

onMounted(async () => {
  loading.value = true
  try {
    suite.value = await testSuiteApi.get(props.id)
    const casesRes = await testSuiteApi.cases(props.id, { page_size: 1000 })
    suiteCases.value = casesRes.results || []
    environments.value = (await environmentApi.list(suite.value.project)).results || []
    runName.value = `Suite run: ${suite.value.name}`
  } catch (e) { ElMessage.error('加载失败') }
  finally { loading.value = false }
})

async function doRun() {
  running.value = true
  try {
    const store = useTestSuiteStore()
    await store.run(props.id, { name: runName.value, environment_id: selectedEnv.value })
    ElMessage.success('套件运行已提交')
  } catch (e) { ElMessage.error(e.message) }
  finally { running.value = false }
}
</script>

<style scoped>
.ts-run { padding:0; }

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
.sub-table { width:100%; }
.url-code {
  font-size:13px; color:#606266; background:#f5f7fa;
  padding:2px 6px; border-radius:4px;
  display:inline-block; max-width:100%;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}

/* ---- 运行配置 ---- */
.config-card { border:1px solid #ebeef5; border-radius:8px; margin-bottom:20px; }
.config-card :deep(.el-card__header) {
  padding:12px 16px; border-bottom:1px solid #f0f0f0; background:#fafafa;
}
.run-form :deep(.el-form-item) { margin-bottom:16px; }
.run-btn { width:100%; }
</style>
