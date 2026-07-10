<template>
  <div class="mock-data-app">
    <router-view v-slot="{ Component }">
      <transition name="fade-slide" mode="out-in">
        <component :is="Component" :key="$route.path" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
</script>

<style>
#app {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: calc(100vh - 120px);
}
.mock-data-app {
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 20px 24px;
  background: var(--bg-body);
  overflow-y: auto;
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
