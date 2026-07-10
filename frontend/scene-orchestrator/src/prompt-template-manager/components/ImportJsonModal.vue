<template>
  <el-dialog
    v-model="store.importModalVisible"
    title="导入JSON"
    width="640px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <div class="import-hint">
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          请输入JSON数组，每个元素为一个模板对象：
          <code style="font-size:13px;background:#f0f2f5;padding:2px 6px;border-radius:4px">
            {"name": "模板名", "description": "...", "template_text": "...", "is_enabled": true}
          </code>
        </template>
      </el-alert>
    </div>

    <el-input
      v-model="store.importJsonContent"
      type="textarea"
      :rows="14"
      placeholder='[
  {
    "name": "通用测试用例生成模板",
    "description": "适用于大多数接口的测试用例生成",
    "template_text": "基于以下接口信息生成测试用例：\n请求方法：{method}\n请求URL：{url}\n...",
    "is_enabled": true
  }
]'
      class="import-textarea"
    />

    <template #footer>
      <el-button @click="store.importModalVisible = false">取消</el-button>
      <el-button type="primary" :loading="store.importing" @click="store.importJson()">
        导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { usePromptTemplateStore } from '../stores/promptTemplate.js'

const store = usePromptTemplateStore()
</script>

<style scoped>
.import-hint {
  margin-bottom: 16px;
}

.import-textarea :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.6;
}
</style>
