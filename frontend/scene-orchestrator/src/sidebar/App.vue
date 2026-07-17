<template>
  <aside class="sidebar" :class="{ 'sidebar--show': isMobileOpen, 'sidebar--embedded': props.embedded }">
    <!-- ========== 品牌标识（仅独立模式）========== -->
    <div v-if="!props.embedded" class="sidebar-brand">
      <a href="/dashboard/" class="brand-link" @click="closeMobile">
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        <span class="brand-text">EasyTesting</span>
      </a>
    </div>

    <!-- ========== 搜索框 ========== -->
    <div class="sidebar-search">
      <div class="search-wrapper">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          ref="searchInput"
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="搜索菜单..."
          @keyup.enter="onSearchInput"
        />
        <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
        <button class="search-submit" title="搜索菜单" @click="onSearchInput">搜索</button>
      </div>
    </div>

    <!-- ========== 菜单列表 ========== -->
    <nav class="sidebar-nav">
      <div
        v-for="group in visibleGroups"
        :key="group.id"
        class="nav-group"
      >
        <!-- 分组标题（可折叠） -->
        <button
          class="group-toggle"
          :class="{ 'group-toggle--open': expandedGroups[group.id] }"
          @click="toggleGroup(group.id)"
          :aria-expanded="expandedGroups[group.id]"
        >
          <svg
            class="group-toggle-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="16"
            height="16"
            v-html="groupIconPaths[group.icon] || groupIconPaths.Calendar"
          ></svg>
          <span class="group-toggle-text">{{ group.label }}</span>
          <svg
            class="group-chevron"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="14"
            height="14"
          >
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>

        <!-- 分组内容（可折叠） -->
        <div
          ref="groupContents"
          class="group-content"
          :class="{ 'group-content--open': expandedGroups[group.id] }"
          :style="{ maxHeight: expandedGroups[group.id] ? getGroupHeight(group.id) + 'px' : '0' }"
        >
          <div class="group-inner" :ref="el => setGroupInnerRef(group.id, el)">
            <template v-for="child in getFilteredChildren(group)" :key="child.label + (child.href || '')">
              <!-- 分隔标题 -->
              <div v-if="child.type === 'section'" class="section-header">
                <span>{{ child.label }}</span>
              </div>
              <!-- 导航链接 -->
              <a
                v-else-if="child.type === 'link'"
                :href="child.href"
                :target="child.external ? '_blank' : '_self'"
                :rel="child.external ? 'noopener' : undefined"
                class="nav-link"
                :class="{ 'nav-link--active': isActive(child), 'nav-link--searched': searchQuery && !child._hidden }"
                @click="handleNavClick(child, $event)"
              >
                <svg
                  class="nav-link-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  width="14"
                  height="14"
                  v-html="navIconPaths[child.icon] || navIconPaths.Speedometer"
                ></svg>
                <span class="nav-link-text">{{ child.label }}</span>
                <svg
                  v-if="child.external"
                  class="nav-link-external"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  width="10"
                  height="10"
                >
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" x2="21" y1="14" y2="3" />
                </svg>
              </a>
            </template>

            <!-- 搜索无结果 -->
            <div v-if="getFilteredChildren(group).length === 0 && searchQuery" class="search-no-results">
              无匹配菜单项
            </div>
          </div>
        </div>
      </div>

      <!-- 全部无结果 -->
      <div v-if="visibleGroups.length === 0 && searchQuery" class="search-no-results overall">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <p>没有匹配的菜单项</p>
      </div>
    </nav>

    <!-- ========== 底部操作栏（仅独立模式）========== -->
    <div v-if="!props.embedded" class="sidebar-footer">
      <div class="footer-divider"></div>
      <div class="footer-actions">
        <!-- 深色模式切换 -->
        <button class="footer-btn" @click="toggleDarkMode" title="切换深色/浅色模式">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <path v-if="isDark" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            <template v-else>
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </template>
          </svg>
          <span class="footer-btn-text">{{ isDark ? '浅色模式' : '深色模式' }}</span>
        </button>
        <!-- 全部展开/折叠 -->
        <button class="footer-btn" @click="toggleAllGroups" :title="allExpanded ? '全部折叠' : '全部展开'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <template v-if="allExpanded">
              <path d="m18 16-6-6-6 6" />
              <path d="M6 5h12" />
            </template>
            <template v-else>
              <path d="m6 9 6 6 6-6" />
              <path d="M6 5h12" />
            </template>
          </svg>
          <span class="footer-btn-text">{{ allExpanded ? '全部折叠' : '全部展开' }}</span>
        </button>
      </div>
    </div>
  </aside>

  <!-- 移动端遮罩 -->
  <transition name="fade">
    <div v-if="isMobileOpen" class="sidebar-backdrop" @click="closeMobile"></div>
  </transition>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { getMenuData } from './menuData.js'

