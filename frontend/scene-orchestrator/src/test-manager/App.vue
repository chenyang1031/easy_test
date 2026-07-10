<template>
  <div class="test-manager">
    <router-view v-slot="{ Component }">
      <transition name="fade-slide" mode="out-in">
        <component :is="Component" :key="$route.path" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useProjectStore } from './stores/project.js'
onMounted(() => useProjectStore().loadProjects())
</script>

<style scoped>
.test-manager {
  display:flex; flex-direction:column; height:100%;
  padding:20px 24px;
  background: var(--bg-body);
  overflow-y:auto;
}
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
