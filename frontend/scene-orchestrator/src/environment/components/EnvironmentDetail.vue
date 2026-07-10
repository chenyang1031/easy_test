<template>
  <div id="environment-detail-root" v-cloak>
    <el-tabs v-model="activeTab" type="card">
      <el-tab-pane label="概览" name="overview">
        <div class="row">
          <div class="col-md-6 mb-4">
            <el-card class="h-100" shadow="never">
              <template #header>
                <div class="clearfix">
                  <span>环境变量详情</span>
                  <a :href="urls.edit" class="btn btn-sm btn-outline-secondary float-end">
                    <i class="bi bi-pencil"></i>
                  </a>
                </div>
              </template>
              <div class="mb-4">
                <h5 class="text-muted mb-2">项目</h5>
                <p>
                  <a :href="urls.project" class="text-decoration-none">{{ project.name }}</a>
                </p>
              </div>
              <div class="mb-4">
                <h5 class="text-muted mb-2">域名</h5>
                <div class="d-flex align-items-center">
                  <code class="bg-light px-3 py-2 rounded flex-grow-1">{{ environment.baseUrl }}</code>
                  <el-button size="small" class="ms-2" @click="copyToClipboard(environment.baseUrl)">
                    <i class="bi bi-clipboard"></i>
                  </el-button>
                </div>
              </div>
              <div class="mb-4">
                <h5 class="text-muted mb-2">创建时间</h5>
                <p>{{ environment.createdAt }}</p>
              </div>
              <div class="mb-4">
                <h5 class="text-muted mb-2">更新时间</h5>
                <p>{{ environment.updatedAt }}</p>
              </div>
            </el-card>
          </div>
          <div class="col-md-6 mb-4">
            <el-card class="h-100" shadow="never">
              <template #header><span>环境变量</span></template>
              <div v-if="hasVariables">
                <div class="table-responsive">
                  <table class="table table-hover">
                    <thead>
                      <tr>
                        <th>Key</th>
                        <th>Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in variablesRows" :key="row.key">
                        <td><code>{{ row.key }}</code></td>
                        <td><code>{{ row.value }}</code></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div v-else class="text-center py-4">
                <div class="text-muted">
                  <i class="bi bi-info-circle me-2"></i> 暂时没有环境变量
                </div>
                <a :href="urls.edit" class="btn btn-sm btn-outline-primary mt-2">新增环境变量</a>
              </div>
            </el-card>
          </div>
        </div>

        <div class="row">
          <div class="col-md-12 mb-4">
            <el-card shadow="never">
              <template #header>
                <div class="clearfix">
                  <span>最近与此环境关联的场景运行</span>
                  <a :href="urls.sceneExecutionListFiltered" class="btn btn-sm btn-outline-primary float-end">查看全部</a>
                </div>
              </template>
              <div class="table-responsive">
                <table class="table table-hover table-sm">
                  <thead>
                    <tr>
                      <th>场景名称</th>
                      <th>状态</th>
                      <th>执行时间</th>
                      <th>耗时</th>
                      <th class="text-end">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="ex in recentSceneExecutions" :key="ex.id">
                      <td>{{ ex.sceneName }}</td>
                      <td>
                        <span v-if="ex.status === 'success'" class="badge bg-success">成功</span>
                        <span v-else-if="ex.status === 'partial_success'" class="badge bg-warning text-dark">部分成功</span>
                        <span v-else-if="ex.status === 'failed'" class="badge bg-danger">失败</span>
                        <span v-else class="badge bg-primary">执行中</span>
                      </td>
                      <td>{{ ex.createdAt }}</td>
                      <td>{{ ex.durationMs }} ms</td>
                      <td class="text-end">
                        <a :href="ex.execUrl" class="btn btn-sm btn-outline-primary" target="_blank">
                          <i class="bi bi-eye"></i> 查看
                        </a>
                        <a :href="ex.designerUrl" class="btn btn-sm btn-outline-secondary ms-1" target="_blank">
                          <i class="bi bi-pencil"></i> 编排
                        </a>
                      </td>
                    </tr>
                    <tr v-if="!recentSceneExecutions.length">
                      <td colspan="5" class="text-center py-4">
                        <div class="text-muted">
                          <i class="bi bi-info-circle me-2"></i> 暂无使用此环境运行的场景记录
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </el-card>
          </div>
          <div class="col-md-12 mb-4">
            <el-card shadow="never">
              <template #header>
                <div class="clearfix">
                  <span>最近与此环境关联的测试运行</span>
                  <a :href="urls.testRunListFiltered" class="btn btn-sm btn-outline-primary float-end">查看全部</a>
                </div>
              </template>
              <div class="table-responsive">
                <table class="table table-hover">
                  <thead>
                    <tr>
                      <th>名称</th>
                      <th>项目</th>
                      <th>状态</th>
                      <th>开始时间</th>
                      <th>结束时间</th>
                      <th class="text-end">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="tr in recentTestRuns" :key="tr.id">
                      <td>{{ tr.name }}</td>
                      <td>{{ tr.projectName }}</td>
                      <td>
                        <span v-if="tr.status === 'completed'" class="badge bg-success">Completed</span>
                        <span v-else-if="tr.status === 'failed'" class="badge bg-danger">Failed</span>
                        <span v-else-if="tr.status === 'running'" class="badge bg-primary">Running</span>
                        <span v-else class="badge bg-secondary">Pending</span>
                      </td>
                      <td>{{ tr.startTime }}</td>
                      <td>{{ tr.endTime }}</td>
                      <td class="text-end">
                        <a :href="tr.detailUrl" class="btn btn-sm btn-outline-primary">
                          <i class="bi bi-eye"></i>
                        </a>
                      </td>
                    </tr>
                    <tr v-if="!recentTestRuns.length">
                      <td colspan="6" class="text-center py-4">
                        <div class="text-muted">
                          <i class="bi bi-info-circle me-2"></i> 没有与此环境关联的测试运行</div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="前置脚本" name="script">
        <el-card shadow="never">
          <template #header>
            <div class="clearfix">
              <span>前置脚本</span>
              <div class="float-end">
                <el-select
                  v-model="snippetChoice"
                  placeholder="插入代码片段"
                  size="small"
                  style="width: 140px"
                  class="me-2"
                  @change="onSnippetChange"
                >
                  <el-option label="插入代码片段" value="" disabled />
                  <el-option label="Token 刷新" value="token_refresh" />
                  <el-option label="签名生成" value="signature" />
                  <el-option label="请求头添加" value="request_header" />
                </el-select>
                <el-button size="small" type="primary" plain :loading="testing" @click="testScript">
                  <i class="bi bi-play-circle"></i> 测试脚本
                </el-button>
                <el-button size="small" type="primary" :loading="saving" @click="saveScript"><i class="bi bi-check-lg"></i> 保存</el-button>
              </div>
            </div>
          </template>
          <textarea
            id="pre-request-script-editor"
            ref="scriptTextarea"
            class="form-control font-monospace"
            rows="12"
            placeholder="// 使用 pm.environment、pm.request、pm.variables 预处理请求"
          />
          <div class="form-text mt-2">当前仅支持 ES5.1 语法。如执行出现错误，建议使用 AI 工具将脚本转换为 ES5.1 语法。</div>
          <div class="form-text mt-1">脚本超时: {{ environment.scriptTimeout }} ms（最多 1000ms）</div>
          <div v-show="scriptTestVisible" class="mt-3" v-html="scriptTestHtml" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import CodeMirror from "codemirror";
