<template>
  <div class="coming-soon">
    <el-result
      icon="info"
      title="功能迁移中"
      sub-title="此页面正在从 Django 模板迁移至 Vue，将在 Phase 2 中完成。"
    >
      <template #extra>
        <el-button type="primary" @click="goBack">返回仪表盘</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
function goBack() {
  router.push('/dashboard')
}
</script>

<style scoped>
.coming-soon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
</style>
