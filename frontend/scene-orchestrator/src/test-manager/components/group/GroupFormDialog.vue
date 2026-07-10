<template>
  <el-dialog v-model="visible" :title="editing ? '编辑分组' : '新建分组'" width="460px" @close="reset">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="分组名称" maxlength="100" />
      </el-form-item>
      <el-form-item label="父分组">
        <el-select v-model="form.parent" placeholder="无（顶级分组）" clearable style="width:100%">
          <el-option label="无（顶级分组）" :value="null" />
          <el-option v-for="p in availableParents" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible=false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  editing: Object,
  projectId: Number,
  groups: { type: Array, default: () => [] },
  type: { type: String, required: true }, // 'testCase' | 'testSuite'
})
const emit = defineEmits(['update:modelValue', 'saved'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref(null)
const submitting = ref(false)
const form = reactive({ name: '', parent: null })
const rules = { name: [{ required: true, message: '请输入名称', trigger: 'blur' }] }

// 可用父分组（排除自身及子孙）
const availableParents = computed(() => {
  const excludeIds = new Set()
  if (props.editing) {
    excludeIds.add(props.editing.id)
    const walk = (nodes) => { nodes.forEach(n => { excludeIds.add(n.id); if (n.children) walk(n.children) }) }
    const findSub = (nodes, id) => {
      for (const n of nodes) { if (n.id === id) { if (n.children) walk(n.children); return true }; if (n.children && findSub(n.children, id)) return true }
      return false
    }
    findSub(props.groups, props.editing.id)
  }
  return props.groups.filter(g => !excludeIds.has(g.id))
})

watch(visible, (v) => {
  if (v) {
    form.name = props.editing?.name || ''
    form.parent = props.editing?.parent || null
  }
})

function reset() {
  formRef.value?.resetFields()
}

async function submit() {
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  submitting.value = true
  try { emit('saved', { ...form, id: props.editing?.id }); visible.value = false }
  catch (e) { ElMessage.error(e.message) }
  finally { submitting.value = false }
}
</script>
