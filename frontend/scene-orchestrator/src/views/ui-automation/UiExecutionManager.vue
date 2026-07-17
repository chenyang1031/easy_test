<template>
  <div class="ui-execution-manager">
    <div class="toolbar">
      <el-select v-model="statusFilter" size="small" clearable placeholder="状态" style="width: 120px" @change="loadRecords">
        <el-option label="待执行" :value="0" /><el-option label="执行中" :value="1" />
        <el-option label="成功" :value="2" /><el-option label="失败" :value="3" />
      </el-select>
      <el-button size="small" @click="loadRecords">刷新</el-button>
    </div>
    <el-table :data="records" size="small" stripe v-loading="loading" empty-text="暂无执行记录">
      <el-table-column prop="name" label="批次名称" min-width="200" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 2 ? 'success' : row.status === 3 ? 'danger' : row.status === 1 ? 'warning' : 'info'" size="small">
            {{ ['待执行','执行中','成功','失败','部分成功'][row.status] || '未知' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="通过/总数" width="100" align="center">
        <template #default="{ row }">{{ row.passed_cases }}/{{ row.total_cases }}</template>
      </el-table-column>
      <el-table-column prop="pass_rate" label="通过率" width="80" align="center">
        <template #default="{ row }">{{ row.pass_rate }}%</template>
      </el-table-column>
      <el-table-column prop="trigger_type" label="触发" width="80">
        <template #default="{ row }">{{ { manual: '手动', scheduled: '定时', api: 'API' }[row.trigger_type] }}</template>
      </el-table-column>
      <el-table-column prop="duration" label="耗时" width="80">
        <template #default="{ row }">{{ row.duration ? row.duration.toFixed(1) + 's' : '-' }}</template>
      </el-table-column>
      <el-table-column prop="creator_name" label="执行者" width="80" />
      <el-table-column prop="created_at" label="时间" width="160">
        <template #default="{ row }">{{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" align="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="viewDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="showDetail" title="执行详情" size="600px">
      <div v-if="detail">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="批次">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ ['待执行','执行中','成功','失败','部分成功'][detail.status] }}</el-descriptions-item>
          <el-descriptions-item label="总数">{{ detail.total_cases }}</el-descriptions-item>
          <el-descriptions-item label="通过率">{{ detail.pass_rate }}%</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ detail.duration?.toFixed(1) }}s</el-descriptions-item>
          <el-descriptions-item label="执行者">{{ detail.creator_name }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin: 16px 0 8px;">执行记录</h4>
        <el-table :data="detail.execution_records || []" size="small" stripe>
          <el-table-column prop="test_case_name" label="用例" min-width="150" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 2 ? 'success' : row.status === 3 ? 'danger' : 'info'" size="small">
                {{ ['待执行','执行中','通过','失败'][row.status] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration" label="耗时" width="80">
            <template #default="{ row }">{{ row.duration?.toFixed(1) }}s</template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误" min-width="150" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { uiBatchApi } from '../../api/uiAutomation'

const props = defineProps({ projectId: [Number, String] })
const records = ref([])
const loading = ref(false)
const statusFilter = ref('')
const showDetail = ref(false)
const detail = ref(null)

async function loadRecords() {
  loading.value = true
  try {
    const params = { project: props.projectId }
    if (statusFilter.value !== '') params.status = statusFilter.value
    const data = await uiBatchApi.list(params)
    records.value = data.results || data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

async function viewDetail(row) {
  try { detail.value = await uiBatchApi.detail(row.id); showDetail.value = true }
  catch (e) { console.error(e) }
}

watch(() => props.projectId, loadRecords)
onMounted(loadRecords)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
