<template>
  <div class="tree-node">
    <div
      class="tree-item"
      :class="{ active: store.currentGroupId === node.id }"
      :style="{ paddingLeft: (12 + depth * 18) + 'px' }"
      @click="store.selectGroup(node.id)"
    >
      <span class="tree-toggle" @click.stop="toggleExpand">
        <el-icon v-if="hasVisibleChildren" :size="12">
          <ArrowRight v-if="!isExpanded" />
          <ArrowDown v-else />
        </el-icon>
        <span v-else class="tree-toggle-placeholder"></span>
      </span>
      <span class="tree-label">{{ node.name }}</span>
    </div>

    <!-- 展开子节点 -->
    <template v-if="isExpanded && node.children">
      <GroupTreeNode
        v-for="child in filteredChildren"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :search="search"
      />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { useApiAssetStore } from '../stores/apiAsset.js'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  search: { type: String, default: '' },
})

const store = useApiAssetStore()

const hasVisibleChildren = computed(() => {
  return props.node.children && filteredChildren.value.length > 0
})

const filteredChildren = computed(() => {
  if (!props.node.children || !props.node.children.length) return []
  const kw = (props.search || '').trim().toLowerCase()
  if (!kw) return props.node.children
  return props.node.children.filter(c => matchesNode(c, kw))
})

const isExpanded = computed(() => {
  // 有搜索关键词时自动展开
  if ((props.search || '').trim()) return hasVisibleChildren.value
  return store.expandedGroupIds.has(props.node.id)
})

function toggleExpand() {
  if (!hasVisibleChildren.value) return
  const id = props.node.id
  const newSet = new Set(store.expandedGroupIds)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  store.expandedGroupIds = newSet
}

function matchesNode(node, kw) {
  if (!kw) return true
  if (node.name.toLowerCase().includes(kw)) return true
  if (node.children && node.children.length) {
    return node.children.some(c => matchesNode(c, kw))
  }
  return false
}
</script>

<style scoped>
.tree-node {
  /* container for nesting */
}
.tree-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: background 0.12s, color 0.12s;
  margin-bottom: 1px;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
}
.tree-item:hover {
  background: #f5f7fa;
}
.tree-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}
.tree-toggle {
  width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #c0c4cc;
  cursor: pointer;
  border-radius: 3px;
}
.tree-toggle:hover {
  color: #909399;
  background: #ebeef5;
}
.tree-toggle-placeholder {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
.tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: none;
  flex: 1;
}
</style>
