import { createRouter, createWebHashHistory } from 'vue-router'
import MockDataList from './views/MockDataList.vue'
import MockDataForm from './views/MockDataForm.vue'

const routes = [
  { path: '/', redirect: '/mock-data' },
  { path: '/mock-data', name: 'mdList', component: MockDataList },
  { path: '/mock-data/create', name: 'mdCreate', component: MockDataForm },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
