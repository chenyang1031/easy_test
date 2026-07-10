<template>
  <div class="avatar-name">
    <span class="avatar-sm">{{ initial }}</span>
    <span>{{ username }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ username: { type: String, default: '' } })
const initial = computed(() => (props.username || '?')[0].toUpperCase())
</script>

<style scoped>
.avatar-name { display:flex; align-items:center; gap:8px; }
.avatar-sm {
  width:30px; height:30px; border-radius:50%; background:#409eff; color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:500;
}
</style>
