<template>
  <div class="app-layout">
    <!-- ========== 顶栏导航 ========== -->
    <header class="app-navbar">
      <div class="navbar-left">
        <button class="navbar-toggle d-md-none" @click="toggleMobileSidebar" aria-label="切换菜单">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <router-link to="/dashboard" class="navbar-brand">
          <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          <span>EasyTesting</span>
        </router-link>
      </div>

      <div class="navbar-right">
        <!-- 深色模式切换 -->
        <button class="theme-btn" @click="toggleDarkMode" :title="isDark ? '浅色模式' : '深色模式'">
          <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <circle cx="12" cy="12" r="5" />
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
          </svg>
        </button>

        <!-- 用户下拉 -->
        <el-dropdown trigger="click" @command="handleUserCommand">
          <button class="user-btn">
            <span class="user-avatar">{{ userInitial }}</span>
            <span class="user-name d-none d-md-inline">{{ userName }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>个人资料
              </el-dropdown-item>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon>账户设置
              </el-dropdown-item>
              <el-dropdown-item divided command="toggleDark">
                <el-icon><Moon /></el-icon>{{ isDark ? '浅色模式' : '深色模式' }}
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- ========== 主内容区 ========== -->
    <div class="app-body">
      <!-- 侧边栏（嵌入式模式：隐藏品牌标识和底部操作栏，偏移 60px 避开导航栏）-->
      <Sidebar ref="sidebarRef" :user-authenticated="isAuthenticated" :embedded="true" />

      <!-- 移动端遮罩 -->
      <transition name="fade">
        <div v-if="mobileSidebarOpen" class="sidebar-overlay" @click="closeMobileSidebar"></div>
      </transition>

      <!-- 内容区 -->
      <main class="app-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="$route.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Sidebar from '../../sidebar/App.vue'
import { logoutApi } from '../../api/auth'

const router = useRouter()

// ============ 状态 ============
const isDark = ref(false)
const mobileSidebarOpen = ref(false)
const sidebarRef = ref(null)

// 从 __INITIAL_STATE__ 读取用户信息
const appState = window.__APP_STATE__ || {}
const isAuthenticated = ref(appState.userAuthenticated === true)
const userName = ref(appState.userName || 'User')

const userInitial = computed(() => userName.value.charAt(0).toUpperCase())

// ============ 深色模式 ============
function applyDarkMode(dark) {
  isDark.value = dark
  if (dark) {
    document.documentElement.classList.add('dark-mode')
    localStorage.setItem('darkMode', 'enabled')
  } else {
    document.documentElement.classList.remove('dark-mode')
    localStorage.setItem('darkMode', 'disabled')
  }
}

function toggleDarkMode() {
  applyDarkMode(!isDark.value)
}

function initDarkMode() {
  const stored = localStorage.getItem('darkMode')
  if (stored === 'enabled') {
    isDark.value = true
    document.documentElement.classList.add('dark-mode')
  } else if (stored === 'disabled') {
    isDark.value = false
    document.documentElement.classList.remove('dark-mode')
  } else {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    applyDarkMode(prefersDark)
  }
}

// ============ 移动端侧边栏 ============
function toggleMobileSidebar() {
  if (!sidebarRef.value) return
  if (sidebarRef.value.isMobileOpen) {
    sidebarRef.value.closeMobile()
    mobileSidebarOpen.value = false
  } else {
    sidebarRef.value.openMobile()
    mobileSidebarOpen.value = true
  }
  document.body.style.overflow = mobileSidebarOpen.value ? 'hidden' : ''
}

function closeMobileSidebar() {
  if (sidebarRef.value) sidebarRef.value.closeMobile()
  mobileSidebarOpen.value = false
  document.body.style.overflow = ''
}

// ============ 用户操作 ============
async function handleUserCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/settings/profile')
      break
    case 'settings':
      router.push('/settings/profile')
      break
    case 'toggleDark':
      toggleDarkMode()
      break
    case 'logout':
      try {
        await logoutApi()
      } catch {
        // 即使 API 失败也执行退出
      }
      window.__APP_STATE__ = window.__APP_STATE__ || {}
      window.__APP_STATE__.userAuthenticated = false
      window.__APP_STATE__.userName = ''
      router.push({ name: 'login' })
      break
  }
}