// ============ Props ============
const props = defineProps({
  /** 用户已登录状态 — 由父组件传入（嵌入式模式），
   *  不传时回退到 #sidebar-app dataset 读取（独立模式） */
  userAuthenticated: {
    type: Boolean,
    default: undefined,
  },
  /** 是否为嵌入式模式（在 MainLayout 中使用）。
   *  嵌入式模式下：隐藏品牌标识、隐藏底部操作栏、top 偏移 60px */
  embedded: {
    type: Boolean,
    default: false,
  },
})

// ============ 状态 ============
const searchQuery = ref('')
const searchInput = ref(null)
const expandedGroups = reactive({})
const groupInnerRefs = reactive({})
const groupHeights = reactive({})
const isMobileOpen = ref(false)
const isDark = ref(false)

// ============ 菜单数据 ============
// 优先使用 prop，否则从 data 属性同步读取登录状态
const isAuthenticated = ref(
  props.userAuthenticated !== undefined
    ? props.userAuthenticated
    : document.getElementById('sidebar-app')?.dataset?.userAuthenticated === 'true'
)
const menuGroups = computed(() => getMenuData({ isAuthenticated: isAuthenticated.value }))

// 可见分组（搜索时展开所有，否则按默认状态）
const visibleGroups = computed(() => {
  if (searchQuery.value) {
    // 搜索模式：展开所有有结果的分组
    return menuGroups.value.filter(g => {
      const children = getFilteredChildren(g)
      return children.length > 0
    })
  }
  return menuGroups.value
})

// 全部展开/折叠状态
const allExpanded = computed(() => {
  const groups = menuGroups.value
  if (groups.length === 0) return false
  return groups.every(g => expandedGroups[g.id])
})

// ============ 图标路径 ============
// 使用内联 SVG 路径，零外部依赖
const groupIconPaths = {
  Calendar: '<rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />',
  Sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3" /><circle cx="4" cy="14" r="2" /><circle cx="12" cy="11" r="2" /><circle cx="20" cy="16" r="2" />',
  Monitor: '<rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8M12 17v4" />',
}

