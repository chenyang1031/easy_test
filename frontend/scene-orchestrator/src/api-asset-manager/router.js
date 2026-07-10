import { createRouter, createWebHashHistory } from 'vue-router'
import AssetList from './views/AssetList.vue'
import AssetFormPage from './views/AssetFormPage.vue'

const routes = [
  { path: '/', name: 'list', component: AssetList },
  { path: '/create', name: 'create', component: AssetFormPage },
  { path: '/edit/:id', name: 'edit', component: AssetFormPage, props: true },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
