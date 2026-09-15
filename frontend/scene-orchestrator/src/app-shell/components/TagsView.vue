<template>
  <div class="tags-view">
    <div class="tags-scroll" ref="scrollRef" @wheel.prevent="onWheel">
      <div
        v-for="tag in visitedTabs"
        :key="tag.path"
        class="tag-item"
        :class="{ active: tag.path === route.path }"
        @click="go(tag)"
        :title="tag.path"
      >
        <span class="tag-dot"></span>
        <span class="tag-title">{{ tag.title }}</span>
        <span v-if="!tag.affix" class="tag-close" @click.stop="closeTab(tag)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </span>
      </div>
    </div>

    <el-dropdown class="tags-action" trigger="click" @command="handleCommand">
      <button class="tags-action-btn" title="标签操作">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <circle cx="12" cy="5" r="1.5" fill="currentColor" />
          <circle cx="12" cy="12" r="1.5" fill="currentColor" />
          <circle cx="12" cy="19" r="1.5" fill="currentColor" />
        </svg>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="closeOthers">关闭其他标签</el-dropdown-item>
          <el-dropdown-item command="closeAll">关闭全部标签</el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VISITED_TABS_KEY } from '../tabsStorage'

// 固定标签：仪表盘始终存在且不可关闭
const AFFIX_PATH = '/dashboard'

const route = useRoute()
const router = useRouter()
const visitedTabs = ref([])
const scrollRef = ref(null)

function routeTitle(r) {
  return r.meta?.title || r.name || r.path
}

function addTab(r) {
  // 登录等公开页不进标签栏
  if (!r.meta?.title && !r.name) return
  if (r.path === '/login' || r.path === '/register' || r.path.startsWith('/password-reset')) return
  const exists = visitedTabs.value.find(t => t.path === r.path)
  if (exists) {
    exists.title = routeTitle(r)
  } else {
    visitedTabs.value.push({
      path: r.path,
      title: routeTitle(r),
      affix: r.path === AFFIX_PATH,
    })
  }
}

function go(tag) {
  if (tag.path !== route.path) router.push(tag.path)
}

function closeTab(tag) {
  if (tag.affix) return
  const idx = visitedTabs.value.findIndex(t => t.path === tag.path)
  if (idx === -1) return
  visitedTabs.value.splice(idx, 1)
  // 关闭的是当前页 → 切到相邻标签
  if (tag.path === route.path) {
    const next = visitedTabs.value[idx] || visitedTabs.value[idx - 1]
    if (next) router.push(next.path)
  }
}

function handleCommand(cmd) {
  if (cmd === 'closeOthers') {
    visitedTabs.value = visitedTabs.value.filter(t => t.affix || t.path === route.path)
  } else if (cmd === 'closeAll') {
    visitedTabs.value = visitedTabs.value.filter(t => t.affix)
    if (route.path !== AFFIX_PATH) router.push(AFFIX_PATH)
  }
}

function onWheel(e) {
  if (scrollRef.value) scrollRef.value.scrollLeft += e.deltaY
}

function saveTabs() {
  localStorage.setItem(VISITED_TABS_KEY, JSON.stringify(visitedTabs.value))
}

function restoreTabs() {
  try {
    const saved = JSON.parse(localStorage.getItem(VISITED_TABS_KEY) || '[]')
    // 只恢复仍然存在的路由，避免失效标签
    const valid = saved.filter(t => {
      try {
        return router.resolve(t.path).matched.length > 0
      } catch {
        return false
      }
    })
    visitedTabs.value = valid.length ? valid : []
  } catch {
    visitedTabs.value = []
  }
  // 固定标签始终在第一位
  if (!visitedTabs.value.find(t => t.path === AFFIX_PATH)) {
    const home = router.resolve(AFFIX_PATH)
    visitedTabs.value.unshift({ path: AFFIX_PATH, title: routeTitle(home), affix: true })
  }
}

onMounted(() => {
  restoreTabs()
  addTab(route)
  saveTabs()
})

watch(() => route.path, () => addTab(route))
watch(visitedTabs, saveTabs, { deep: true })
</script>

<style scoped>
.tags-view {
  position: sticky;
  top: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  margin: -20px -20px 16px;
  padding: 8px 12px;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #E2E8F0);
  gap: 8px;
}

.tags-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: thin;
  flex: 1;
}
.tags-scroll::-webkit-scrollbar { height: 4px; }
.tags-scroll::-webkit-scrollbar-thumb { background: var(--border-color, #E2E8F0); border-radius: 2px; }

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid var(--border-color, #E2E8F0);
  border-radius: 6px;
  background: var(--bg-body, #F8FAFC);
  color: var(--text-secondary, #64748B);
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.tag-item:hover {
  color: var(--primary-color, #4F46E5);
  border-color: var(--primary-glow, #818CF8);
}

.tag-item.active {
  background: var(--sidebar-active-bg, rgba(79, 70, 229, 0.07));
  border-color: var(--primary-color, #4F46E5);
  color: var(--primary-color, #4F46E5);
  font-weight: 600;
}
.tag-item.active .tag-dot { background: var(--primary-color, #4F46E5); }

.tag-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sidebar-text-muted, #94A3B8);
  flex-shrink: 0;
}

.tag-title { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }

.tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  margin-left: 2px;
  color: var(--sidebar-text-muted, #94A3B8);
  transition: all 0.15s;
}
.tag-close:hover {
  background: var(--danger-color, #EF4444);
  color: #fff;
}

.tags-action { flex-shrink: 0; }
.tags-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary, #64748B);
  cursor: pointer;
  transition: all 0.15s;
}
.tags-action-btn:hover {
  background: var(--sidebar-hover-bg, rgba(99, 102, 241, 0.08));
  color: var(--primary-color, #4F46E5);
}
</style>
