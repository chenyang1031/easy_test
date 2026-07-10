<template>
  <el-tag :type="tagType" size="small">{{ method }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ method: { type: String, required: true } })

const typeMap = { GET:'success', POST:'primary', PUT:'warning', DELETE:'danger', PATCH:'info' }
const tagType = computed(() => typeMap[props.method] || 'info')
</script>
