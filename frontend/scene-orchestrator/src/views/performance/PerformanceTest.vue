<!-- 兼容旧链接 #/performance：重定向到任务列表 -->
<template><div /></template>
<script setup>
import { onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
onMounted(() => {
  router.replace({ name: "perf-list" });
});
</script>
