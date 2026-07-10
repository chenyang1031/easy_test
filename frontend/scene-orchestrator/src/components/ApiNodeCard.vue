<template>
  <div :class="['node-card', statusClass, { selected: selected, disabled: isDisabled }]" @click="$emit('select', node.id)" @contextmenu.prevent="$emit('contextmenu', node, $event)">
    <div class="node-name">{{ node.name || "未命名接口" }}</div>
    <div v-if="isDisabled" class="node-disabled-tip">已禁用</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  selected: {
    type: Boolean,
    default: false
  }
});

const statusClass = computed(() => {
  return "";
});

const isDisabled = computed(() => props.node?.isEnabled === false || props.node?.is_enabled === false);
</script>
