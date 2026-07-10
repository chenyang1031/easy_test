<template>
  <div class="environment-form-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="goBack" :icon="ArrowLeft" class="back-btn" />
        <h2 class="page-title">{{ isEdit ? '编辑环境' : '新建环境' }}</h2>
        <el-tag v-if="isEdit" size="small" effect="plain" :type="form.category === 'third_party' ? 'warning' : 'info'">
          {{ form.category === 'third_party' ? '第三方' : '默认' }}
        </el-tag>
      </div>
    </div>

    <!-- 加载骨架 -->
    <div v-if="loadingDetail" class="skeleton-wrap">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else>
      <div class="panel-card">
        <div v-loading="saving" class="form-body">
          <el-tabs v-model="activeTab" type="card" class="form-tabs">
            <!-- ====== 基础信息 ====== -->
            <el-tab-pane name="basic">
              <template #label>
                <span><el-icon :size="14"><InfoFilled /></el-icon> 基础信息</span>
              </template>
              <div class="form-section">
                <el-form label-position="top" class="env-form" :validate-on-rule-change="false">
                  <el-row :gutter="24">
                    <el-col :span="12">
                      <el-form-item
                        label="环境名称"
                        :error="formErrors.name"
                        required
                      >
                        <el-input
                          v-model="form.name"
                          placeholder="请输入环境名称"
                          maxlength="100"
                          show-word-limit
                          clearable
                        />
                        <div class="form-help">环境名称，例如「生产环境」「测试环境」</div>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item
                        label="项目"
                        :error="formErrors.project"
                        required
                      >
                        <el-select v-model="form.project" placeholder="选择项目" filterable style="width:100%">
                          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
                        </el-select>
                        <div class="form-help">选择与环境关联的项目</div>
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-form-item
                    label="域名"
                    :error="formErrors.base_url"
                    required
                  >
                    <el-input v-model="form.base_url" placeholder="https://api.example.com" clearable>
                      <template #prefix><el-icon><Link /></el-icon></template>
                    </el-input>
                    <div class="form-help">环境中 API 请求的基地址</div>
                  </el-form-item>

                  <el-row :gutter="24">
                    <el-col :span="12">
                      <el-form-item label="环境分类">
                        <el-select v-model="form.category" style="width:100%">
                          <el-option label="默认环境" value="default" />
                          <el-option label="第三方环境" value="third_party" />
                        </el-select>
                        <div class="form-help">第三方环境可用于调用外部地址</div>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item>
                        <template #label>
                          <span>全局可见</span>
                        </template>
                        <div class="checkbox-wrap">
                          <el-switch v-model="form.is_global_visible" />
                          <span class="switch-label">{{ form.is_global_visible ? '是' : '否' }}</span>
                        </div>
                        <div class="form-help">开启后，其他项目也可选择此环境</div>
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form>
              </div>
            </el-tab-pane>

            <!-- ====== 前置脚本 ====== -->
            <el-tab-pane name="script">
              <template #label>
                <span><el-icon :size="14"><EditPen /></el-icon> 前置脚本</span>
              </template>
              <div class="form-section">
                <el-form label-position="top">
                  <el-form-item label="前置脚本（可选）">
                    <el-input
                      v-model="form.pre_request_script"
                      type="textarea"
                      :rows="14"
                      placeholder="// 使用 pm.environment、pm.request、pm.variables 预处理请求"
                      class="script-textarea"
                    />
                    <div class="form-help">当前仅支持 ES5.1 语法。如执行出现错误，建议使用 AI 工具将脚本转换为 ES5.1 语法。</div>
                  </el-form-item>

                  <el-form-item label="脚本超时 (ms)">
                    <el-input-number
                      v-model="form.script_timeout"
                      :min="100"
                      :max="10000"
                      :step="100"
                      style="width:200px"
                    />
                    <div class="form-help">脚本执行超时时间，默认为 1000ms</div>
                  </el-form-item>
                </el-form>
              </div>
            </el-tab-pane>

            <!-- ====== 环境变量 ====== -->
            <el-tab-pane name="variables">
              <template #label>
                <span><el-icon :size="14"><List /></el-icon> 环境变量 <el-tag size="small" round type="primary">{{ varRows.length }}</el-tag></span>
              </template>
              <div class="form-section">
                <el-alert
                  title="键值对将保存为 JSON 对象；说明文案写入 __var_descriptions__ 元数据，运行时不会参与变量替换。"
                  type="info"
                  :closable="false"
                  show-icon
                  class="section-alert"
                />
                <el-table :data="varRows" border stripe size="small" class="env-kv-table" empty-text="暂无行，请点击下方按钮添加">
                  <el-table-column label="变量名" min-width="160">
                    <template #default="{ row, $index }">
                      <el-input v-model="row.key" placeholder="Key" size="small" clearable />
                    </template>
                  </el-table-column>
                  <el-table-column label="变量值" min-width="240">
                    <template #default="{ row, $index }">
                      <el-input v-model="row.value" type="textarea" :rows="2" placeholder="变量值" size="small" />
                    </template>
                  </el-table-column>
                  <el-table-column label="说明" min-width="160">
                    <template #default="{ row, $index }">
                      <el-input v-model="row.description" placeholder="选填" size="small" clearable />
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="88" align="center" fixed="right">
                    <template #default="{ $index }">
                      <el-button link type="danger" size="small" @click="removeVarRow($index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="mt-2">
                  <el-button type="primary" size="small" plain @click="addVarRow">
                    <el-icon><Plus /></el-icon> 添加行
                  </el-button>
                  <el-button size="small" @click="varRows = [{ key: '', value: '', description: '' }]">
                    清空
                  </el-button>
                </div>
              </div>
            </el-tab-pane>

            <!-- ====== 请求头预设 ====== -->
            <el-tab-pane name="headers">
              <template #label>
                <span><el-icon :size="14"><Paperclip /></el-icon> 请求头预设 <el-tag size="small" round type="primary">{{ headerRows.length }}</el-tag></span>
              </template>
              <div class="form-section">
                <el-alert
                  title="用于 API 资产编辑时一键填充；保存为 JSON 数组，兼容原有 key / value / required / type 字段。"
                  type="info"
                  :closable="false"
                  show-icon
                  class="section-alert"
                />
                <el-table :data="headerRows" border stripe size="small" class="env-kv-table" empty-text="暂无行，请点击下方按钮添加">
                  <el-table-column label="Header 名" min-width="160">
                    <template #default="{ row }">
                      <el-input v-model="row.key" placeholder="如 Content-Type" size="small" clearable />
                    </template>
                  </el-table-column>
                  <el-table-column label="值" min-width="200">
                    <template #default="{ row }">
                      <el-input v-model="row.value" placeholder="Header 值" size="small" clearable />
                    </template>
                  </el-table-column>
                  <el-table-column label="说明" min-width="140">
                    <template #default="{ row }">
                      <el-input v-model="row.description" placeholder="选填" size="small" clearable />
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="88" align="center" fixed="right">
                    <template #default="{ $index }">
                      <el-button link type="danger" size="small" @click="removeHeaderRow($index)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="mt-2">
                  <el-button type="primary" size="small" plain @click="addHeaderRow">
                    <el-icon><Plus /></el-icon> 添加行
                  </el-button>
                  <el-button size="small" @click="headerRows = [{ key: '', value: '', description: '', required: true, type: 'string' }]">
                    清空
                  </el-button>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 底部按钮 -->
        <div class="form-footer">
          <div>
            <el-button @click="goBack" :icon="ArrowLeft">取消</el-button>
          </div>
          <div class="form-footer-right">
            <el-button :loading="saving" @click="handleSubmit">
              <el-icon><Check /></el-icon> {{ isEdit ? '保存修改' : '创建环境' }}
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, InfoFilled, EditPen, List, Paperclip, Plus, Link } from '@element-plus/icons-vue'
import { environmentApi } from '../../../environment/api/index.js'
import { projectApi } from '../../../projects/api/index.js'
import {
  safeJsonParse,
  rowsFromVariables,
  buildVariablesObject,
  rowsFromHeaders,
  buildHeadersArray,
} from '../../../environment/utils/environmentPayload.js'

