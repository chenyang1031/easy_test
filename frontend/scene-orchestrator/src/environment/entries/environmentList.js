import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import EnvironmentList from "../components/EnvironmentList.vue";

const el = document.getElementById("environment-list-mount");
if (el) {
  let payload = {};
  try {
    const script = document.getElementById("env-list-vue-payload");
    if (script?.textContent) payload = JSON.parse(script.textContent);
  } catch {
    /* ignore */
  }
  const createUrl = el.dataset.createUrl || "/environments/create/";
  const app = createApp(EnvironmentList, { initial: payload, createUrl });
  app.use(ElementPlus, { locale: zhCn });
  app.mount(el);
}
