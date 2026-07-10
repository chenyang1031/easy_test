<template>
  <div class="md-form-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="$router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 class="page-title">
          <el-icon><EditPen /></el-icon>
          生成测试数据
        </h2>
      </div>
    </div>

    <div class="panel-card">
      <el-form ref="formRef" :model="form" label-width="100px" class="main-form">
        <!-- 生成条数 -->
        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="section-header">
              <el-icon color="#409eff"><InfoFilled /></el-icon>
              <span>基本信息</span>
            </div>
          </template>

          <el-form-item label="生成条数" required>
            <el-input-number
              v-model="form.num"
              :min="1"
              :max="10000"
              :step="10"
              controls-position="right"
              style="width: 200px"
            />
            <span class="form-hint">范围 1~10000</span>
          </el-form-item>

          <el-form-item label="用途" required>
            <el-input
              v-model="form.aim"
              placeholder="描述数据用途，如：登录接口测试数据"
              maxlength="255"
            />
          </el-form-item>

          <el-form-item label="描述">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="2"
              placeholder="可选，简单描述这批数据..."
            />
          </el-form-item>
        </el-card>

        <!-- 字段定义 -->
        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="section-header">
              <el-icon color="#67c23a"><List /></el-icon>
              <span>字段定义</span>
              <el-tag size="small" type="info" round>{{ fields.length }} 个字段</el-tag>
            </div>
          </template>

          <div class="field-list">
            <div v-for="(field, index) in fields" :key="index" class="field-row">
              <el-row :gutter="12" align="middle">
                <el-col :span="7">
                  <el-input
                    v-model="field.name"
                    placeholder="字段名"
                    size="default"
                    :disabled="generating"
                  />
                </el-col>
                <el-col :span="7">
                  <el-select v-model="field.type" placeholder="类型" size="default" style="width: 100%" :disabled="generating">
                    <el-option
                      v-for="opt in typeOptions"
                      :key="opt.value"
                      :label="opt.label"
                      :value="opt.value"
                    />
                  </el-select>
                </el-col>
                <el-col :span="6">
                  <el-checkbox v-model="field.required" :disabled="generating">必填</el-checkbox>
                </el-col>
                <el-col :span="4" class="field-actions">
                  <el-button
                    size="small"
                    text
                    type="danger"
                    @click="removeField(index)"
                    :disabled="generating || fields.length <= 1"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-col>
              </el-row>
              <el-row v-if="field.type === 'enum'" :gutter="12" style="margin-top:8px">
                <el-col :span="14" :push="1">
                  <el-input
                    v-model="field.values"
                    placeholder="枚举值用逗号分隔，如: A,B,C"
                    size="small"
                    :disabled="generating"
                    clearable
                  >
                    <template #prepend>枚举值</template>
                  </el-input>
                </el-col>
              </el-row>
            </div>
          </div>

          <el-button
            class="add-field-btn"
            size="small"
            @click="addField"
            :disabled="generating"
          >
            <el-icon><Plus /></el-icon> 添加字段
          </el-button>

          <div class="preset-section">
            <span class="preset-label">快速添加：</span>
            <el-button
              v-for="preset in presets"
              :key="preset.name"
              size="small"
              @click="applyPreset(preset)"
              :disabled="generating"
            >
              {{ preset.label }}
            </el-button>
          </div>
        </el-card>

        <!-- 预览 -->
        <el-card v-if="previewData" shadow="never" class="section-card">
          <template #header>
            <div class="section-header">
              <el-icon color="#e6a23c"><View /></el-icon>
              <span>数据预览（前 3 条）</span>
            </div>
          </template>
          <el-input
            type="textarea"
            :rows="8"
            :model-value="previewData"
            readonly
            class="preview-editor"
          />
        </el-card>

        <!-- 底部操作栏 -->
        <div class="form-footer">
          <el-button size="large" @click="$router.back()" :disabled="generating">
            <el-icon><Close /></el-icon> 取消
          </el-button>
          <el-button
            size="large"
            type="primary"
            :loading="generating"
            @click="submit"
          >
            <el-icon><Lightning /></el-icon> 生成并保存
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, EditPen, InfoFilled, List, Plus, Delete,
  View, Close, Lightning,
} from '@element-plus/icons-vue'
import { mockDataApi } from '../api/index.js'

const router = useRouter()

const generating = ref(false)
const formRef = ref(null)
const previewData = ref(null)

const form = reactive({
  num: 10,
  aim: '',
  description: '',
})

