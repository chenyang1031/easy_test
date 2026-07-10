<template>
  <div class="project-selector">
    <el-select
      v-model="selectedId"
      placeholder="请选择项目"
      size="default"
      style="width: 220px"
      :loading="loading"
      :disabled="loading && projects.length === 0"
      @change="handleChange"
    >
      <el-option
        v-for="p in projects"
        :key="p.id"
        :label="p.name"
        :value="p.id"
      />
    </el-select>
    <div class="project-stats" v-if="store.projectStats">
      <span class="stat-item">接口 {{ store.projectStats.total_assets || 0 }}</span>
      <span class="stat-sep">|</span>
      <span class="stat-item">分组 {{ store.projectStats.group_count || 0 }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'

const store = useApiAssetStore()
const selectedId = ref(null)
const loading = ref(false)

// 同步 store 中的 platformProjectId 到本地 select 值
watch(() => store.platformProjectId, (val) => {
  selectedId.value = val
})

const projects = ref([])

// 加载项目列表
onMounted(async () => {
  loading.value = true
  try {
    await store.fetchProjects()
    projects.value = store.platformProjects
    if (store.platformProjectId) {
      selectedId.value = store.platformProjectId
    }
  } catch (e) {
    console.error('加载项目列表失败:', e)
  } finally {
    loading.value = false
  }
})

// 监听 store 中项目列表变化
watch(() => store.platformProjects, (val) => {
  projects.value = val || []
})

// 选择变化
async function handleChange(val) {
  if (!val) return
  loading.value = true
  try {
    await store.selectProject(val)
  } catch (e) {
    console.error('切换项目失败:', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.project-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}
.project-stats {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}
.stat-item {
  color: #606266;
}
.stat-sep {
  margin: 0 6px;
  color: #dcdfe6;
}
</style>
