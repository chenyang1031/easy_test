<template>
  <div class="tree-node">
    <div
      class="tree-item"
      :class="{ active: selectedGroupId === node.id }"
      :style="{ paddingLeft: (12 + depth * 20) + 'px' }"
      @click="$emit('select', node.id)"
    >
      <span class="tree-toggle" @click.stop="toggleExpand">
        <el-icon v-if="hasVisibleChildren" :size="12">
          <CaretRight v-if="!isExpanded" />
          <CaretBottom v-else />
        </el-icon>
        <span v-else class="tree-toggle-spacer"></span>
      </span>
      <el-icon v-if="isExpanded" :size="14" color="#e6a23c"><FolderOpened /></el-icon>
      <el-icon v-else :size="14" color="#c0c4cc"><Folder /></el-icon>
      <span class="tree-label">{{ node.name }}</span>
      <span v-if="node.asset_count != null" class="tree-badge">{{ node.asset_count }}</span>
      <el-button
        size="small"
        text
        type="danger"
        class="tree-delete-btn"
        @click.stop="$emit('delete', node)"
      >
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>

    <template v-if="isExpanded && node.children && node.children.length">
      <ProjectGroupTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :selected-group-id="selectedGroupId"
        @select="$emit('select', $event)"
        @delete="$emit('delete', $event)"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { CaretRight, CaretBottom, Folder, FolderOpened, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  selectedGroupId: { type: Number, default: null },
})

const emit = defineEmits(['select', 'delete'])

const expanded = ref(false) // 默认折叠

const hasVisibleChildren = computed(() => {
  return props.node.children && props.node.children.length > 0
})

const isExpanded = computed(() => {
  return expanded.value && hasVisibleChildren.value
})

function toggleExpand() {
  if (!hasVisibleChildren.value) return
  expanded.value = !expanded.value
}
</script>

<style scoped>
.tree-node {
  /* nesting container */
}
.tree-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: background 0.12s, color 0.12s;
  margin-bottom: 1px;
  white-space: nowrap;
  overflow: hidden;
  position: relative;
}
.tree-item:hover {
  background: #f5f7fa;
}
.tree-item:hover .tree-delete-btn {
  opacity: 1;
}
.tree-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}
.tree-item.active .tree-label {
  color: #409eff;
}

.tree-toggle {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #c0c4cc;
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.12s;
}
.tree-toggle:hover {
  color: #606266;
  background: #e8eaed;
}
.tree-toggle-spacer {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: none;
  flex: 1;
  min-width: 0;
}

.tree-badge {
  font-size: 11px;
  color: #c0c4cc;
  margin-left: 4px;
  padding: 0 6px;
  background: #f5f7fa;
  border-radius: 8px;
  line-height: 16px;
  flex-shrink: 0;
}

.tree-delete-btn {
  opacity: 0;
  transition: opacity 0.12s;
  flex-shrink: 0;
  margin-left: 2px;
}
</style>
