import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router.js'

const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Pinia — 所有 store 共享同一个实例
app.use(createPinia())

// Element Plus — 中文语言包
app.use(ElementPlus, { locale: zhCn })

// Vue Router — 统一 hash 路由
app.use(router)

// 将 Django 注入的 __INITIAL_STATE__ 暴露为全局，方便组件读取
window.__APP_STATE__ = window.__INITIAL_STATE__ || {}

app.mount('#app')
