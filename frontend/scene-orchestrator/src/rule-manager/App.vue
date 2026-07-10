<template>
  <div class="fade-in"><RuleList /></div>
</template>

<script setup>
import RuleList from './components/RuleList.vue'
</script>

<style>
#app {
  padding: 20px 24px;
  background: var(--bg-body);
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeInUp 0.25s ease; }
</style>
