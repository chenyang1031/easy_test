import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";
import EnvironmentForm from "../components/EnvironmentForm.vue";

const el = document.getElementById("environment-form-mount");
if (el) {
  let initial = {};
  try {
    const s = document.getElementById("env-form-initial-payload");
    if (s?.textContent) initial = JSON.parse(s.textContent);
  } catch {
    /* ignore */
  }
  const cancelUrl = el.dataset.cancelUrl || "/environments/";
  const app = createApp(EnvironmentForm, { initialJson: initial, cancelUrl });
  app.use(ElementPlus, { locale: zhCn });
  app.mount(el);
}
