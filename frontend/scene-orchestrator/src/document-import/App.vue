<template>
  <div class="fade-in"><DocumentGenList /></div>
</template>

<script setup>
import DocumentGenList from './components/DocumentGenList.vue'
</script>

<style>
#app {
  padding: 20px 24px;
  background: var(--bg-body, #f5f7fb);
  min-height: 100vh;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeInUp 0.25s ease; }
</style>
