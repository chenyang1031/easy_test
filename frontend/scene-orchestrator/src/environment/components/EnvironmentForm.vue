<template>
  <form id="environment-form-app" method="post" action="" @submit="onFormSubmit">
    <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />
    <input type="hidden" name="project" :value="project" />
    <input type="hidden" name="category" :value="category" />

    <el-tabs v-model="activeTab" type="card" class="environment-form-tabs">
      <el-tab-pane label="基础信息" name="basic">
        <div class="env-tab-pane-inner">
          <div class="mb-3">
            <label class="form-label fw-medium">环境名称</label>
            <input
              v-model="name"
              type="text"
              name="name"
              class="form-control form-control-lg"
              required
              placeholder="请输入环境名称"
              maxlength="100"
            />
            <div class="form-text">环境名称（例如 OA 系统、HR 系统）</div>
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">项目</label>
            <el-select v-model="project" placeholder="选择项目" filterable style="width: 100%" size="small">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <div class="form-text">选择与环境关联的项目</div>
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">域名</label>
            <input
              v-model="baseUrl"
              type="url"
              name="base_url"
              class="form-control"
              required
              placeholder="https://api.example.com"
            />
            <div class="form-text">环境中 API 请求的基地址</div>
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">环境分类</label>
            <el-select v-model="category" style="width: 100%" size="small">
              <el-option label="默认环境" value="default" />
              <el-option label="第三方环境" value="third_party" />
            </el-select>
            <div class="form-text">第三方环境可用于调用外部地址</div>
          </div>
          <div class="mb-3">
            <div class="form-check">
              <input
                id="id_is_global_visible"
                v-model="isGlobalVisible"
                type="checkbox"
                name="is_global_visible"
                class="form-check-input"
              />
              <label class="form-check-label" for="id_is_global_visible">全局可见</label>
            </div>
            <div class="form-text">开启后，其他项目也可选择此环境</div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="前置脚本" name="script">
        <div class="env-tab-pane-inner">
          <div class="mb-3">
            <label class="form-label fw-medium">前置脚本（可选）</label>
            <textarea
              v-model="preRequestScript"
              name="pre_request_script"
              class="form-control font-monospace"
              rows="14"
              placeholder="// 使用 pm.environment、pm.request、pm.variables 预处理请求"
            />
            <div class="form-text">当前仅支持 ES5.1 语法。如执行出现错误，建议使用 AI 工具将脚本转换为 ES5.1 语法。</div>
            <div v-if="preRequestScriptHelp" class="form-text">{{ preRequestScriptHelp }}</div>
          </div>
          <div class="mb-3">
            <label class="form-label fw-medium">脚本超时 (ms)</label>
            <input
              v-model.number="scriptTimeout"
              type="number"
              name="script_timeout"
              class="form-control"
              min="100"
              max="1000"
              placeholder="1000"
              style="max-width: 240px"
            />
            <div v-if="scriptTimeoutHelp" class="form-text">{{ scriptTimeoutHelp }}</div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="环境变量" name="variables">
        <div class="env-tab-pane-inner">
          <p class="text-muted small mb-2">
            键值对将保存为 JSON 对象；说明文案写入 <code>__var_descriptions__</code> 元数据，运行时不会参与变量替换。
          </p>
          <el-table
            :data="varRows"
            border
            stripe
            size="small"
            class="env-kv-table env-variables-table"
            empty-text="暂无行，请点击下方按钮添加"
          >
            <el-table-column label="变量名" min-width="160" class-name="env-var-col-key">
              <template #default="scope">
                <el-input v-model="scope.row.key" placeholder="Key" size="small" clearable />
              </template>
            </el-table-column>
            <el-table-column label="变量值" min-width="220" class-name="env-var-col-value">
              <template #default="scope">
                <el-input
                  v-model="scope.row.value"
                  type="textarea"
                  :rows="2"
                  placeholder="变量值；支持 mustache 占位符或 JSON 字面量"
                  size="small"
                />
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="160" class-name="env-var-col-desc">
              <template #default="scope">
                <el-input v-model="scope.row.description" placeholder="选填" size="small" clearable />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="88" align="center" fixed="right">
              <template #default="scope">
                <el-button link type="danger" size="small" @click="removeVarRow(scope.$index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="mt-2">
            <el-button type="primary" size="small" @click="addVarRow"><i class="bi bi-plus-lg"></i> 添加行</el-button>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="请求头预设" name="headers">
        <div class="env-tab-pane-inner">
          <p class="text-muted small mb-2">
            用于 API 资产编辑时一键填充；保存为 JSON 数组，兼容原有 <code>key / value / required / type</code> 字段。
          </p>
          <el-table :data="headerRows" border stripe size="small" class="env-kv-table" empty-text="暂无行，请点击下方按钮添加">
            <el-table-column label="Header 名" min-width="160">
              <template #default="scope">
                <el-input v-model="scope.row.key" placeholder="如 Content-Type" size="small" clearable />
              </template>
            </el-table-column>
            <el-table-column label="值" min-width="200">
              <template #default="scope">
                <el-input v-model="scope.row.value" placeholder="Header 值" size="small" clearable />
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="140">
              <template #default="scope">
                <el-input v-model="scope.row.description" placeholder="选填" size="small" clearable />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="88" align="center" fixed="right">
              <template #default="scope">
                <el-button link type="danger" size="small" @click="removeHeaderRow(scope.$index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="mt-2">
            <el-button type="primary" size="small" @click="addHeaderRow"><i class="bi bi-plus-lg"></i> 添加行</el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <textarea v-model="variablesJsonStr" name="variables_json" class="d-none" aria-hidden="true" />
    <textarea v-model="requestHeadersJsonStr" name="request_headers_json" class="d-none" aria-hidden="true" />

    <div class="d-flex justify-content-between mt-4">
      <a :href="cancelUrl" class="btn btn-outline-secondary">
        <i class="bi bi-arrow-left"></i> 取消
      </a>
      <button type="submit" class="btn btn-primary px-4">
        <i class="bi bi-check-lg"></i> 保存
      </button>
    </div>
  </form>
