<template>
  <el-dialog
    v-model="store.modalVisible" :title="store.modalTitle"
    width="900px" :close-on-click-modal="false" destroy-on-close
  >
    <el-form :model="store.formData" label-width="100px" label-position="top" size="default">
      <!-- 基本信息 -->
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="供应商名称" required>
            <el-input v-model="store.formData.name" placeholder="如：智谱AI" maxlength="100" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="供应商类型">
            <el-select v-model="store.formData.provider_type" style="width:100%">
              <el-option label="OpenAI 兼容" value="openai" />
              <el-option label="智谱 AI" value="zhipu" />
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <!-- API配置 -->
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="API 基础地址" required>
            <el-input v-model="store.formData.base_url" placeholder="https://open.bigmodel.cn/api/paas/v4" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="API 路径">
            <el-input v-model="store.formData.api_path" placeholder="/chat/completions" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="模型名称" required>
            <el-input v-model="store.formData.model_name" placeholder="glm-4-plus" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="API Key">
        <el-input v-model="store.formData.api_key" placeholder="Bearer Token" type="password" show-password />
      </el-form-item>

      <!-- 模型参数 -->
      <el-row :gutter="16">
        <el-col :span="6">
          <el-form-item label="温度 (0-2)">
            <el-input-number v-model="store.formData.temperature" :min="0" :max="2" :step="0.1" :precision="1" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="最大 Token">
            <el-input-number v-model="store.formData.max_tokens" :min="100" :max="128000" :step="256" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="超时时间(秒)">
            <el-input-number v-model="store.formData.timeout" :min="10" :max="600" :step="10" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="响应解桥路径">
            <el-input v-model="store.formData.response_cases_path" placeholder="choices.0.message.content" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 系统提示词 -->
      <el-form-item label="系统提示词">
        <el-input v-model="store.formData.system_prompt" type="textarea" :rows="2" placeholder="你是一个专业的API测试工程师..." />
      </el-form-item>

      <!-- 提示词模板 -->
      <el-form-item label="提示词模板" required>
        <div class="template-wrap">
          <div class="template-hint">
            <span>可用变量：</span>
            <el-tag v-for="v in templateVars" :key="v" size="small" effect="plain" @click="insertVar(v)" style="cursor:pointer">
              {{ '{' + v + '}' }}
            </el-tag>
          </div>
          <el-input
            v-model="store.formData.prompt_template"
            type="textarea" :rows="10" class="template-textarea"
            placeholder="请根据接口信息生成测试用例..."
          />
        </div>
      </el-form-item>

      <!-- 开关 -->
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item>
            <el-switch v-model="store.formData.is_enabled" active-text="启用" inactive-text="禁用" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item>
            <el-switch v-model="store.formData.is_default" active-text="设为默认" inactive-text="非默认" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 测试结果 -->
      <el-alert v-if="store.testResult" :title="store.testResult.msg" :type="store.testResult.type" show-icon closable class="mt-2" @close="store.testResult = null" />
    </el-form>

    <template #footer>
      <el-button @click="store.modalVisible = false">取消</el-button>
      <el-button v-if="store.editingId" type="success" :loading="store.testing" @click="store.testConnection(store.editingId)">
        <el-icon style="margin-right:4px"><Connection /></el-icon>测试连接
      </el-button>
      <el-button type="primary" :loading="store.saving" @click="store.save()">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { Connection } from '@element-plus/icons-vue'
import { useModelProviderStore } from '../stores/modelProvider.js'

const store = useModelProviderStore()

const templateVars = ['method', 'url', 'headers', 'body_schema', 'rules_text', 'case_type', 'casetype_desc', 'api_name', 'api_desc', 'params', 'body_format', 'request_body', 'response_schema', 'error_codes', 'auth_config']

function insertVar(name) {
  store.formData.prompt_template = (store.formData.prompt_template || '') + `{${name}}`
}
</script>

<style scoped>
.template-wrap { width: 100%; }
.template-hint {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin-bottom: 8px; padding: 6px 10px; background: #f5f7fa; border-radius: 6px; font-size: 13px; color: #909399;
}
.template-textarea :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 14px; line-height: 1.6;
}
</style>
