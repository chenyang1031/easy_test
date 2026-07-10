import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { fetchSceneDetail, fetchSceneNodes, updateScene } from "../api/scene";

export const useSceneStore = defineStore("scene", () => {
  const currentSceneId = ref(null);
  const scene = ref({
    name: "",
    description: "",
    variables: {}
  });
  const nodeList = ref([]);
  const variablePool = ref({});
  const sceneVariablePool = ref({});
  const selectedNodeId = ref(null);
  const dirty = ref(false);
  const saving = ref(false);
  const lastSavedAt = ref("");

  const selectedNode = computed(() => nodeList.value.find((item) => item.id === selectedNodeId.value) || null);

  function markDirty() {
    dirty.value = true;
  }

  function setSelectedNode(nodeId) {
    if (nodeId === null || nodeId === undefined) {
      selectedNodeId.value = null;
      return;
    }
    selectedNodeId.value = Number(nodeId) || null;
  }

  function setSelectedNodeId(nodeId) {
    setSelectedNode(nodeId);
  }

  function upsertNode(node, shouldMarkDirty = false) {
    const nextNode = { ...(node || {}) };
    const idx = nodeList.value.findIndex((item) => item.id === nextNode.id);
    const nextList = [...nodeList.value];
    if (idx === -1) {
      nextList.push(nextNode);
    } else {
      nextList[idx] = { ...nextList[idx], ...nextNode };
    }
    nextList.sort((a, b) => (a.sort || 0) - (b.sort || 0));
    nodeList.value = nextList;
    updateSceneVariablePoolFromNode(nextNode);
    if (shouldMarkDirty) {
      markDirty();
    }
  }

  function removeNode(nodeId, shouldMarkDirty = false) {
    nodeList.value = nodeList.value.filter((item) => item.id !== nodeId);
    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = null;
    }
    buildSceneVariablePool();
    if (shouldMarkDirty) {
      markDirty();
    }
  }

  function updateNodeLocal(nodeId, patch, shouldMarkDirty = true) {
    const idx = nodeList.value.findIndex((item) => item.id === nodeId);
    if (idx === -1) {
      return;
    }
    // 创建新数组以触发 watcher，避免 deep: true
    const nextList = [...nodeList.value];
    nextList[idx] = { ...nextList[idx], ...patch };
    nodeList.value = nextList;
    if (shouldMarkDirty) {
      markDirty();
    }
  }

  function setNodeList(nodes) {
    nodeList.value = [...nodes].sort((a, b) => (a.sort || 0) - (b.sort || 0));
    buildSceneVariablePool();
  }

  function buildSceneVariablePool() {
    const pool = {};
    (nodeList.value || []).forEach((node) => {
      const key = node.node_key || `node_${node.id}`;
      const rules = node.extract_rules;
      if (!Array.isArray(rules) || rules.length === 0) {
        pool[key] = {};
        return;
      }
      const vars = {};
      rules.forEach((r) => {
        const name = String(r?.name || "").trim();
        if (name) {
          vars[name] = String(r?.path || "").trim() || "$.response";
        }
      });
      pool[key] = vars;
    });
    sceneVariablePool.value = pool;
  }

  function updateSceneVariablePoolFromNode(node) {
    if (!node) return;
    const key = node.node_key || `node_${node.id}`;
    const rules = node.extract_rules;
    const vars = {};
    if (Array.isArray(rules)) {
      rules.forEach((r) => {
        const name = String(r?.name || "").trim();
        if (name) {
          vars[name] = String(r?.path || "").trim() || "$.response";
        }
      });
    }
    sceneVariablePool.value = { ...sceneVariablePool.value, [key]: vars };
  }

  function buildVariableTree() {
    const tree = {};
    nodeList.value.forEach((node) => {
      const key = node.node_key || `node_${node.id}`;
      tree[key] = {
        response: {
          data: {},
          headers: {}
        }
      };
    });
    variablePool.value = {
      ...(scene.value?.variables || {}),
      ...tree
    };
  }

  async function loadScene(sceneId) {
    currentSceneId.value = Number(sceneId);
    const [sceneData, nodes] = await Promise.all([
      fetchSceneDetail(sceneId),
      fetchSceneNodes(sceneId)
    ]);
    scene.value = sceneData;
    setNodeList(nodes.results || nodes || []);
    selectedNodeId.value = nodeList.value[0]?.id || null;
    buildVariableTree();
    dirty.value = false;
  }

  async function flushSave() {
    if (!dirty.value || !scene.value) {
      return;
    }
    saving.value = true;
    try {
      const updated = await updateScene(scene.value.id, {
        project: scene.value.project,
        name: scene.value.name,
        description: scene.value.description,
        group: scene.value.group,
        variables: scene.value.variables || {},
        runtime_config: scene.value.runtime_config || {},
        is_active: scene.value.is_active
      });
      if (updated && typeof updated === "object") {
        scene.value = { ...scene.value, ...updated };
      }
      dirty.value = false;
      lastSavedAt.value = new Date().toLocaleTimeString();
    } finally {
      saving.value = false;
    }
  }

  function attachBeforeUnloadGuard() {
    window.addEventListener("beforeunload", onBeforeUnload);
  }

  function detachBeforeUnloadGuard() {
    window.removeEventListener("beforeunload", onBeforeUnload);
  }

  function onBeforeUnload(event) {
    if (!dirty.value) {
      return;
    }
    event.preventDefault();
    event.returnValue = "";
  }

  return {
    currentSceneId,
    scene,
    nodeList,
    variablePool,
    sceneVariablePool,
    selectedNodeId,
    selectedNode,
    dirty,
    saving,
    lastSavedAt,
    loadScene,
    setSelectedNode,
    setSelectedNodeId,
    upsertNode,
    removeNode,
    updateNodeLocal,
    setNodeList,
    buildVariableTree,
    markDirty,
    flushSave,
    attachBeforeUnloadGuard,
    detachBeforeUnloadGuard
  };
});
