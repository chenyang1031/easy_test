import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import EnvironmentDetail from "../components/EnvironmentDetail.vue";

const el = document.getElementById("environment-detail-mount");
if (el) {
  let initial = {};
  try {
    const s = document.getElementById("env-detail-vue-payload");
    if (s?.textContent) initial = JSON.parse(s.textContent);
  } catch {
    /* ignore */
  }
  const app = createApp(EnvironmentDetail, { initial });
  app.use(ElementPlus, { locale: zhCn });
  app.mount(el);
}
