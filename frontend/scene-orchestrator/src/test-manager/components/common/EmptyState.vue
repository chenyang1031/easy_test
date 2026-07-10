<template>
  <el-empty :description="description" :image-size="80">
    <slot />
  </el-empty>
</template>

<script setup>
defineProps({ description: { type: String, default: '暂无数据' } })
</script>
