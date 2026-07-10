<template>
  <div class="card">
    <div class="card-header">
      <span>快捷操作</span>
    </div>
    <div class="card-body p-0">
      <div class="list-group list-group-flush">
        <a
          v-for="item in actions"
          :key="item.label"
          :href="item.link"
          class="list-group-item list-group-item-action d-flex align-items-center"
        >
          <el-icon :class="`text-${item.color} me-3`" size="20">
            <component :is="item.icon" />
          </el-icon>
          <div>
            <div class="fw-medium">{{ item.label }}</div>
            <div class="text-muted small">{{ item.desc }}</div>
          </div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { FolderAdd, DocumentAdd, Collection, Setting } from '@element-plus/icons-vue'

const actions = [
  { label: '创建项目',   desc: '添加一个新的项目',     link: '/projects/create/',              icon: FolderAdd,    color: 'primary' },
  { label: '创建用例',   desc: '新增一个测试用例',     link: '/test-cases-vue/#/test-cases/create', icon: DocumentAdd, color: 'success' },
  { label: '创建测试套件', desc: '组织测试套件',        link: '/test-suites-vue/#/test-suites/create', icon: Collection,  color: 'info' },
  { label: '新增配置环境', desc: '配置环境信息',        link: '/environments/create/',          icon: Setting,      color: 'warning' },
]
</script>