const router = useRouter()
const route = useRoute()

const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const loadingDetail = ref(false)
const activeTab = ref('basic')
const projects = ref([])
const form = ref({
  name: '',
  project: null,
  base_url: '',
  category: 'default',
  is_global_visible: false,
  pre_request_script: '',
  script_timeout: 1000,
})

const formErrors = reactive({
  name: '',
  project: '',
  base_url: '',
})

const varRows = ref([{ key: '', value: '', description: '' }])
const headerRows = ref([{ key: '', value: '', description: '', required: true, type: 'string' }])

function addVarRow() { varRows.value.push({ key: '', value: '', description: '' }) }
function removeVarRow(index) {
  varRows.value.splice(index, 1)
  if (!varRows.value.length) varRows.value.push({ key: '', value: '', description: '' })
}

function addHeaderRow() { headerRows.value.push({ key: '', value: '', description: '', required: true, type: 'string' }) }
function removeHeaderRow(index) {
  headerRows.value.splice(index, 1)
  if (!headerRows.value.length) headerRows.value.push({ key: '', value: '', description: '', required: true, type: 'string' })
}

function clearErrors() {
  formErrors.name = ''
  formErrors.project = ''
  formErrors.base_url = ''
}

function goBack() {
  if (isEdit.value) {
    router.push(`/environments/${route.params.id}`)
  } else {
    router.push('/environments')
  }
}

