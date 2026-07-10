import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import ApifoxEnvImportPanel from "../components/ApifoxEnvImportPanel.vue";

let rootApp = null;

/**
 * 挂载 Apifox 环境变量导入预览（API 资产管理导入弹窗内）
 * @param {HTMLElement} el
 * @param {{ environmentImport: object, platformProjectId: number|null, onGateChange?: () => void }} props
 */
export function mountApifoxEnvImportApp(el, props) {
  unmountApifoxEnvImportApp();
  if (!el) return;
  const app = createApp(ApifoxEnvImportPanel, props || {});
  app.use(ElementPlus, { locale: zhCn });
  app.mount(el);
  rootApp = app;
}

export function unmountApifoxEnvImportApp() {
  if (rootApp) {
    rootApp.unmount();
    rootApp = null;
  }
}

/* 供 Django 模板以 <script type="module" src> 加载；避免仅 export 被 Rollup 摇树移除 */
if (typeof window !== "undefined") {
  window.mountApifoxEnvImportApp = mountApifoxEnvImportApp;
  window.unmountApifoxEnvImportApp = unmountApifoxEnvImportApp;
}
