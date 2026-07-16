import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: "/static/scene-orchestrator/",
  plugins: [vue()],
  server: {
    port: 5178,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "../../static/scene-orchestrator",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      input: {
        // ===== 统一 SPA Shell 入口 =====
        'app-shell': path.resolve(__dirname, "src/app-shell/main.js"),

        // ===== 过渡期保留的旧入口（逐步移除） =====
        main: path.resolve(__dirname, "index.html"),
        environmentList: path.resolve(__dirname, "src/environment/entries/environmentList.js"),
        environmentForm: path.resolve(__dirname, "src/environment/entries/environmentForm.js"),
        environmentDetail: path.resolve(__dirname, "src/environment/entries/environmentDetail.js"),
        apiAssetApifoxEnv: path.resolve(__dirname, "src/api-asset-import/entries/apiAssetApifoxEnv.js"),
        apiAssetManager: path.resolve(__dirname, "src/api-asset-manager/index.html"),
        promptTemplateManager: path.resolve(__dirname, "src/prompt-template-manager/index.html"),
        ruleManager: path.resolve(__dirname, "src/rule-manager/index.html"),
        modelProviderManager: path.resolve(__dirname, "src/model-provider-manager/index.html"),
        draftBox: path.resolve(__dirname, "src/draft-box/index.html"),
        testManager: path.resolve(__dirname, "src/test-manager/index.html"),
        aiGenRecord: path.resolve(__dirname, "src/ai-gen-record/index.html"),
        mockData: path.resolve(__dirname, "src/mock-data/index.html"),
        documentImport: path.resolve(__dirname, "src/document-import/index.html"),
        dashboard: path.resolve(__dirname, "src/dashboard/index.html"),
        sidebar: path.resolve(__dirname, "src/sidebar/main.js")
      },
      output: {
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === "main") return "assets/main.js";
          return `assets/${chunkInfo.name}.js`;
        },
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name][extname]",
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("echarts")) return "echarts";
            if (id.includes("element-plus") || id.includes("@element-plus")) return "element-plus";
            if (id.includes("codemirror")) return "codemirror";
            if (id.includes("vue") || id.includes("pinia") || id.includes("vue-router")) return "vue-vendor";
            return "vendor";
          }
        }
      }
    }
  }
});
