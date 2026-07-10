<template>
  <div class="project-detail-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <el-button text @click="goBack" :icon="ArrowLeft" class="back-btn" />
        <div class="breadcrumb">
          <router-link to="/projects" class="breadcrumb-link">项目列表</router-link>
          <span class="breadcrumb-sep">›</span>
          <span class="breadcrumb-current">{{ project.name || '项目详情' }}</span>
        </div>
      </div>
      <div class="page-header-right">
        <el-button @click="loadData" :icon="Refresh">刷新</el-button>
        <el-button type="primary" :icon="Edit" @click="goEdit">编辑项目</el-button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="28"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <template v-else>
      <!-- ===== 项目信息 - 顶部全宽 ===== -->
      <div class="card info-card">
        <div class="card-header-row">
          <el-icon :size="16" color="#409eff"><InfoFilled /></el-icon>
          <span class="card-section-title">项目信息</span>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
          <el-descriptions-item label="创建人">
            <div class="creator-cell">
              <span class="creator-avatar">{{ getInitial(project.created_by_name) }}</span>
              <span>{{ project.created_by_name }}</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="描述">
            {{ project.description || '暂无描述' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(project.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatTime(project.updated_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- ===== 下部分两列 ===== -->
      <div class="body-row">
        <!-- 左列：分组管理 -->
        <div class="body-col-main">
          <div class="card">
            <ProjectGroupManager :project-id="Number(route.params.id)" />
          </div>
        </div>

        <!-- 右列：快捷入口 + 环境 -->
        <div class="body-col-side">
          <!-- 快捷入口 -->
          <div class="card">
            <div class="card-header-row">
              <el-icon :size="16" color="#67c23a"><Discount /></el-icon>
              <span class="card-section-title">快捷入口</span>
            </div>
            <el-row :gutter="8">
              <el-col :span="12" class="quick-item">
                <el-card shadow="hover" class="quick-card" @click="$router.push(`/environments?project=${project.id}`)">
                  <el-icon :size="20" color="#409eff"><Setting /></el-icon>
                  <div class="quick-text">环境管理</div>
                </el-card>
              </el-col>
              <el-col :span="12" class="quick-item">
                <el-card shadow="hover" class="quick-card" @click="$router.push(`/test-cases?project=${project.id}`)">
                  <el-icon :size="20" color="#67c23a"><Document /></el-icon>
                  <div class="quick-text">测试用例</div>
                </el-card>
              </el-col>
              <el-col :span="12" class="quick-item">
                <el-card shadow="hover" class="quick-card" @click="$router.push(`/test-suites?project=${project.id}`)">
                  <el-icon :size="20" color="#e6a23c"><Collection /></el-icon>
                  <div class="quick-text">测试套件</div>
                </el-card>
              </el-col>
              <el-col :span="12" class="quick-item">
                <el-card shadow="hover" class="quick-card" @click="$router.push(`/api-assets?project=${project.id}`)">
                  <el-icon :size="20" color="#909399"><Connection /></el-icon>
                  <div class="quick-text">API 资产</div>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <!-- 关联环境 -->
          <div class="card">
            <div class="card-header-row">
              <el-icon :size="16" color="#e6a23c"><Link /></el-icon>
              <span class="card-section-title">关联环境</span>
              <el-button size="small" type="primary" plain @click="goCreateEnv">
                <el-icon><Plus /></el-icon> 添加
              </el-button>
            </div>
            <div v-if="envsLoading" class="mini-loading">
              <el-icon class="is-loading"><Loading /></el-icon> 加载中...
            </div>
            <template v-else-if="envs.length > 0">
              <div class="env-list">
                <div v-for="env in envs" :key="env.id" class="env-item" @click="$router.push(`/environments/${env.id}`)">
                  <div class="env-dot" :style="{ background: env.color || '#409eff' }"></div>
                  <div class="env-info">
                    <div class="env-name">{{ env.name }}</div>
                    <code class="env-url">{{ env.base_url }}</code>
                  </div>
                  <el-icon class="env-arrow"><ArrowRight /></el-icon>
                </div>
              </div>
            </template>
            <el-empty v-else description="暂无关联环境" :image-size="36" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Edit, Refresh, Loading, Plus, Setting, Collection, Connection, Document, InfoFilled, Discount, Link } from '@element-plus/icons-vue'
import { projectApi } from '../../../projects/api/index.js'
import { environmentApi } from '../../../environment/api/index.js'
import ProjectGroupManager from './ProjectGroupManager.vue'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const project = ref({})
const envs = ref([])
const envsLoading = ref(false)

function getInitial(name) { return (name || '?').charAt(0).toUpperCase() }

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function goBack() { router.push('/projects') }
function goEdit() { router.push(`/projects/${route.params.id}/edit`) }
function goCreateEnv() { router.push(`/environments/create?project=${route.params.id}`) }

async function loadData() {
  loading.value = true
  try {
    const data = await projectApi.get(route.params.id)
    project.value = data
  } catch (e) {
    ElMessage.error('加载项目详情失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }

  // 加载关联环境
  envsLoading.value = true
  try {
    const data = await environmentApi.list({ project: route.params.id, page_size: 100 })
    envs.value = data.results || data
  } catch { /* ignore */ }
  finally { envsLoading.value = false }
}

onMounted(() => { loadData() })
</script>

<style scoped>
.project-detail-page {
  padding: 0;
  min-height: 100%;
}

/* ===== 页面头部 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}
.page-header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}
.back-btn {
  font-size: 18px;
  padding: 4px 6px;
  margin-right: 4px;
}
.back-btn:hover {
  background: #f0f2f5;
  border-radius: 6px;
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}
.breadcrumb-link {
  color: #909399;
  text-decoration: none;
  transition: color 0.15s;
}
.breadcrumb-link:hover {
  color: #409eff;
}
.breadcrumb-sep {
  color: #c0c4cc;
  font-size: 16px;
  font-weight: 600;
}
.breadcrumb-current {
  color: #303133;
  font-weight: 600;
  font-size: 20px;
}
.page-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ===== 加载状态 ===== */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 0;
  color: #909399;
}
.mini-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 16px 0;
  color: #909399;
  font-size: 13px;
  justify-content: center;
}

/* ===== 通用卡片 ===== */
.card {
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
}
.info-card {
  margin-bottom: 20px;
}
.card-header-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
}
.card-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.card-header-row .el-button {
  margin-left: auto;
}

/* ===== 项目信息 ===== */
.creator-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.creator-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

/* ===== 两列布局 ===== */
.body-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.body-col-main {
  flex: 1.5;
  min-width: 0;
}
.body-col-side {
  flex: 1;
  min-width: 280px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
@media (max-width: 900px) {
  .body-row { flex-direction: column; }
  .body-col-side { max-width: none; }
}

/* ===== 快捷入口 ===== */
.quick-item {
  margin-bottom: 8px;
}
.quick-card {
  cursor: pointer;
  text-align: center;
  transition: transform 0.15s, box-shadow 0.15s;
}
.quick-card:hover {
  transform: translateY(-1px);
}
.quick-card :deep(.el-card__body) {
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.quick-text {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

/* ===== 关联环境列表 ===== */
.env-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.env-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
}
.env-item:hover {
  background: #f5f7fa;
}
.env-item:hover .env-arrow {
  opacity: 1;
}
.env-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.env-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.env-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.env-url {
  font-size: 11px;
  color: #909399;
  background: #f5f7fa;
  padding: 1px 5px;
  border-radius: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  max-width: 100%;
}
.env-arrow {
  font-size: 12px;
  color: #c0c4cc;
  opacity: 0;
  transition: opacity 0.12s;
  flex-shrink: 0;
}
</style>
