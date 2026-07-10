<template>
  <div class="json-editor">
    <div class="editor-toolbar">
      <el-button size="small" @click="formatJson">格式化</el-button>
      <el-button size="small" :type="viewMode==='code'?'primary':''" @click="viewMode='code'">代码视图</el-button>
      <el-button size="small" :type="viewMode==='tree'?'primary':''" @click="viewMode='tree'">树形视图</el-button>
      <span v-if="jsonError" class="validation-tag error">JSON格式错误</span>
      <span v-else-if="modelValue && viewMode==='code'" class="validation-tag ok">JSON有效</span>
      <span v-if="varCount > 0" class="validation-tag var">变量 {{ varCount }}</span>
    </div>
    <div v-if="viewMode==='code'">
      <div class="code-area" ref="codeRef">
        <el-input
          :model-value="modelValue"
          @update:model-value="$emit('update:modelValue',$event)"
          type="textarea"
          :rows="8"
          :placeholder="placeholder"
          class="font-mono"
          @input="checkJson"
        />
      </div>
      <!-- 高亮预览 -->
      <div class="var-list" v-if="variables.length > 0">
        <span class="var-list-title">检测到变量：</span>
        <el-tag v-for="v in variables" :key="v" size="small" type="warning" effect="plain" style="margin:2px 4px">{{ v }}</el-tag>
      </div>
    </div>
    <div v-else class="tree-view">
      <div v-if="parsedTree" class="tree-content">
        <JsonTreeNode
          v-for="(val,key) in parsedTree"
          :key="key"
          :name="String(key)"
          :value="val"
          :depth="0"
        />
      </div>
      <el-empty v-else description="无数据或JSON格式错误" :image-size="40" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import JsonTreeNode from './JsonTreeNode.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '{}' },
})
const emit = defineEmits(['update:modelValue'])

const viewMode = ref('code')
const jsonError = ref(false)
const codeRef = ref(null)

// 校验JSON
function checkJson() {
  try {
    JSON.parse(props.modelValue || '{}')
    jsonError.value = false
  } catch { jsonError.value = true }
}

// 解析变量 {{xxx}}
const variables = computed(() => {
  const matches = (props.modelValue || '').match(/\{\{([^{}]+)\}\}/g)
  if (!matches) return []
  return [...new Set(matches)]
})
const varCount = computed(() => variables.value.length)

const parsedTree = computed(() => {
  try { return JSON.parse(props.modelValue || '{}') }
  catch { return null }
})

function formatJson() {
  try {
    const obj = JSON.parse(props.modelValue || '{}')
    emit('update:modelValue', JSON.stringify(obj, null, 2))
    jsonError.value = false
  } catch { jsonError.value = true }
}
</script>

<style scoped>
.editor-toolbar { display: flex; gap: 6px; margin-bottom: 8px; align-items: center; }
.font-mono :deep(textarea) { font-family: 'Consolas','Courier New',monospace; font-size: 13px; }
.validation-tag { font-size: 12px; padding: 2px 8px; border-radius: 4px; margin-left: auto; }
.validation-tag.error { color: #f56c6c; background: #fef0f0; }
.validation-tag.ok { color: #67c23a; background: #f0f9eb; }
.validation-tag.var { color: #e6a23c; background: #fdf6ec; }
.var-list { padding: 8px 0; }
.var-list-title { font-size: 12px; color: #909399; margin-right: 4px; }
.tree-view { border: 1px solid #dcdfe6; border-radius: 6px; padding: 12px; min-height: 100px; background: #fafafa; }
.tree-content { font-family: 'Consolas','Courier New',monospace; font-size: 13px; }
</style>
