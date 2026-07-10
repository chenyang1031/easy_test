<template>
  <div class="group-tree">
    <!-- 全部接口 -->
    <div
      class="tree-item"
      :class="{ active: !store.currentGroupId }"
      @click="store.selectGroup(null)"
    >
      <span class="tree-label">全部接口</span>
    </div>

    <!-- 递归渲染 -->
    <GroupTreeNode
      v-for="node in filteredRoots"
      :key="node.id"
      :node="node"
      :depth="0"
      :search="store.groupSearchKeyword"
    />

    <!-- 空状态 -->
    <div v-if="filteredRoots.length === 0 && !store.groupTreeData.length" class="empty-hint">
      <span class="empty-text">暂无分组，点击 + 新建</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'
import GroupTreeNode from './GroupTreeNode.vue'

const store = useApiAssetStore()

// 只显示匹配搜索的根节点
const filteredRoots = computed(() => {
  const kw = (store.groupSearchKeyword || '').trim().toLowerCase()
  return store.groupTreeData.filter(g => matchesSearch(g, kw))
})

function matchesSearch(node, kw) {
  if (!kw) return true
  if (node.name.toLowerCase().includes(kw)) return true
  if (node.children && node.children.length) {
    return node.children.some(c => matchesSearch(c, kw))
  }
  return false
}
</script>

<style scoped>
.group-tree {
  padding: 4px 0;
}
.tree-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: background 0.12s, color 0.12s;
  margin-bottom: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tree-item:hover {
  background: #f5f7fa;
}
.tree-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}
.tree-label {
  user-select: none;
}
.empty-hint {
  text-align: center;
  padding: 16px 8px;
  color: #c0c4cc;
  font-size: 12px;
}
.empty-text {
  display: block;
}
</style>
