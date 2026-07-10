<template>
  <el-dialog
    v-model="store.importModalVisible"
    title="导入规则（JSON）"
    width="640px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <div class="import-hint">
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          请输入JSON数组，每个元素为一个规则对象：
          <code style="font-size:13px;background:#f0f2f5;padding:2px 6px;border-radius:4px">
            {"name": "规则名", "category": "param_validate", "priority": "high", "rule_content": "一行一条规则", "is_enabled": true}
          </code>
        </template>
      </el-alert>
    </div>
    <el-input
      v-model="store.importJsonContent"
      type="textarea"
      :rows="16"
      placeholder='[
  {
    "name": "参数校验-必填参数检查",
    "description": "检查接口必填参数",
    "category": "param_validate",
    "priority": "high",
    "rule_content": "必填参数不能为空\n参数格式校验",
    "is_enabled": true
  }
]'
      class="import-textarea"
    />
    <template #footer>
      <el-button @click="store.importModalVisible = false">取消</el-button>
      <el-button type="primary" :loading="store.importing" @click="store.importJson()">导入</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { useRuleStore } from '../stores/rule.js'
const store = useRuleStore()
</script>

<style scoped>
.import-hint { margin-bottom: 16px; }
.import-textarea :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 14px; line-height: 1.6;
}
</style>