const typeOptions = [
  { value: 'username', label: '用户名' },
  { value: 'phone', label: '手机号' },
  { value: 'email', label: '邮箱' },
  { value: 'url', label: 'URL' },
  { value: 'ip', label: 'IP 地址' },
  { value: 'id_card', label: '身份证号' },
  { value: 'company', label: '公司名' },
  { value: 'address', label: '地址' },
  { value: 'bank_card', label: '银行卡号' },
  { value: 'text', label: '文本' },
  { value: 'int', label: '整数' },
  { value: 'float', label: '浮点数' },
  { value: 'boolean', label: '布尔值' },
  { value: 'datetime', label: '日期时间' },
  { value: 'date', label: '日期' },
  { value: 'enum', label: '枚举值' },
  { value: 'uuid', label: 'UUID' },
]

const presets = [
  {
    name: 'user',
    label: '用户信息',
    fields: [
      { name: 'username', type: 'username', required: false },
      { name: 'phone', type: 'phone', required: false },
      { name: 'email', type: 'email', required: false },
    ],
  },
  {
    name: 'address',
    label: '地址信息',
    fields: [
      { name: 'name', type: 'username', required: false },
      { name: 'phone', type: 'phone', required: false },
      { name: 'address', type: 'address', required: false },
    ],
  },
  {
    name: 'company',
    label: '公司信息',
    fields: [
      { name: 'company', type: 'company', required: false },
      { name: 'url', type: 'url', required: false },
      { name: 'address', type: 'address', required: false },
    ],
  },
]

const defaultField = { name: '', type: 'text', required: false, values: '' }

const fields = reactive([
  { ...defaultField },
])

function addField() {
  fields.push({ ...defaultField })
}

function removeField(index) {
  if (fields.length <= 1) return
  fields.splice(index, 1)
}

function applyPreset(preset) {
  fields.length = 0
  preset.fields.forEach(f => fields.push({ ...f }))
}

async function submit() {
  // 基本校验
  if (!form.aim.trim()) {
    ElMessage.warning('请输入用途')
    return
  }

  const fieldDefs = fields
    .filter(f => f.name.trim())
    .map(f => {
      const def = {
        name: f.name.trim(),
        type: f.type,
        required: f.required,
      }
      // enum 类型附带枚举值列表
      if (f.type === 'enum' && f.values) {
        def.values = f.values.split(',').map(v => v.trim()).filter(Boolean)
      }
      return def
    })

  if (fieldDefs.length === 0) {
    ElMessage.warning('请至少定义一个有效字段')
    return
  }

  generating.value = true
  try {
    const result = await mockDataApi.generate({
      field_defs: fieldDefs,
      num: form.num,
      aim: form.aim.trim(),
      description: form.description.trim(),
    })

    // 生成预览
    try {
      const data = JSON.parse(result.data)
      const preview = Array.isArray(data) ? data.slice(0, 3) : [data]
      previewData.value = JSON.stringify(preview, null, 2)
    } catch {
      previewData.value = result.data
    }

    ElMessage.success(`成功生成 ${result.data_count} 条 Mock 数据`)
    // 跳转回列表页
    setTimeout(() => router.push('/mock-data'), 1500)
  } catch (e) {
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
/* ---- 页面 ---- */
.md-form-page { padding: 0; }

/* ---- 页面标题 ---- */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header-left { display: flex; align-items: center; gap: 4px; }
.back-btn { font-size: 14px; color: #606266; padding: 6px 8px; transition: color 0.2s; }
.back-btn:hover { color: #409eff; }
.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ---- 内容卡片 ---- */
.panel-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
}
.section-card {
  width: 100%;
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
}
.section-card :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}
.section-card :deep(.el-card__body) { padding: 16px 20px; }
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

/* ---- 表单 ---- */
.main-form :deep(.el-form-item) { margin-bottom: 16px; }
.main-form :deep(.el-form-item:last-child) { margin-bottom: 0; }
.main-form :deep(.el-form-item__label) { font-weight: 500; color: #606266; }
.form-hint {
  font-size: 13px;
  color: #909399;
  margin-left: 12px;
}

/* ---- 字段列表 ---- */
.field-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.field-row {
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}
.field-actions { text-align: right; }
.add-field-btn { margin-bottom: 12px; }

/* ---- 预设 ---- */
.preset-section {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.preset-label { font-size: 13px; color: #909399; white-space: nowrap; }

/* ---- 预览 ---- */
.preview-editor :deep(textarea) {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  background: #f8f9fa;
}

/* ---- 底部 ---- */
.form-footer {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 4px 0 32px;
  box-sizing: border-box;
}
</style>
