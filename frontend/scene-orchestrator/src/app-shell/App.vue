<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  // 初始化深色模式（跟 base.html 保持一致逻辑）
  const stored = localStorage.getItem('darkMode')
  if (stored === 'enabled') {
    document.documentElement.classList.add('dark-mode')
  } else if (stored === 'disabled') {
    document.documentElement.classList.remove('dark-mode')
  } else {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.classList.toggle('dark-mode', prefersDark)
  }
})
</script>

<style>
/* ===== 全局样式重置 ===== */
*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  padding: 0;
  background-color: var(--bg-body);
  color: var(--text-primary);
}

/* ===== 路由过渡动画 ===== */
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

/* ===== 框架级滚动条 ===== */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #CBD5E1;
  border-radius: 3px;
}
.dark-mode ::-webkit-scrollbar-thumb {
  background: #475569;
}
</style>