const navIconPaths = {
  Speedometer: '<path d="M12 2a10 10 0 1 0 10 10 10 10 0 0 0-10-10Z" /><path d="M12 6v6l4 2" />',
  FolderOpened: '<path d="m9 17-5-5 5-5" /><path d="M20 17V7a2 2 0 0 0-2-2H4" /><path d="m15 17 5-5-5-5" />',
  Setting: '<circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />',
  Connection: '<path d="M5 3v4M19 3v4M3 7h18" /><rect x="4" y="11" width="16" height="10" rx="2" /><circle cx="12" cy="16" r="1" />',
  Share: '<circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.59 13.51 6.83 3.98M15.41 6.51l-6.82 3.98" />',
  ClipboardData: '<rect x="8" y="2" width="8" height="4" rx="1" /><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><path d="M8 13h2v5H8zM12 10h2v8h-2zM16 16h2v2h-2z" />',
  FolderFilled: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" fill="currentColor" opacity="0.2"/><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />',
  BriefcaseFilled: '<rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />',
  Collection: '<path d="M12 2H2v10l10 10 10-10L12 2z" /><path d="M2 12h20" /><path d="M12 2v20" />',
  PlayCircleFilled: '<circle cx="12" cy="12" r="10" /><polygon points="10 8 16 12 10 16 10 8" fill="currentColor" />',
  ReplyAllFilled: '<path d="m7 17-5-5 5-5" /><path d="m17 17 5-5-5-5" /><path d="M12 3 7 12l5 9" />',
  LightningChargeFilled: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />',
  InboxFilled: '<path d="M22 12h-6l-2 3H10l-2-3H2" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />',
  ClockHistory: '<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />',
  Rulers: '<path d="M15 3v18M9 3v2M9 9v2M9 15v2M21 3H3v18h18V3z" />',
  ChatLeftTextFilled: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M8 9h8M8 13h6" />',
  CpuFilled: '<rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" />',
  FileEarmarkArrowUpFilled: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><path d="M12 12v6M15 15l-3-3-3 3" />',
  ClockFilled: '<circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />',
  UserFilled: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />',
  Lock: '<rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />',
  Message: '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" />',
  Operation: '<circle cx="12" cy="12" r="3" /><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />',
  Laptop: '<path d="M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0-4 2H8l-4-2m16 0 2 4H2l2-4" />',
  Terminal: '<polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" />',
  DataLine: '<path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" />',
}

// ============ 方法 ============

/** 获取分组内过滤后的子项（搜索时） */
function getFilteredChildren(group) {
  if (!searchQuery.value) return group.children || []
  const q = searchQuery.value.toLowerCase()
  return (group.children || []).filter(child => {
    if (child.type === 'section') {
      // section 只保留如果其后的 link 有匹配
      return true
    }
    if (child.type === 'link') {
      return child.label.toLowerCase().includes(q)
    }
    return false
  })
}

/** 计算搜索模式下每个分组展开后的高度 */
function setGroupInnerRef(groupId, el) {
  if (el) {
    groupInnerRefs[groupId] = el
    groupHeights[groupId] = el.scrollHeight
  }
}

function getGroupHeight(groupId) {
  return groupHeights[groupId] || 400
}

// 路由变化计数器 — 驱动 isActive 响应式重新计算
const routeKey = ref(0)

/** 判断菜单项是否激活 */
function isActive(item) {
  if (item.type !== 'link') return false
  // 引用 routeKey 使此函数响应式重新执行
  void routeKey.value
  const path = window.location.pathname
  const hash = window.location.hash

  // Django 页面路径匹配
  if (item.matchPaths) {
    for (const p of item.matchPaths) {
      if (path.includes(p)) return true
    }
  }

  // Vue SPA hash 匹配
  if (item.matchBases && item.matchHashes) {
    const onBase = item.matchBases.some(bp => path.includes(bp))
    if (onBase) {
      for (const h of item.matchHashes) {
        if (hash.includes(h)) return true
      }
    }
  }

  return false
}

/** 判断任何子项是否激活（用于分组高亮） */
function isGroupActive(group) {
  if (!group.children) return false
  return group.children.some(child => child.type === 'link' && isActive(child))
}

/** 切换分组展开/折叠 */
function toggleGroup(id) {
  expandedGroups[id] = !expandedGroups[id]
  // 重新计算高度
  if (expandedGroups[id]) {
    requestAnimationFrame(() => {
      const inner = groupInnerRefs[id]
      if (inner) {
        groupHeights[id] = inner.scrollHeight
      }
    })
  }
}

/** 全部展开/折叠 */
function toggleAllGroups() {
  const newVal = !allExpanded.value
  menuGroups.value.forEach(g => {
    expandedGroups[g.id] = newVal
  })
  // 展开后重新计算高度
  if (newVal) {
    requestAnimationFrame(() => {
      menuGroups.value.forEach(g => {
        const inner = groupInnerRefs[g.id]
        if (inner) {
          groupHeights[g.id] = inner.scrollHeight
        }
      })
    })
  }
}

