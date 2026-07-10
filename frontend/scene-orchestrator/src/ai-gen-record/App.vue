<template>
  <div class="fade-in"><RecordList /></div>
</template>

<script setup>
import RecordList from './components/RecordList.vue'
</script>

<style>
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeInUp 0.25s ease; }
</style>
