<template>
  <el-dialog
    v-model="store.modalVisible"
    :title="store.modalTitle"
    width="680px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-form
      ref="formRef"
      :model="store.formData"
      label-width="80px"
      label-position="top"
      size="default"
    >
      <el-row :gutter="16">
        <el-col :span="14">
          <el-form-item label="规则名称" required>
            <el-input v-model="store.formData.name" placeholder="请输入规则名称" maxlength="100" show-word-limit />
          </el-form-item>
        </el-col>
        <el-col :span="10">
          <el-form-item label="优先级">
            <el-select v-model="store.formData.priority" style="width:100%">
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="分类">
            <el-select v-model="store.formData.category" style="width:100%">
              <el-option label="参数校验" value="param_validate" />
              <el-option label="业务逻辑" value="biz_logic" />
              <el-option label="异常处理" value="error_handle" />
              <el-option label="边界值" value="boundary" />
              <el-option label="安全" value="security" />
              <el-option label="性能" value="performance" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态">
            <el-switch
              v-model="store.formData.is_enabled"
              active-text="启用"
              inactive-text="禁用"
              style="margin-top: 6px"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="规则描述">
        <el-input
          v-model="store.formData.description"
          type="textarea"
          :rows="2"
          placeholder="简要描述规则用途"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="规则内容" required>
        <div class="rule-content-wrap">
          <div class="rule-content-hint">
            <span>每行一条规则，共 {{ lineCount }} 条</span>
          </div>
          <el-input
            v-model="store.formData.rule_content"
            type="textarea"
            :rows="10"
            placeholder="请求参数不能为空&#10;参数类型必须为数字&#10;长度不能超过100个字符"
            class="rule-textarea"
          />
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="store.modalVisible = false">取消</el-button>
      <el-button type="primary" :loading="store.saving" @click="store.saveRule()">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { useRuleStore } from '../stores/rule.js'

const store = useRuleStore()

const lineCount = computed(() => {
  const t = store.formData.rule_content || ''
  return t.split('\n').filter(l => l.trim()).length
})
</script>

<style scoped>
.rule-content-wrap { width: 100%; }
.rule-content-hint {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 6px; font-size: 14px; color: #909399;
}
.rule-textarea :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 14px; line-height: 1.6;
}
</style>