/** 导航点击处理 —— 优化同基础路径内的 hash 路由切换，避免整页刷新 */
function handleNavClick(item, event) {
  if (item.external) return // 浏览器自动在新标签页打开
  closeMobile()

  // 判断目标链接是否与当前页面同基础路径 + hash 路由
  // 如 /test-suites-vue/#/test-suites → /test-suites-vue/#/test-runs
  // 这种情况只需更新 hash，无需整页刷新
  try {
    const targetUrl = new URL(item.href, window.location.origin)
    const currentPath = window.location.pathname.replace(/\/+$/, '')
    const targetPath = targetUrl.pathname.replace(/\/+$/, '')

    if (currentPath === targetPath && targetUrl.hash) {
      event.preventDefault()
      if (targetUrl.hash !== window.location.hash) {
        window.location.hash = targetUrl.hash
        // 浏览器设置 location.hash 会自动触发 hashchange 事件
      }
      return
    }
  } catch (e) {
    // URL 解析异常时回退到浏览器默认导航
  }
  // 不同路径：走浏览器默认整页导航（Django 路由）
}

/** 搜索输入 */
function onSearchInput() {
  // 搜索时自动展开所有匹配的分组
  if (searchQuery.value) {
    menuGroups.value.forEach(g => {
      expandedGroups[g.id] = true
    })
  }
}

/** 深色模式切换 */
function toggleDarkMode() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark-mode', isDark.value)
  localStorage.setItem('darkMode', isDark.value ? 'enabled' : 'disabled')
  // 同步更新导航栏图标
  updateNavbarThemeIcon(isDark.value)
}

function updateNavbarThemeIcon(dark) {
  const icon = document.getElementById('themeToggleIcon')
  if (icon) icon.className = dark ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill'
  const label = document.getElementById('darkModeLabel')
  if (label) label.textContent = dark ? '浅色模式' : '深色模式'
  const dropdownIcon = document.querySelector('#darkModeToggle i')
  if (dropdownIcon) dropdownIcon.className = dark ? 'bi bi-sun me-2' : 'bi bi-moon-stars me-2'
}

/** 获取初始深色模式状态 */
function initDarkMode() {
  const stored = localStorage.getItem('darkMode')
  if (stored === 'enabled') {
    isDark.value = true
  } else if (stored === 'disabled') {
    isDark.value = false
  } else {
    // 跟随系统
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  // 确保文档 class 与状态一致
  document.documentElement.classList.toggle('dark-mode', isDark.value)
  updateNavbarThemeIcon(isDark.value)
}

/** 移动端关闭 */
function closeMobile() {
  isMobileOpen.value = false
  document.body.style.overflow = ''
}

function openMobile() {
  isMobileOpen.value = true
  document.body.style.overflow = 'hidden'
}

/** 更新激活状态 */
function updateActiveState() {
  routeKey.value++
}

// ============ 暴露方法给父组件 ============
defineExpose({ openMobile, closeMobile, isMobileOpen })

// ============ 生命周期 ============
let resizeHandler = null
let hashChangeHandler = null
let popStateHandler = null
let darkModeObserver = null

onMounted(() => {
  // 初始化深色模式
  initDarkMode()

  // 初始化展开状态（根据当前路径）
  menuGroups.value.forEach(g => {
    expandedGroups[g.id] = g.defaultExpanded || isGroupActive(g)
    if (searchQuery.value) expandedGroups[g.id] = true
  })

  // 监听 hash 变化更新激活状态
  hashChangeHandler = () => updateActiveState()
  popStateHandler = () => updateActiveState()
  window.addEventListener('hashchange', hashChangeHandler)
  window.addEventListener('popstate', popStateHandler)

  // 窗口 resize 时关闭移动端侧边栏
  resizeHandler = () => {
    if (window.innerWidth > 767.98 && isMobileOpen.value) {
      closeMobile()
    }
  }
  window.addEventListener('resize', resizeHandler)

  // 观察 dark-mode class 变化（外部切换时同步）
  darkModeObserver = new MutationObserver(() => {
    const newDark = document.documentElement.classList.contains('dark-mode')
    if (newDark !== isDark.value) {
      isDark.value = newDark
      updateNavbarThemeIcon(newDark)
    }
  })
  darkModeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })

  // 移动端侧栏触发的汉堡按钮（navbar-toggler）
  const toggler = document.querySelector('.navbar-toggler')
  if (toggler) {
    toggler.addEventListener('click', (e) => {
      e.preventDefault()
      if (isMobileOpen.value) closeMobile()
      else openMobile()
    })
  }
})