</template>

<script>
import {
  safeJsonParse,
  rowsFromVariables,
  buildVariablesObject,
  rowsFromHeaders,
  buildHeadersArray,
} from "../utils/environmentPayload.js";

export default {
  name: "EnvironmentForm",
  props: {
    initialJson: {
      type: [Object, String],
      default: () => ({}),
    },
    cancelUrl: {
      type: String,
      required: true,
    },
  },
  data() {
    const initial =
      typeof this.initialJson === "string" ? safeJsonParse(this.initialJson, {}) : this.initialJson || {};
    const variablesObj = safeJsonParse(initial.variablesJson || "{}", {});
    const headersRaw = safeJsonParse(initial.requestHeadersJson || "[]", []);
    return {
      csrfToken: initial.csrfToken || "",
      preRequestScriptHelp: initial.preRequestScriptHelp || "",
      scriptTimeoutHelp: initial.scriptTimeoutHelp || "",
      activeTab: "basic",
      name: initial.name || "",
      project: initial.project != null && initial.project !== "" ? Number(initial.project) : null,
      projects: initial.projects || [],
      baseUrl: initial.baseUrl || "",
      category: initial.category || "default",
      isGlobalVisible: !!initial.isGlobalVisible,
      preRequestScript: initial.preRequestScript || "",
      scriptTimeout: initial.scriptTimeout != null ? Number(initial.scriptTimeout) : 1000,
      varRows: rowsFromVariables(variablesObj),
      headerRows: rowsFromHeaders(headersRaw),
      variablesJsonStr: JSON.stringify(variablesObj),
      requestHeadersJsonStr: JSON.stringify(headersRaw),
    };
  },
  methods: {
    onFormSubmit(e) {
      const form = e.currentTarget;
      const v = JSON.stringify(buildVariablesObject(this.varRows));
      const h = JSON.stringify(buildHeadersArray(this.headerRows));
      const taVar = form.querySelector('textarea[name="variables_json"]');
      const taHdr = form.querySelector('textarea[name="request_headers_json"]');
      if (taVar) taVar.value = v;
      if (taHdr) taHdr.value = h;
      this.variablesJsonStr = v;
      this.requestHeadersJsonStr = h;
      const hiProj = form.querySelector('input[type="hidden"][name="project"]');
      const hiCat = form.querySelector('input[type="hidden"][name="category"]');
      if (hiProj) {
        hiProj.value =
          this.project !== null && this.project !== undefined && this.project !== "" ? String(this.project) : "";
      }
      if (hiCat) hiCat.value = this.category || "";
    },
    addVarRow() {
      this.varRows.push({ key: "", value: "", description: "" });
    },
    removeVarRow(index) {
      this.varRows.splice(index, 1);
      if (!this.varRows.length) {
        this.varRows.push({ key: "", value: "", description: "" });
      }
    },
    addHeaderRow() {
      this.headerRows.push({ key: "", value: "", description: "", required: true, type: "string" });
    },
    removeHeaderRow(index) {
      this.headerRows.splice(index, 1);
      if (!this.headerRows.length) {
        this.headerRows.push({ key: "", value: "", description: "", required: true, type: "string" });
      }
    },
  },
};
</script>

<style scoped>
.environment-form-tabs {
  margin-top: 0;
}
.environment-form-tabs .el-tabs__header {
  margin-bottom: 12px;
}
.environment-form-tabs .el-tabs__item {
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
  font-size: 13px;
}
.environment-form-tabs .el-tabs__content {
  overflow: visible;
}
.env-tab-pane-inner {
  padding-top: 4px;
  min-height: 200px;
}
.env-kv-table {
  width: 100%;
}
.env-kv-table .el-input__inner,
.env-kv-table .el-textarea__inner {
  font-size: 13px;
}
.environment-form-tabs .env-variables-table .el-table__cell {
  padding-top: 14px;
  padding-bottom: 14px;
  vertical-align: middle;
}
.environment-form-tabs .env-variables-table td.env-var-col-key,
.environment-form-tabs .env-variables-table td.env-var-col-desc {
  padding-top: 17px;
  padding-bottom: 17px;
}
</style>
