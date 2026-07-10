<template>
  <div class="asset-tree">
    <div class="mb-2">
      <input v-model="keyword" class="form-control form-control-sm" placeholder="搜索API资产" />
    </div>
    <div class="group-list">
      <div v-for="group in treeGroups" :key="group.id || 'root'" class="group-block">
        <button type="button" class="group-title group-toggle" @click="toggleGroup(group.id)">
          <span>{{ expandedGroupSet.has(group.id) ? "▾" : "▸" }}</span>
          <span>{{ group.name }}</span>
          <small class="text-muted">({{ group.assets.length }})</small>
        </button>
        <div v-if="expandedGroupSet.has(group.id)" class="asset-list">
          <div
            v-for="asset in group.assets"
            :key="asset.id"
            :class="['asset-item', { disabled: isAssetDisabled(asset) }]"
            :draggable="!isAssetDisabled(asset)"
            @dragstart="onDragAsset(asset, $event)"
          >
            <span class="asset-text">{{ asset.name }}</span>
            <span v-if="isAssetDisabled(asset)" class="asset-disabled-tag">禁用</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  assets: {
    type: Array,
    default: () => []
  },
  groups: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["drag-asset"]);
const keyword = ref("");
const expandedGroupSet = ref(new Set());

const treeGroups = computed(() => {
  const groupMap = new Map();
  (props.groups || []).forEach((group) => {
    groupMap.set(group.id, {
      id: group.id,
      name: group.name,
      assets: []
    });
  });

  const root = {
    id: null,
    name: "API资产",
    assets: []
  };
  const q = keyword.value.trim().toLowerCase();
  (props.assets || []).forEach((asset) => {
    if (q && !`${asset.name}`.toLowerCase().includes(q)) {
      return;
    }
    const target = groupMap.get(asset.group_id) || root;
    target.assets.push(asset);
  });

  return [...groupMap.values(), root].filter((group) => group.assets.length > 0);
});

watch(
  treeGroups,
  (value) => {
    const next = new Set(expandedGroupSet.value);
    value.forEach((group) => {
      if (!next.has(group.id)) {
        next.add(group.id);
      }
    });
    expandedGroupSet.value = next;
  },
  { immediate: true }
);

function toggleGroup(groupId) {
  const next = new Set(expandedGroupSet.value);
  if (next.has(groupId)) {
    next.delete(groupId);
  } else {
    next.add(groupId);
  }
  expandedGroupSet.value = next;
}

function isAssetDisabled(asset) {
  const status = String(asset?.status || "").toLowerCase();
  const paramStatus = String(asset?.param_status || "").toLowerCase();
  return status === "inactive" || status === "disabled" || paramStatus === "disabled";
}

function onDragAsset(asset, event) {
  if (isAssetDisabled(asset)) {
    event.preventDefault();
    return;
  }
  const payload = {
    type: "api",
    id: asset.id
  };
  emit("drag-asset", payload);
  // 拖拽只传最小字段，避免序列化大对象导致卡顿。
  event.dataTransfer.setData("application/json", JSON.stringify(payload));
  event.dataTransfer.setData("application/x-scene-asset", JSON.stringify(payload));
  event.dataTransfer.setData("text/plain", JSON.stringify(payload));
}
</script>
