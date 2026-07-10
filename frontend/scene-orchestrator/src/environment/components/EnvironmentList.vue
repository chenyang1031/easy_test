<template>
  <div class="environment-list-vue">
    <el-alert
      v-if="projectFilter"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <template #title>
        <span>按项目筛选: <strong>{{ projectFilter.name }}</strong></span>
        <a :href="projectFilter.clearUrl" class="btn btn-sm btn-outline-primary ms-3">
          <i class="bi bi-x-lg"></i> 清除筛选
        </a>
      </template>
    </el-alert>

    <el-table
      v-if="rows.length"
      :data="rows"
      stripe
      style="width: 100%"
      class="environment-list-table"
    >
      <el-table-column prop="name" label="名称" min-width="160">
        <template #default="scope">
          <a :href="scope.row.urls.detail" class="fw-medium text-decoration-none text-dark">
            {{ scope.row.name }}
          </a>
        </template>
      </el-table-column>
      <el-table-column prop="projectName" label="项目" min-width="140">
        <template #default="scope">
          <a :href="scope.row.urls.project" class="text-decoration-none">
            {{ scope.row.projectName }}
          </a>
        </template>
      </el-table-column>
      <el-table-column prop="baseUrl" label="域名" min-width="220">
        <template #default="scope">
          <code class="bg-light px-2 py-1 rounded">{{ scope.row.baseUrl }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" width="170" />
      <el-table-column label="操作" width="220" align="right" fixed="right">
        <template #default="scope">
          <el-button-group>
            <el-button size="small" @click="go(scope.row.urls.detail)"><i class="bi bi-eye"></i></el-button>
            <el-button size="small" @click="go(scope.row.urls.edit)"><i class="bi bi-pencil"></i></el-button>
            <el-button size="small" type="danger" @click="go(scope.row.urls.delete)"><i class="bi bi-trash"></i></el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="text-center py-5">
      <div class="py-5">
        <i class="bi bi-gear-wide-connected display-4 text-muted mb-3"></i>
        <h5>暂无环境</h5>
        <p class="text-muted">创建第一个环境</p>
        <a :href="createUrl" class="btn btn-primary mt-2">
          <i class="bi bi-plus-lg"></i> 创建环境
        </a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "EnvironmentList",
  props: {
    initial: {
      type: Object,
      default: () => ({ rows: [], projectFilter: null }),
    },
    createUrl: {
      type: String,
      default: "/environments/create/",
    },
  },
  data() {
    return {
      rows: this.initial.rows || [],
      projectFilter: this.initial.projectFilter || null,
    };
  },
  methods: {
    go(url) {
      if (url) window.location.href = url;
    },
  },
};
</script>

<style scoped>
.environment-list-table .el-button-group .el-button {
  padding: 7px 10px;
}
</style>
