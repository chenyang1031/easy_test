<template>
  <el-tag :type="tagType" size="small">{{ label }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, default: '' } })
const map = {
  passed: { type: 'success', label: '通过' },
  completed: { type: 'success', label: '完成' },
  failed: { type: 'danger', label: '失败' },
  error: { type: 'warning', label: '错误' },
  running: { type: 'primary', label: '运行中' },
  pending: { type: 'info', label: '等待' },
  skipped: { type: 'info', label: '跳过' },
}
const tagType = computed(() => map[props.status]?.type || 'info')
const label = computed(() => map[props.status]?.label || props.status)
</script>
