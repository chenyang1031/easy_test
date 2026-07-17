<template>
  <div class="ui-content-tabs">
    <el-tabs v-model="activeTab" @tab-click="onTabChange">
      <el-tab-pane label="页面管理" name="pages">
        <UiPageManager :project-id="projectId" :module-id="moduleId" v-if="activeTab === 'pages'" />
      </el-tab-pane>
      <el-tab-pane label="元素管理" name="elements">
        <UiElementManager :project-id="projectId" :module-id="moduleId" v-if="activeTab === 'elements'" />
      </el-tab-pane>
      <el-tab-pane label="测试用例" name="cases">
        <UiTestCaseManager :project-id="projectId" :module-id="moduleId" v-if="activeTab === 'cases'" @refresh="$emit('refresh')" />
      </el-tab-pane>
      <el-tab-pane label="执行记录" name="executions">
        <UiExecutionManager :project-id="projectId" v-if="activeTab === 'executions'" />
      </el-tab-pane>
      <el-tab-pane label="环境配置" name="env">
        <UiEnvManager :project-id="projectId" v-if="activeTab === 'env'" />
      </el-tab-pane>
      <el-tab-pane label="公共数据" name="data">
        <UiPublicDataManager :project-id="projectId" v-if="activeTab === 'data'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UiPageManager from './UiPageManager.vue'
import UiElementManager from './UiElementManager.vue'
import UiTestCaseManager from './UiTestCaseManager.vue'
import UiExecutionManager from './UiExecutionManager.vue'
import UiEnvManager from './UiEnvManager.vue'
import UiPublicDataManager from './UiPublicDataManager.vue'

const props = defineProps({ projectId: [Number, String], moduleId: [Number, String] })
defineEmits(['refresh'])

const activeTab = ref('pages')
function onTabChange() {}
</script>

<style scoped>
.ui-content-tabs { height: 100%; }
</style>