function validate() {
  clearErrors()
  let valid = true
  if (!form.value.name.trim()) {
    formErrors.name = '请输入环境名称'
    valid = false
  }
  if (!form.value.project) {
    formErrors.project = '请选择项目'
    valid = false
  }
  if (!form.value.base_url.trim()) {
    formErrors.base_url = '请输入域名'
    valid = false
  }
  return valid
}

async function handleSubmit() {
  if (!validate()) {
    activeTab.value = 'basic'
    return
  }

  saving.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      project: form.value.project,
      base_url: form.value.base_url.trim(),
      category: form.value.category,
      is_global_visible: form.value.is_global_visible,
      pre_request_script: form.value.pre_request_script,
      script_timeout: form.value.script_timeout,
      variables: buildVariablesObject(varRows.value),
      request_headers: buildHeadersArray(headerRows.value),
    }

    if (isEdit.value) {
      await environmentApi.update(route.params.id, payload)
      ElMessage.success('环境已更新')
      router.push(`/environments/${route.params.id}`)
    } else {
      const result = await environmentApi.create(payload)
      ElMessage.success('环境已创建')
      router.push(`/environments/${result.id}`)
    }
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function loadProjects() {
  try {
    const data = await projectApi.list({ page_size: 1000 })
    projects.value = data.results || data
    // 如果 URL 中有 project 参数，自动选中
    if (!isEdit.value && route.query.project) {
      const pid = Number(route.query.project)
      if (projects.value.some(p => p.id === pid)) {
        form.value.project = pid
      }
    }
  } catch { /* ignore */ }
}

async function loadDetail() {
  if (!isEdit.value) return
  loadingDetail.value = true
  try {
    const env = await environmentApi.get(route.params.id)
    form.value = {
      name: env.name || '',
      project: env.project || null,
      base_url: env.base_url || '',
      category: env.category || 'default',
      is_global_visible: !!env.is_global_visible,
      pre_request_script: env.pre_request_script || '',
      script_timeout: env.script_timeout ?? 1000,
    }
    const variablesObj = safeJsonParse(
      typeof env.variables === 'string' ? env.variables : JSON.stringify(env.variables || {}),
      {}
    )
    varRows.value = rowsFromVariables(variablesObj)

    const headersRaw = safeJsonParse(
      typeof env.request_headers === 'string' ? env.request_headers : JSON.stringify(env.request_headers || []),
      []
    )
    headerRows.value = rowsFromHeaders(headersRaw)
  } catch (e) {
    ElMessage.error('加载环境信息失败: ' + (e.message || '未知错误'))
  } finally {
    loadingDetail.value = false
  }
}

onMounted(async () => {
  await loadProjects()
  await loadDetail()
})
</script>

<style scoped>
.environment-form-page { padding: 0; min-height: 100%; }

/* ---- 页面标题 ---- */
.page-header { display: flex; align-items: center; margin-bottom: 20px; }
.page-header-left { display: flex; align-items: center; gap: 8px; }
.page-title { font-size: 24px; font-weight: 600; color: #303133; margin: 0; line-height: 1.3; }
.back-btn { font-size: 20px; padding: 4px; }

/* ---- 骨架屏 ---- */
.skeleton-wrap { background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }

/* ---- 卡片 ---- */
.panel-card {
  background: #fff; border-radius: 10px; padding: 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  max-width: 860px;
  margin: 0 auto;
}

/* ---- 表单 ---- */
.form-body { min-height: 200px; }
.form-tabs { margin-top: 0; }
.form-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
.form-tabs :deep(.el-tabs__item) { font-size: 14px; }
.form-tabs :deep(.el-tabs__item) .el-icon { vertical-align: middle; margin-right: 3px; }
.form-section { max-width: 860px; padding: 20px 4px 8px; }
.env-form :deep(.el-form-item) { margin-bottom: 22px; }
.env-form :deep(.el-form-item__label) { font-weight: 500; color: #303133; }
.form-help { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1.4; }
.text-muted-hint { font-size: 13px; color: #909399; margin-bottom: 12px; }
.text-muted-hint code { font-size: 12px; background: #f5f7fa; padding: 1px 5px; border-radius: 3px; }
.env-kv-table { width: 100%; }
.script-textarea :deep(.el-textarea__inner) { font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace; font-size: 13px; }
.checkbox-wrap { display: flex; align-items: center; gap: 10px; }
.switch-label { font-size: 14px; color: #606266; }
.mt-2 { margin-top: 12px; display: flex; gap: 8px; }
.section-alert { margin-bottom: 16px; }

/* ---- 底部按钮 ---- */
.form-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 24px; padding-top: 20px; border-top: 1px solid #ebeef5;
}
</style>
