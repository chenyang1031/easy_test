<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>最近场景执行</span>
      <a href="/test-suites-vue/#/scene-executions" class="btn btn-sm btn-outline-primary">
        <el-icon style="margin-right:4px"><List /></el-icon>
        查看全部
      </a>
    </div>
    <div class="card-body">
      <!-- 空状态 -->
      <el-empty v-if="executions.length === 0" description="暂无场景执行记录" />

      <!-- 表格 -->
      <div v-else class="table-responsive">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th>场景</th>
              <th>环境</th>
              <th>状态</th>
              <th>耗时</th>
              <th>开始时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ex in executions" :key="ex.sceneId + '-' + ex.createdAt">
              <td>
                <a :href="`/test-scene-orchestrator/#/scenes/${ex.sceneId}/executions/${ex.executionId}`">
                  {{ ex.sceneName }}
                </a>
              </td>
              <td>{{ ex.environmentName }}</td>
              <td>
                <el-tag :type="sceneStatusType(ex.status)" size="small">
                  {{ sceneStatusLabel(ex.status) }}
                </el-tag>
              </td>
              <td>{{ ex.durationDisplay }}</td>
              <td>{{ ex.startedAt }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { List } from '@element-plus/icons-vue'

defineProps({
  executions: {
    type: Array,
    required: true,
  },
})

const SCENE_STATUS_MAP = {
  success: { type: 'success', label: '成功' },
  failed: { type: 'danger', label: '失败' },
  running: { type: 'primary', label: '执行中' },
  partial_success: { type: 'warning', label: '部分成功' },
}

function sceneStatusType(status) {
  return SCENE_STATUS_MAP[status]?.type || 'info'
}
function sceneStatusLabel(status) {
  return SCENE_STATUS_MAP[status]?.label || status
}
</script>
