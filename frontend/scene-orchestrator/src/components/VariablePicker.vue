<template>
  <div class="variable-picker-inline">
    <el-input
      :model-value="displayText"
      readonly
      placeholder="点击选择变量引用"
      @focus="openPicker"
      @click="openPicker"
    >
      <template #append>
        <el-button @click.stop="openPicker">选择</el-button>
      </template>
    </el-input>

    <el-dialog
      v-model="dialogVisible"
      title="选择变量引用"
      width="680px"
      :close-on-click-modal="true"
      destroy-on-close
      append-to-body
      class="variable-picker-dialog"
      @close="handleDialogClose"
    >
      <div class="variable-picker-panel">
        <div class="picker-toolbar">
          <el-input
            v-model="keyword"
            clearable
            size="small"
            placeholder="搜索字段名/路径"
            class="picker-search"
          />
          <div class="picker-tabs-row">
            <el-tag
              v-for="(items, kind) in groupedOptions"
              :key="kind"
              v-show="items.length"
              :type="activeKind === kind ? kindTagType(kind) : 'info'"
              :effect="activeKind === kind ? 'dark' : 'plain'"
              size="small"
              class="picker-tab-tag"
              @click="activeKind = kind"
            >
              {{ kind }} ({{ items.length }})
            </el-tag>
          </div>
        </div>
        <el-table
          v-if="!loading && !loadError && filteredOptions.length"
          :data="currentKindItems"
          :max-height="360"
          highlight-current-row
          size="small"
          class="picker-table"
          @row-click="emitPick($event.value)"
        >
          <el-table-column label="变量名 / 路径" min-width="260" prop="label" show-overflow-tooltip />
          <el-table-column label="类型" width="130" prop="kindText">
            <template #default="{ row }">
              <el-tag size="small" :type="kindTagType(row.kindText)">{{ row.kindText }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="值类型" width="90" prop="valueType" align="center">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.valueType || "unknown" }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div v-else-if="loading" class="picker-empty">字段加载中...</div>
        <div v-else-if="loadError" class="picker-empty picker-error">{{ loadError }}</div>
        <div v-else-if="!currentKindItems.length && !loading" class="picker-empty">暂无可插入变量</div>
      </div>
      <template #footer>
        <el-button @click="closePicker">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { fetchSceneVariableFields } from "../api/scene";

const props = defineProps({
  options: {
    type: Array,
    default: () => []
  },
  visible: {
    type: Boolean,
    default: false
  },
  modelValue: {
    type: String,
    default: ""
  },
  sceneId: {
    type: [Number, String],
    default: null
  },
  currentNodeId: {
    type: [Number, String],
    default: null
  },
  environmentId: {
    type: [Number, String],
    default: null
  }
});

const emit = defineEmits(["pick", "close", "update:visible"]);
const keyword = ref("");
const loading = ref(false);
const loadError = ref("");
const remoteOptions = ref([]);
const activeKind = ref("");

const dialogVisible = computed({
  get: () => props.visible,
  set: (v) => emit("update:visible", v)
});

const normalizedOptions = computed(() => {
  const merged = [...remoteOptions.value, ...props.options];
  return merged.map((item) => {
    if (typeof item === "string") {
      return {
        label: item,
        value: item,
        kindText: "变量",
        valueType: guessValueType(item)
      };
    }
    return {
      label: item.label || item.value || "",
      value: item.value || "",
      kindText: item.kindText || "变量",
      valueType: item.valueType || guessValueType(item.value || item.label || "")
    };
  });
});

const filteredOptions = computed(() => {
  const q = keyword.value.trim().toLowerCase();
  if (!q) {
    return normalizedOptions.value;
  }
  return normalizedOptions.value.filter((item) =>
    `${item.label} ${item.value}`.toLowerCase().includes(q)
  );
});

// 分组顺序：debugtalk 函数 → 环境变量 → 场景变量 → 前置变量 → 节点变量 → 其他
const KIND_ORDER = ["debugtalk 函数", "环境变量", "场景变量", "前置变量", "节点变量", "变量"];

const groupedOptions = computed(() => {
  const groups = {};
  KIND_ORDER.forEach((k) => { groups[k] = []; });
  filteredOptions.value.forEach((item) => {
    const kind = item.kindText || "变量";
    if (!groups[kind]) groups[kind] = [];
    groups[kind].push(item);
  });
  return groups;
});

const currentKindItems = computed(() => {
  const groups = groupedOptions.value;
  if (activeKind.value && groups[activeKind.value]) {
    return groups[activeKind.value];
  }
  // 无选中分类时展示全部
  return filteredOptions.value;
});

function kindTagType(kind) {
  const map = {
    "debugtalk 函数": "success",
    "环境变量": "warning",
    "场景变量": "primary",
    "前置变量": "info",
    "节点变量": ""
  };
  return map[kind] ?? "info";
}

const displayText = computed(() => props.modelValue || "");

watch(
  () => props.visible,
  (value) => {
    if (value) {
      loadFields();
    }
  },
  { immediate: true }
);

function openPicker() {
  emit("update:visible", true);
  loadFields();
}

function closePicker() {
  emit("update:visible", false);
  emit("close");
}

function handleDialogClose() {
  closePicker();
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      const groups = groupedOptions.value;
      const first = KIND_ORDER.find((k) => groups[k]?.length);
      activeKind.value = first || Object.keys(groups).find((k) => groups[k]?.length) || "";
    } else {
      activeKind.value = "";
    }
  },
  { immediate: true }
);

async function loadFields() {
  if (!props.sceneId) {
    return;
  }
  loading.value = true;
  loadError.value = "";
  try {
    const data = await fetchSceneVariableFields(props.sceneId, props.currentNodeId, props.environmentId);
    const paths = Array.isArray(data?.sample) ? data.sample : [];
    // 统一转成 picker 项，便于父组件直接复用 value
    remoteOptions.value = paths.map((path) => ({
      label: path,
      value: `{{${path}}}`,
      kindText: path.startsWith("env.") ? "环境变量"
        : path.startsWith("scene.") ? "场景变量"
        : "节点变量",
      valueType: guessValueType(path)
    }));
  } catch (error) {
    loadError.value = "字段预览加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
}

function guessValueType(pathText) {
  const text = String(pathText || "").toLowerCase();
  if (text.includes(".id") || text.includes(".count") || text.includes(".total")) {
    return "number";
  }
  if (text.includes(".is_") || text.includes(".enabled") || text.includes(".success")) {
    return "boolean";
  }
  if (text.includes(".list") || text.includes(".items") || text.endsWith(".0")) {
    return "array";
  }
  if (text.includes(".data") || text.includes(".body")) {
    return "object";
  }
  return "string";
}

function emitPick(value) {
  emit("pick", value);
  closePicker();
}
</script>
