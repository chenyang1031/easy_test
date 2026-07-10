/**
 * 侧边栏 Vue 应用入口
 *
 * 独立于页面主 Vue 应用，通过 #sidebar-app 挂载。
 * 使用内联 SVG 图标，不依赖 Element Plus 组件库，
 * 避免与 Django 模板页面的 Bootstrap 样式冲突。
 */
import { createApp } from 'vue'
import App from './App.vue'

const mountEl = document.getElementById('sidebar-app')

if (mountEl) {
  const app = createApp(App)
  app.mount(mountEl)
} else {
  console.warn('[Sidebar] #sidebar-app 挂载点不存在，跳过侧边栏初始化')
}
