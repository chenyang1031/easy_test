<template>
  <el-dialog
    v-model="store.modalVisible"
    :title="store.modalTitle"
    width="720px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="store.formData"
      label-width="90px"
      label-position="top"
      size="default"
    >
      <el-form-item label="模板名称" required>
        <el-input
          v-model="store.formData.name"
          placeholder="请输入模板名称"
          maxlength="100"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="描述">
        <el-input
          v-model="store.formData.description"
          type="textarea"
          :rows="2"
          placeholder="简要描述模板用途"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="分类">
        <el-select v-model="store.formData.category" style="width:100%">
          <el-option label="用例生成" value="test_case_gen" />
          <el-option label="API生成" value="api_gen" />
        </el-select>
      </el-form-item>

      <el-form-item label="模板内容" required>
        <div class="template-editor-wrap">
          <div class="template-toolbar">
            <span class="toolbar-hint">可用变量：</span>
            <el-button
              v-for="varName in availableVariables"
              :key="varName"
              size="small"
              plain
              @click="insertVariable(varName)"
            >
              {{ '{' + varName + '}' }}
            </el-button>
          </div>
          <el-input
            v-model="store.formData.template_text"
            type="textarea"
            :rows="14"
            placeholder="基于以下接口信息和测试规则，生成测试用例：

【接口信息】
请求方法：{method}
请求URL：{url}
请求头：{headers}
请求体结构：{body_schema}

【测试规则】
{rules}

【生成要求】
1. 每个用例包含：name, request_method, request_url, request_headers, request_body, expected_status_code, validation_rules
2. 覆盖所有规则类别
3. 返回JSON数组"
            class="template-textarea"
          />
          <div class="variable-preview" v-if="detectedVariables.length">
            <span class="detected-label">检测到变量：</span>
            <el-tag
              v-for="v in detectedVariables"
              :key="v"
              size="small"
              type="info"
              effect="plain"
              style="margin-right: 4px; margin-bottom: 2px"
            >
              {{ '{' + v + '}' }}
            </el-tag>
          </div>
        </div>
      </el-form-item>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item>
            <el-checkbox v-model="store.formData.is_default" label="设为默认模板" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item>
            <el-checkbox v-model="store.formData.is_enabled" label="启用" />
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <template #footer>
      <el-button @click="store.modalVisible = false">取消</el-button>
      <el-button type="primary" :loading="store.saving" @click="store.saveTemplate()">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { usePromptTemplateStore } from '../stores/promptTemplate.js'

const store = usePromptTemplateStore()

const availableVariables = ['method', 'url', 'headers', 'body_schema', 'rules', 'description', 'response_schema']

const detectedVariables = computed(() => {
  const text = store.formData.template_text || ''
  const matches = text.match(/\{([^}]+)\}/g) || []
  return matches.map(m => m.slice(1, -1))
})

function insertVariable(varName) {
  store.formData.template_text = (store.formData.template_text || '') + `{${varName}}`
}
</script>

<style scoped>
.template-editor-wrap {
  width: 100%;
}

.template-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.toolbar-hint {
  font-size: 14px;
  color: #909399;
  margin-right: 4px;
}

.template-textarea :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.6;
}

.variable-preview {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
  padding: 6px 0;
}

.detected-label {
  font-size: 13px;
  color: #909399;
  margin-right: 4px;
}
</style>