// ============ 生命周期 ============
let darkModeObserver = null

onMounted(() => {
  initDarkMode()

  // 监听外部深色模式变化
  darkModeObserver = new MutationObserver(() => {
    const newDark = document.documentElement.classList.contains('dark-mode')
    if (newDark !== isDark.value) {
      isDark.value = newDark
    }
  })
  darkModeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })
})

onUnmounted(() => {
  if (darkModeObserver) darkModeObserver.disconnect()
  document.body.style.overflow = ''
})
</script>

<style>
/* ============ 非 scoped：关键布局（保证始终生效）============ */
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 101;
  height: 60px;
}

.app-body {
  display: flex;
  padding-top: 60px;
  flex: 1;
  min-height: 0;
}

.app-content {
  flex: 1;
  margin-left: 220px;
  min-height: calc(100vh - 60px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

@media (max-width: 767.98px) {
  .app-content {
    margin-left: 0;
  }
}
</style>

<style scoped>
/* ============ 布局容器 ============ */
.app-layout {
  background: var(--bg-body);
}

/* ============ 顶栏导航 ============ */
.app-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-navbar, #0F172A);
  backdrop-filter: var(--navbar-blur, none);
  -webkit-backdrop-filter: var(--navbar-blur, none);
  border-bottom: var(--navbar-border, 1px solid var(--sidebar-border));
  box-shadow: var(--navbar-shadow, 0 1px 3px rgba(0, 0, 0, 0.08));
  transition: background 0.3s ease, box-shadow 0.3s ease;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.navbar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: none;
  border: 1px solid var(--navbar-toggle-border, rgba(255,255,255,0.15));
  border-radius: 6px;
  color: var(--navbar-toggle-color, rgba(255,255,255,0.8));
  cursor: pointer;
  transition: all 0.15s;
}
.navbar-toggle:hover {
  background: var(--navbar-toggle-hover-bg, rgba(255,255,255,0.1));
  color: var(--navbar-toggle-hover-color, #fff);
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--navbar-brand-text, #fff);
  font-weight: 700;
  font-size: 1.15rem;
  font-family: var(--font-heading);
}
.navbar-brand .brand-icon {
  color: var(--sidebar-icon-active, #3B82F6);
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.theme-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--theme-btn-border, rgba(255,255,255,0.12));
  color: var(--theme-btn-color, rgba(255,255,255,0.7));
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1.1rem;
}
.theme-btn:hover {
  color: var(--theme-btn-hover-color, #fff);
  background: var(--theme-btn-hover-bg, rgba(255,255,255,0.1));
  border-color: var(--theme-btn-hover-border, rgba(255,255,255,0.25));
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: none;
  border: none;
  color: var(--user-btn-color, rgba(255,255,255,0.85));
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s;
  font-size: 0.875rem;
}
.user-btn:hover {
  background: var(--user-btn-hover-bg, rgba(255,255,255,0.08));
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--primary-color, #1E40AF);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.85rem;
  flex-shrink: 0;
}

/* ============ 主体 ============ */
/* display/flex/padding-top 定义在非 scoped 中 */

/* ============ 移动端遮罩 ============ */
.sidebar-overlay {
  display: none;
}

/* ============ 路由过渡 ============ */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ============ 响应式 ============ */
@media (max-width: 767.98px) {
  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 1039;
    background: rgba(0, 0, 0, 0.5);
  }
  .app-navbar {
    padding: 0 12px;
  }
  .navbar-brand span {
    display: none;
  }
}
</style>
