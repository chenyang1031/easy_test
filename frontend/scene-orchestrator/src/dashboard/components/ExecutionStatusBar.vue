<template>
  <div class="card border-0 bg-light">
    <div class="card-body py-2 d-flex flex-wrap align-items-center gap-3">
      <span class="text-muted small">场景执行状态</span>
      <el-tag type="primary">{{ dist.running }} 执行中</el-tag>
      <el-tag type="success">{{ dist.success }} 成功</el-tag>
      <el-tag type="warning">{{ dist.partialSuccess }} 部分成功</el-tag>
      <el-tag type="danger">{{ dist.failed }} 失败</el-tag>
    </div>
  </div>
</template>

<script setup>
defineProps({
  dist: {
    type: Object,
    required: true,
  },
})
</script>
