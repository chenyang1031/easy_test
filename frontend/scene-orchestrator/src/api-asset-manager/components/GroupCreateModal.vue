<template>
  <el-dialog
    v-model="visible"
    title="新建分组"
    width="420px"
    :close-on-click-modal="false"
    @open="resetForm"
  >
    <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
      <el-form-item label="分组名称" required>
        <el-input
          v-model="form.name"
          placeholder="请输入分组名称"
          maxlength="100"
          ref="nameInputRef"
        />
      </el-form-item>
      <el-form-item label="父分组">
        <el-select
          v-model="form.parentId"
          placeholder="根目录"
          clearable
          style="width:100%"
        >
          <el-option
            v-for="g in parentOptions"
            :key="g.id"
            :label="g.displayName"
            :value="g.id"
          />
        </el-select>
      </el-form-item>
    </el-form>

    <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        创建
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useApiAssetStore } from '../stores/apiAsset.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const store = useApiAssetStore()
const nameInputRef = ref(null)
const submitting = ref(false)
const errorMsg = ref('')
const form = ref({ name: '', parentId: null })

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const parentOptions = computed(() => {
  return store.flatGroupList.map(g => ({
    id: g.id,
    displayName: g.displayName
  }))
})

function resetForm() {
  form.value = { name: '', parentId: null }
  errorMsg.value = ''
  nextTick(() => {
    nameInputRef.value?.focus()
  })
}

async function handleSubmit() {
  const name = (form.value.name || '').trim()
  if (!name) {
    errorMsg.value = '请输入分组名称'
    return
  }
  if (!store.currentProjectId) {
    errorMsg.value = '请先选择项目'
    return
  }

  submitting.value = true
  errorMsg.value = ''
  try {
    await store.createGroup(name, form.value.parentId)
    visible.value = false
  } catch (e) {
    errorMsg.value = e?.message || '创建失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.error-msg {
  color: #f56c6c;
  font-size: 13px;
  margin-top: -8px;
}
</style>
