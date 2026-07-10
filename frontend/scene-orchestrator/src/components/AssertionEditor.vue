<template>
  <div class="assertion-editor">
    <div class="assertion-head">
      <strong>断言规则</strong>
      <div class="assertion-actions">
        <el-button size="small" @click="addTemplate('status200')">模板: 状态码200</el-button>
        <el-button size="small" @click="addTemplate('successCode')">模板: 业务 code=200</el-button>
        <el-button size="small" type="primary" @click="addRule">新增断言</el-button>
      </div>
    </div>

    <div class="assertion-tip">
      <el-alert type="info" :closable="false" show-icon>
        <template #title>
          <span>校验路径说明：</span>
          <code>$.status_code</code>、<code>$.response.code</code> ...
          <span class="assertion-tip-dl">
            <br />
            <span>若节点为文件下载接口，额外支持：</span>
            <code>$.download_file.md5</code>（MD5 校验）、
            <code>$.download_file.file_size</code>（文件大小，字节）、
            <code>$.download_file.filename</code>（文件名）
          </span>
        </template>
      </el-alert>
    </div>

    <el-table :data="localRules" size="small" border stripe empty-text="暂无断言规则">
      <el-table-column label="校验维度" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.path" placeholder="如 $.status_code、$.response.code（body 在 response 下，勿写 $.response.body）" />
        </template>
      </el-table-column>
      <el-table-column label="操作符" width="140">
        <template #default="{ row }">
          <el-select v-model="row.comparator" placeholder="操作符" popper-class="scene-select-popper" transition="el-fade-in">
            <el-option v-for="item in operators" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="期望值" min-width="120">
        <template #default="{ row }">
          <el-input v-model="row.expected" placeholder="期望值" />
        </template>
      </el-table-column>
      <el-table-column label="说明" width="120">
        <template #default="{ row }">
          <el-input v-model="row.description" placeholder="Description" />
        </template>
      </el-table-column>
      <el-table-column label="失败策略" width="120">
        <template #default="{ row }">
          <el-select v-model="row.on_failed" popper-class="scene-select-popper" transition="el-fade-in">
            <el-option label="失败终止" value="stop" />
            <el-option label="失败继续" value="continue" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="70" align="center">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removeRule($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { nextTick, ref, watch } from "vue";

const MAX_ASSERT_RULES = 50;

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["update:modelValue"]);
const localRules = ref([]);
const isSyncingFromProps = ref(false);
const operators = [
  { label: "等于", value: "eq" },
  { label: "不等于", value: "ne" },
  { label: "包含", value: "contains" },
  { label: "大于", value: "gt" },
  { label: "大于等于", value: "ge" },
  { label: "小于", value: "lt" },
  { label: "小于等于", value: "le" },
  { label: "以...开头", value: "startswith" },
  { label: "以...结尾", value: "endswith" },
  { label: "正则匹配", value: "regex_match" },
  { label: "长度等于", value: "length_eq" },
  { label: "长度大于", value: "length_gt" },
  { label: "长度大于等于", value: "length_ge" },
  { label: "长度小于", value: "length_lt" },
  { label: "长度小于等于", value: "length_le" }
];

function normalizeRule(item) {
  return {
    path: item.path || "",
    comparator: item.comparator || "eq",
    expected: item.expected ?? "",
    description: item.description || "",
    enabled: item.enabled !== false,
    on_failed: item.on_failed === "continue" ? "continue" : "stop"
  };
}

watch(
  () => props.modelValue,
  (value) => {
    isSyncingFromProps.value = true;
    try {
      localRules.value = Array.isArray(value)
        ? value.map((item) => normalizeRule(item))
        : [];
    } finally {
      nextTick(() => {
        isSyncingFromProps.value = false;
      });
    }
  },
  { immediate: true, deep: true }
);

watch(
  localRules,
  (value) => {
    if (isSyncingFromProps.value) return;
    try {
      emit(
        "update:modelValue",
        value.map((item) => ({
          path: item.path,
          comparator: item.comparator,
          expected: item.expected,
          description: item.description || "",
          enabled: item.enabled !== false,
          on_failed: item.on_failed === "continue" ? "continue" : "stop"
        }))
      );
    } catch (err) {
      console.error("AssertionEditor emit error:", err);
    }
  },
  { deep: true }
);

function addRule() {
  try {
    if (localRules.value.length >= MAX_ASSERT_RULES) {
      ElMessage.warning(`断言规则最多 ${MAX_ASSERT_RULES} 条`);
      return;
    }
    localRules.value.push({
      path: "$.status_code",
      comparator: "eq",
      expected: "200",
      description: "",
      enabled: true,
      on_failed: "stop"
    });
  } catch (error) {
    console.error("新增断言失败:", error);
    ElMessage.error("新增断言失败");
  }
}

function removeRule(index) {
  localRules.value.splice(index, 1);
}

function addTemplate(templateKey) {
  try {
    if (localRules.value.length >= MAX_ASSERT_RULES) {
      ElMessage.warning(`断言规则最多 ${MAX_ASSERT_RULES} 条`);
      return;
    }
    const templates = {
      status200: { path: "$.status_code", comparator: "eq", expected: "200", description: "", enabled: true, on_failed: "stop" },
      // 与 scene_engine 中 node_context.response 一致：即为 JSON 根，无额外 .body 层
      successCode: { path: "$.response.code", comparator: "eq", expected: "200", description: "", enabled: true, on_failed: "stop" }
    };
    const tpl = templates[templateKey];
    if (!tpl) {
      ElMessage.warning("未知的断言模板");
      return;
    }
    localRules.value.push({ ...tpl });
  } catch (error) {
    console.error("添加断言模板失败:", error);
    ElMessage.error("添加断言模板失败");
  }
}
</script>