onUnmounted(() => {
  if (hashChangeHandler) window.removeEventListener('hashchange', hashChangeHandler)
  if (popStateHandler) window.removeEventListener('popstate', popStateHandler)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (darkModeObserver) darkModeObserver.disconnect()
})
</script>

<style>
/* ============ 非 scoped：关键布局（保证始终生效）============ */
.sidebar {
  width: 220px;
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
}
.sidebar--embedded {
  top: 60px;
  z-index: 99;
  height: calc(100vh - 60px);
}
</style>

<style scoped>
/* ============ CSS 变量 (局部覆盖) ============ */
.sidebar {
  --sidebar-width: 220px;
  --sidebar-brand-h: 56px;
  --sidebar-search-h: 42px;
  --sidebar-footer-h: 48px;
  --nav-link-height: 34px;
}

/* ============ 主容器（视觉属性）============ */
.sidebar {
  background: var(--bg-sidebar);
  border-right: 1px solid var(--sidebar-border);
  box-shadow: var(--sidebar-shadow, none);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease;
}

/* ============ 品牌标识 ============ */
.sidebar-brand {
  height: var(--sidebar-brand-h);
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--sidebar-border);
  flex-shrink: 0;
}
.brand-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--sidebar-text-active);
  font-weight: 700;
  font-size: 1.15rem;
  font-family: var(--font-heading);
}
.brand-icon {
  width: 22px;
  height: 22px;
  color: var(--sidebar-icon-active);
  flex-shrink: 0;
}
.brand-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ============ 搜索框 ============ */
.sidebar-search {
  flex-shrink: 0;
  padding: 6px 10px;
  border-bottom: 1px solid var(--sidebar-border);
}
.search-wrapper {
  display: flex;
  align-items: center;
  background: var(--sidebar-hover-bg);
  border-radius: 6px;
  padding: 0 8px;
  border: 1px solid transparent;
  transition: border-color 0.2s;
}
.search-wrapper:focus-within {
  border-color: var(--primary-color);
  background: var(--bg-sidebar);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.08);
}
.search-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  color: var(--sidebar-text-muted);
}
.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 5px 6px;
  font-size: 0.75rem;
  color: var(--sidebar-text);
  outline: none;
  min-width: 0;
}
.search-input::placeholder {
  color: var(--sidebar-text-muted);
}
.search-clear {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--sidebar-text-muted);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  transition: color 0.15s;
}
.search-clear:hover {
  color: var(--sidebar-text);
}
.search-submit {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color, #3b82f6);
  border: none;
  color: #fff;
  font-size: 0.7rem;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 4px;
  transition: opacity 0.15s;
}
.search-submit:hover {
  opacity: 0.9;
}

/* ============ 导航菜单 ============ */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 0;
  scrollbar-width: thin;
  scrollbar-color: var(--sidebar-border, rgba(0,0,0,0.08)) transparent;
}

/* 分组 */
.nav-group + .nav-group {
  border-top: 1px solid var(--sidebar-border);
  margin-top: 3px;
  padding-top: 3px;
}

