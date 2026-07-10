<template>
  <div class="json-node" :style="{ paddingLeft: depth * 16 + 'px' }">
    <span class="node-toggle" v-if="isObject" @click="expanded = !expanded">
      <el-icon :size="12"><ArrowRight v-if="!expanded" /><ArrowDown v-else /></el-icon>
    </span>
    <span class="node-key">{{ name }}</span>
    <span class="node-colon">: </span>
    <template v-if="isObject && !expanded">
      <span class="node-type">{{ Array.isArray(value) ? `Array(${value.length})` : `{...}` }}</span>
    </template>
    <template v-else-if="!isObject">
      <span class="node-value" :class="[valueClass, { 'var-highlight': isVariable }]">{{ displayValue }}</span>
    </template>
    <div v-if="isObject && expanded">
      <JsonTreeNode
        v-for="(v,k) in objectEntries"
        :key="k"
        :name="String(k)"
        :value="v"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ArrowRight, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  name: { type: String, default: '' },
  value: { default: null },
  depth: { type: Number, default: 0 },
})

const expanded = ref(props.depth < 2)

const isObject = computed(() => props.value !== null && typeof props.value === 'object')
const objectEntries = computed(() => isObject.value ? (Array.isArray(props.value) ? props.value : Object.entries(props.value)) : [])

const displayValue = computed(() => {
  if (props.value === null) return 'null'
  if (typeof props.value === 'string') return `"${props.value}"`
  return String(props.value)
})

const isVariable = computed(() => {
  return typeof props.value === 'string' && /\{\{[^{}]+\}\}/.test(props.value)
})

const valueClass = computed(() => {
  if (props.value === null) return 'null-val'
  if (typeof props.value === 'string') return 'string-val'
  if (typeof props.value === 'number') return 'number-val'
  if (typeof props.value === 'boolean') return 'boolean-val'
  return ''
})
</script>

<style scoped>
.json-node { line-height: 1.6; }
.node-toggle { cursor: pointer; color: #c0c4cc; margin-right: 2px; display: inline-flex; align-items: center; }
.node-toggle:hover { color: #909399; }
.node-key { color: #881391; font-weight: 500; }
.node-colon { color: #999; }
.node-type { color: #999; font-style: italic; }
.string-val { color: #0a860a; }
.number-val { color: #1c00cf; }
.boolean-val { color: #1c00cf; }
.null-val { color: #999; font-style: italic; }
.var-highlight { background: #fdf6ec; color: #e6a23c; padding: 0 3px; border-radius: 3px; font-weight: 500; }
</style>
