<template>
  <div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>最近测试运行</span>
      <a href="/test-suites-vue/#/test-runs" class="btn btn-sm btn-outline-primary">
        <el-icon style="margin-right:4px"><List /></el-icon>
        查看全部
      </a>
    </div>
    <div class="card-body">
      <div v-loading="loading" element-loading-text="加载中...">
        <!-- 空状态 -->
        <el-empty v-if="!loading && runs.results.length === 0" description="暂无测试运行" />

        <!-- 表格 -->
        <div v-else class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>名称</th>
                <th>项目</th>
                <th>环境</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>动作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in runs.results" :key="run.id">
                <td>{{ run.name }}</td>
                <td>{{ run.projectName }}</td>
                <td>{{ run.environmentName }}</td>
                <td>
                  <el-tag :type="statusType(run.status)" size="small">
                    {{ statusLabel(run.status) }}
                  </el-tag>
                </td>
                <td>{{ run.createdAt }}</td>
                <td>
                  <a :href="run.detailUrl" class="btn btn-sm btn-outline-primary">
                    <el-icon><View /></el-icon>
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div v-if="runs.totalPages > 1" class="d-flex justify-content-center mt-3">
          <el-pagination
            :current-page="runs.currentPage"
            :page-size="5"
            :total="runs.total"
            layout="prev, pager, next"
            @current-change="$emit('page-change', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { View, List } from '@element-plus/icons-vue'

defineProps({
  runs: {
    type: Object,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['page-change'])

const STATUS_MAP = {
  completed: { type: 'success', label: '已完成' },
  failed: { type: 'danger', label: '失败' },
  running: { type: 'primary', label: '运行中' },
  pending: { type: 'info', label: '等待中' },
}

function statusType(status) {
  return STATUS_MAP[status]?.type || 'info'
}
function statusLabel(status) {
  return STATUS_MAP[status]?.label || status
}
</script>