import "codemirror/lib/codemirror.css";
import "codemirror/mode/javascript/javascript.js";
import { ElMessage } from "element-plus";

const SNIPPETS = {
  token_refresh:
    "// 从环境变量读�?token 并写入请求头\nvar token = pm.environment.get('token');\nif (token) {\n    pm.request.headers.set('Authorization', 'Bearer ' + token);\n}",
  signature:
    "// 简单签名示例：时间�?密钥\nvar ts = Math.floor(Date.now() / 1000);\nvar secret = pm.environment.get('secret') || '';\npm.request.params.set('timestamp', ts);\npm.request.params.set('sign', ts + secret);",
  request_header:
    "// 添加通用请求头\npm.request.headers.set('X-Request-Id', 'req-' + Date.now());\npm.request.headers.set('X-Client', 'EasyTesting');",
};

function getCsrfToken() {
  const inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (inp) return inp.value;
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1].trim() : "";
}

export default {
  name: "EnvironmentDetail",
  props: {
    initial: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      activeTab: "overview",
      environment: this.initial.environment || {},
      project: this.initial.project || {},
      variablesRows: this.initial.variablesRows || [],
      hasVariables: !!this.initial.hasVariables,
      recentSceneExecutions: this.initial.recentSceneExecutions || [],
      recentTestRuns: this.initial.recentTestRuns || [],
      urls: this.initial.urls || {},
      apiBase: this.initial.apiBase || "/api/v1/environments",
      envVarsForScriptTest: this.initial.envVarsForScriptTest || {},
      scriptEditor: null,
      scriptSavedValue: (this.initial.environment && this.initial.environment.preRequestScript) || "",
      scriptDirty: false,
      scriptTestVisible: false,
      scriptTestHtml: "",
      snippetChoice: "",
      saving: false,
      testing: false,
    };
  },
  watch: {
    activeTab(newVal, oldVal) {
      if (oldVal === "script" && newVal !== "script" && this.scriptDirty) {
        this.saveScriptSilent();
      }
      if (newVal === "script" && this.scriptEditor) {
        this.$nextTick(() => {
          this.scriptEditor.refresh();
        });
      }
    },
  },
  mounted() {
    const self = this;
    this.$nextTick(() => {
      const ta = self.$refs.scriptTextarea;
      const initialScript = (self.environment && self.environment.preRequestScript) || "";
      if (ta) ta.value = initialScript;
      if (ta) {
        self.scriptEditor = CodeMirror.fromTextArea(ta, {
          mode: "javascript",
          lineNumbers: true,
          indentUnit: 4,
          theme: "default",
        });
        self.scriptEditor.setValue(initialScript);
        self.scriptEditor.on("change", () => {
          self.scriptDirty = self.scriptEditor.getValue() !== self.scriptSavedValue;
        });
      }
      self.scriptSavedValue = self.getScriptFromEditor();
    });
    window.addEventListener("beforeunload", (e) => {
      if (self.scriptDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    });
  },
  methods: {
    getScriptFromEditor() {
      if (this.scriptEditor) return this.scriptEditor.getValue();
      const ta = this.$refs.scriptTextarea;
      return ta ? ta.value : "";
    },
    setScriptToEditor(text) {
      if (this.scriptEditor) this.scriptEditor.setValue(text);
      else if (this.$refs.scriptTextarea) this.$refs.scriptTextarea.value = text;
    },
    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(
        () => {
          ElMessage.success("Base URL 已复制到剪贴板");
        },
        (err) => {
          console.error(err);
          ElMessage.error("复制失败");
        }
      );
    },
    saveScriptSilent() {
      const script = this.getScriptFromEditor();
      return fetch(`${this.apiBase}/${this.environment.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({ pre_request_script: script }),
      }).then((r) => {
        if (r.ok) {
          this.scriptSavedValue = script;
          this.scriptDirty = false;
        }
        return r;
      });
    },
    saveScript() {
      const script = this.getScriptFromEditor();
      this.saving = true;
      this.scriptTestVisible = true;
      fetch(`${this.apiBase}/${this.environment.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({ pre_request_script: script }),
      })
        .then((r) => r.json().then((data) => ({ ok: r.ok, data, status: r.status })))
        .then((res) => {
          if (res.ok) {
            this.scriptSavedValue = script;
            this.scriptDirty = false;
            this.scriptTestHtml = '<div class="alert alert-success">保存成功</div>';
          } else {
            this.scriptTestHtml = `<div class="alert alert-danger">保存失败: ${
              res.data && res.data.detail ? JSON.stringify(res.data.detail) : res.status
            }</div>`;
          }
        })
        .catch((e) => {
          this.scriptTestHtml = `<div class="alert alert-danger">保存失败: ${e.message}</div>`;
        })
        .finally(() => {
          this.saving = false;
        });
    },
    testScript() {
      const self = this;
      const script = this.getScriptFromEditor();
      this.testing = true;
      this.scriptTestVisible = true;
      this.scriptTestHtml = '<div class="text-muted"><i class="bi bi-hourglass-split"></i> 执行中...</div>';
      const ctrl = new AbortController();
      const timeoutId = setTimeout(() => ctrl.abort(), 15000);
      fetch(`${this.apiBase}/${this.environment.id}/test-pre-request-script/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
        body: JSON.stringify({
          script,
          env_vars: self.envVarsForScriptTest,
          script_timeout: self.environment.scriptTimeout,
        }),
        signal: ctrl.signal,
      })
        .then((r) => r.json())
        .then((data) => {
          clearTimeout(timeoutId);
          if (data.success) {
            let html = '<div class="alert alert-success"><strong>执行成功</strong></div>';
            if (data.console && data.console.length) {
              html +=
                '<div class="mb-2"><strong>Console 输出：</strong><pre class="bg-light p-2 rounded small mb-0" style="max-height:150px;overflow:auto;">';
              data.console.forEach((c) => {
                const cls = c.level === "error" ? "text-danger" : c.level === "warn" ? "text-warning" : "";
                html += `<span class="${cls}">[${c.level || "log"}] ${String(c.msg || "").replace(/</g, "&lt;")}</span>\n`;
              });
              html += "</pre></div>";
            }
            if (data.logs && data.logs.length) {
              html +=
                '<div><strong>变量变更</strong></div><table class="table table-sm"><thead><tr><th>类型</th><th>Key</th><th>旧值</th><th>新值</th></tr></thead><tbody>';
              data.logs.forEach((l) => {
                html += `<tr><td>${l.type || "-"}</td><td><code>${l.key || ""}</code></td><td><code>${JSON.stringify(
                  l.old
                )}</code></td><td><code>${JSON.stringify(l.new)}</code></td></tr>`;
              });
              html += "</tbody></table>";
            }
            if (!(data.console && data.console.length) && (!data.logs || !data.logs.length)) {
              html += '<div class="text-muted">无变量变更，无 Console 输出</div>';
            }
            self.scriptTestHtml = html;
          } else {
            let errHtml = `<div class="alert alert-danger">${data.error || "执行失败"}</div>`;
            if (data.console && data.console.length) {
              errHtml += '<div class="mt-2"><strong>Console 输出：</strong><pre class="bg-light p-2 rounded small">';
              data.console.forEach((c) => {
                errHtml += `[${c.level || "log"}] ${c.msg || ""}\n`;
              });
              errHtml += "</pre></div>";
            }
            self.scriptTestHtml = errHtml;
          }
        })
        .catch((e) => {
          clearTimeout(timeoutId);
          let errMsg = e.message || "未知错误";
          if (e.name === "AbortError") {
            errMsg = "请求超时（5秒），请检查后端服务是否正常运行";
          } else if (e.message === "Failed to fetch") {
            errMsg =
              "网络请求失败。请检查：1) 后端服务是否已启动；2) 当前访问地址是否在 ALLOWED_HOSTS 中；3) 是否已安装 py-mini-racer (pip install py-mini-racer)";
          }
          self.scriptTestHtml = `<div class="alert alert-danger"><strong>请求失败</strong>: ${errMsg}</div>`;
        })
        .finally(() => {
          self.testing = false;
        });
    },
    onSnippetChange(val) {
      if (!val || !SNIPPETS[val]) return;
      const content = this.getScriptFromEditor();
      const insert = (content ? "\n\n" : "") + SNIPPETS[val];
      this.setScriptToEditor(content + insert);
      this.scriptDirty = true;
      this.snippetChoice = "";
    },
  },
};
</script>

<style scoped>
[v-cloak] {
  display: none;
}
</style>
