/**
 * 与场景编排等页一致的提示：可手动关闭、约 3 秒收起
 */
import { ElMessage, ElMessageBox } from "element-plus";

const MSG = {
  duration: 3000,
  showClose: true
};

export function msgSuccess(message) {
  return ElMessage.success({ message, ...MSG });
}

export function msgWarning(message) {
  return ElMessage.warning({ message, ...MSG });
}

export function msgError(message) {
  return ElMessage.error({ message, ...MSG });
}

/** 与 SceneDesigner 中 ElMessageBox.confirm 一致：标题「提示」、警告样式 */
export function confirmWarning(message, title = "提示") {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
    closeOnClickModal: false,
    autofocus: false
  });
}
