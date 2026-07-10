<template>
  <div class="add-tc-dialog">
    <el-input v-model="search" placeholder="搜索测试用例..." clearable class="mb-3" />
    <div v-if="!loading">
      <!-- 分组折叠 -->
      <el-collapse v-if="groupedCases.length">
        <el-collapse-item v-for="group in groupedCases" :key="group.id" :title="`${group.name} (${group.cases.length})`">
          <el-table :data="group.cases" size="small">
            <el-table-column label="名称" prop="name" />
            <el-table-column label="方法" width="80"><template #default="{row}"><RequestMethodBadge :method="row.request_method" /></template></el-table-column>
            <el-table-column label="URL" min-width="120"><template #default="{row}"><code class="url-code">{{ row.request_url }}</code></template></el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{row}">
                <el-button v-if="addedIds.has(row.id)" size="small" disabled>已添加</el-button>
                <el-button v-else size="small" type="primary" @click="addCase(row.id)">添加</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>
      <!-- 未分组 -->
      <div v-if="ungrouped.length">
        <h6 class="section-title">未分组</h6>
        <el-table :data="ungrouped" size="small">
          <el-table-column label="名称" prop="name" />
          <el-table-column label="方法" width="80"><template #default="{row}"><RequestMethodBadge :method="row.request_method" /></template></el-table-column>
          <el-table-column label="URL" min-width="120"><template #default="{row}"><code class="url-code">{{ row.request_url }}</code></template></el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{row}">
              <el-button v-if="addedIds.has(row.id)" size="small" disabled>已添加</el-button>
              <el-button v-else size="small" type="primary" @click="addCase(row.id)">添加</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { testCaseApi, testCaseGroupApi, testSuiteApi } from '../../api/index.js'
import { useTestSuiteStore } from '../../stores/testSuite.js'
import RequestMethodBadge from '../common/RequestMethodBadge.vue'

const props = defineProps({ suiteId: Number, projectId: Number })
const emit = defineEmits(['added', 'close'])

const store = useTestSuiteStore()
const search = ref('')
const loading = ref(true)
const allCases = ref([])
const groups = ref([])
const addedIds = ref(new Set())

// Grouped cases
const groupedCases = computed(() => {
  const map = {}
  allCases.value.forEach(c => {
    if (!c.group) return
    const gid = c.group
    if (!map[gid]) {
      const g = groups.value.find(x => x.id === gid)
      map[gid] = { id: gid, name: g?.name || 'Unknown', cases: [] }
    }
    if (!search.value || c.name.toLowerCase().includes(search.value.toLowerCase())) {
      map[gid].cases.push(c)
    }
  })
  return Object.values(map).filter(g => g.cases.length > 0)
})

// Ungrouped cases
const ungrouped = computed(() => {
  return allCases.value.filter(c => {
    if (c.group) return false
    if (!search.value) return true
    return c.name.toLowerCase().includes(search.value.toLowerCase())
  })
})

async function addCase(caseId) {
  try {
    await store.addTestCase(props.suiteId, { test_case_id: caseId, order: addedIds.value.size + 1 })
    addedIds.value.add(caseId)
    ElMessage.success('已添加')
    emit('added')
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(async () => {
  try {
    const [cases, groupData, suite] = await Promise.all([
      testCaseApi.list({ project: props.projectId, page_size: 1000 }),
      testCaseGroupApi.list(props.projectId),
      testSuiteApi.get(props.suiteId),
    ])
    allCases.value = cases.results || cases
    groups.value = groupData.results || groupData
    // Get existing case IDs
    if (suite?.test_suite_cases) {
      suite.test_suite_cases.forEach(sc => addedIds.value.add(sc.test_case))
    }
  } catch (e) { /* ignore */ }
  finally { loading.value = false }
})
</script>

<style scoped>
.url-code { font-size:12px; background:#f5f7fa; padding:2px 6px; border-radius:4px; display:inline-block; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.section-title { font-size:14px; font-weight:600; color:#606266; margin-bottom:6px; }
</style>
