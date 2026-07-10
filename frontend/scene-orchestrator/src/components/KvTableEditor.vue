<template>
  <div class="kv-table-wrap" style="width:100%">
    <table class="kv-table" style="width:100%" :class="{ 'kv-table-typed': variant === 'typed' }">
      <thead>
        <tr>
          <th :style="{ width: variant === 'typed' ? '25%' : '32%' }">Key</th>
          <th v-if="variant === 'typed'" style="width:10%">类型</th>
          <th :style="{ width: variant === 'typed' ? '58%' : '61%' }">Value</th>
          <th style="width:7%" class="text-center">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in modelValue" :key="`${rowKey}-${idx}`">
          <td><input v-model="row.key" class="form-control form-control-sm" placeholder="key" @input="emitChange" /></td>
          <td v-if="variant === 'typed'">
            <el-select v-model="row.type" size="small" popper-class="scene-select-popper" class="row-type-select" @change="emitChange">
              <el-option v-for="opt in typeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </td>
          <td>
            <template v-if="variant === 'typed' && row.type === 'file'">
              <div class="d-flex flex-column gap-1">
                <div v-if="row.value" class="text-success small">
                  <i class="bi bi-check-circle"></i> 已上传: {{ row.fileName || (row.value ? row.value.split(/[/\\]/).pop() : '') }}
                </div>
                <div class="d-flex gap-1 align-items-center">
                  <input v-model="row.value" class="form-control form-control-sm flex-grow-1" placeholder="上传后的文件路径" readonly />
                  <button type="button" class="btn btn-sm btn-outline-secondary" @click="handleFileUpload(row)">上传</button>
                </div>
              </div>
            </template>
            <input
              v-else
              v-model="row.value"
              class="form-control form-control-sm"
              :placeholder="variant === 'typed' && row.type === 'number' ? '数字' : 'value'"
              @focus="$emit('row-focus', idx)"
              @input="emitChange"
            />
          </td>
          <td class="text-center"><button class="btn btn-sm btn-outline-danger" @click="removeRow(idx)">删</button></td>
        </tr>
      </tbody>
    </table>
    <button class="btn btn-sm btn-outline-primary mt-1" @click="addRow">{{ addLabel }}</button>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus";
import { uploadFile } from "../api/scene";

const props = defineProps({
  modelValue: { type: Array, default: () => [{ key: "", value: "" }] },
  variant: { type: String, default: "simple" }, // "simple" | "typed"
  typeOptions: { type: Array, default: () => [
    { value: "string", label: "string" },
    { value: "number", label: "number" },
    { value: "boolean", label: "boolean" },
    { value: "file", label: "file" },
    { value: "array", label: "array" },
    { value: "object", label: "object" }
  ]},
  rowKey: { type: String, default: "kv" },
  addLabel: { type: String, default: "+ 新增" }
});

const emit = defineEmits(["update:modelValue", "row-focus"]);

function emitChange() {
  emit("update:modelValue", [...props.modelValue]);
}

function addRow() {
  const newRow = props.variant === "typed"
    ? { key: "", value: "", type: "string" }
    : { key: "", value: "" };
  const next = [...props.modelValue, newRow];
  emit("update:modelValue", next);
}

function removeRow(index) {
  const next = [...props.modelValue];
  next.splice(index, 1);
  if (!next.length) {
    next.push(props.variant === "typed" ? { key: "", value: "", type: "string" } : { key: "", value: "" });
  }
  emit("update:modelValue", next);
}

async function handleFileUpload(row) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "*/*";
  input.onchange = async (e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    try {
      const res = await uploadFile(file);
      if (res?.success && res?.file_path) {
        row.value = res.file_path;
        row.fileName = res.file_name || file.name;
        row.type = "file";
        emitChange();
      } else {
        ElMessage.error(res?.detail || "上传失败");
      }
    } catch (err) {
      ElMessage.error(err?.message || "上传失败");
    }
  };
  input.click();
}
</script>