/* 分组按钮 */
.group-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 7px 14px;
  background: none;
  border: none;
  color: var(--sidebar-text);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, color 0.15s;
  user-select: none;
}
.group-toggle:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-text-active);
}
.group-toggle-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
}
.group-toggle-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.group-chevron {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  color: var(--sidebar-text-muted);
  transition: transform 0.25s ease;
}
.group-toggle--open .group-chevron {
  transform: rotate(90deg);
}

/* 分组内容（可折叠） */
.group-content {
  overflow: hidden;
  transition: max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  max-height: 0;
}
.group-inner {
  padding: 1px 0 3px;
}

/* 分隔标题 */
.section-header {
  padding: 6px 14px 3px;
  margin-top: 3px;
  border-top: 1px solid var(--sidebar-border);
}
.section-header span {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--sidebar-text-muted);
  font-weight: 600;
}

/* 导航链接 */
.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px 5px 14px;
  margin: 1px 6px;
  border-radius: 4px;
  text-decoration: none;
  color: var(--sidebar-text);
  font-size: 0.78rem;
  transition: all 0.15s ease;
  cursor: pointer;
  position: relative;
}
.nav-link:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-text-active);
}
.nav-link:hover .nav-link-icon {
  color: var(--sidebar-text-active);
}
.nav-link--active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-text-active);
  font-weight: 500;
}
.nav-link--active::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 0 3px 3px 0;
  background: var(--sidebar-icon-active, #3B82F6);
  box-shadow: 0 0 6px rgba(59, 130, 246, 0.3);
}
.nav-link--active .nav-link-icon {
  color: var(--sidebar-icon-active);
  filter: drop-shadow(0 0 3px rgba(59, 130, 246, 0.25));
}
.nav-link-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  color: var(--sidebar-icon);
  transition: color 0.15s;
}
.nav-link-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-link-external {
  flex-shrink: 0;
  color: var(--sidebar-text-muted);
  opacity: 0.6;
}

/* 搜索无结果 */
.search-no-results {
  padding: 16px 20px;
  font-size: 0.8rem;
  color: var(--sidebar-text-muted);
  text-align: center;
}
.search-no-results.overall {
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.search-no-results.overall p {
  margin: 0;
  font-size: 0.85rem;
}
.search-no-results.overall svg {
  opacity: 0.4;
}

/* ============ 底部操作栏 ============ */
.sidebar-footer {
  flex-shrink: 0;
  border-top: none;
}
.footer-divider {
  height: 1px;
  background: var(--sidebar-border);
  margin: 0 12px;
}
.footer-actions {
  display: flex;
  padding: 6px 10px;
  gap: 4px;
}
.footer-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 5px 6px;
  background: none;
  border: none;
  border-radius: 4px;
  color: var(--sidebar-text);
  font-size: 0.72rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.footer-btn:hover {
  background: var(--sidebar-hover-bg);
  color: var(--sidebar-text-active);
}
.footer-btn-text {
  white-space: nowrap;
}

/* ============ 移动端遮罩 ============ */
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 99;
  background: rgba(0, 0, 0, 0.5);
}

/* ============ 过渡动画 ============ */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ============ 嵌入式模式 ============ */
/* top/z-index/height 定义在非 scoped 的 <style> 块中 */
.sidebar--embedded .sidebar-nav {
  padding-top: 4px; /* 补偿被移除的品牌区 */
}

/* ============ 响应式 - 移动端 ============ */
@media (max-width: 767.98px) {
  .sidebar {
    transform: translateX(-100%);
    z-index: 1040;
    box-shadow: none;
  }
  .sidebar.sidebar--show {
    transform: translateX(0);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
  }
  .sidebar--embedded {
    top: 60px;
    z-index: 1040; /* 移动端高于遮罩 */
  }
}

/* ============ 深色模式适配 ============ */
:global(.dark-mode) .sidebar {
  box-shadow: none;
}
:global(.dark-mode) .sidebar-backdrop {
  background: rgba(0, 0, 0, 0.6);
}
</style>
