import { createRouter, createWebHashHistory } from "vue-router";
import SceneListPage from "../pages/SceneListPage.vue";
import SceneDesignerPage from "../pages/SceneDesignerPage.vue";
import SceneExecutionPage from "../pages/SceneExecutionPage.vue";
import PerformanceTaskList from "../views/performance/PerformanceTaskList.vue";
import PerformanceTaskEditor from "../views/performance/PerformanceTaskEditor.vue";
import PerformanceConsole from "../views/performance/PerformanceConsole.vue";
import PerformanceReport from "../views/performance/PerformanceReport.vue";
import ReportListPage from "../views/reports/ReportListPage.vue";
import ReportDetailPage from "../views/reports/ReportDetailPage.vue";
import ReportFormPage from "../views/reports/ReportFormPage.vue";

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/scenes" },
    { path: "/scenes", name: "scene-list", component: SceneListPage, meta: { title: "测试场景编排" } },
    { path: "/performance", name: "perf-list", component: PerformanceTaskList, meta: { title: "性能测试" } },
    {
      path: "/performance/tasks/new",
      name: "perf-task-new",
      component: PerformanceTaskEditor,
      meta: { title: "新建性能任务" }
    },
    {
      path: "/performance/tasks/:id/edit",
      name: "perf-task-edit",
      component: PerformanceTaskEditor,
      meta: { title: "编辑性能任务" }
    },
    {
      path: "/performance/tasks/:id/console",
      name: "perf-console",
      component: PerformanceConsole,
      meta: { title: "压测控制台" }
    },
    {
      path: "/performance/tasks/:id/report",
      name: "perf-report",
      component: PerformanceReport,
      meta: { title: "性能测试报告" }
    },
    {
      path: "/scenes/:id/designer",
      name: "scene-designer",
      component: SceneDesignerPage,
      props: true,
      meta: { title: "编辑场景详情" }
    },
    {
      path: "/scenes/:id/executions/:executionId?",
      name: "scene-execution",
      component: SceneExecutionPage,
      props: true,
      meta: { title: "执行日志" }
    },
    // ===== 测试报告 =====
    {
      path: "/reports",
      name: "reportList",
      component: ReportListPage,
      meta: { title: "测试报告" }
    },
    {
      path: "/reports/create",
      name: "reportCreate",
      component: ReportFormPage,
      meta: { title: "新建测试报告" }
    },
    {
      path: "/reports/:id",
      name: "reportDetail",
      component: ReportDetailPage,
      props: true,
      meta: { title: "测试报告详情" }
    },
    {
      path: "/reports/:id/edit",
      name: "reportEdit",
      component: ReportFormPage,
      props: true,
      meta: { title: "编辑测试报告" }
    },
    {
      path: "/scene-executions/:executionId/generate-report",
      name: "sceneExecutionReportForm",
      component: () => import("../views/reports/SceneExecutionReportForm.vue"),
      props: true,
      meta: { title: "生成测试报告" }
    },
    {
      path: "/test-runs/:testRunId/generate-report",
      name: "testRunReportForm",
      component: () => import("../views/reports/TestRunReportForm.vue"),
      props: true,
      meta: { title: "生成测试报告" }
    },
    // ===== 日志查询 =====
    {
      path: "/log-query",
      name: "log-query",
      component: () => import("../views/log-query/LogQuery.vue"),
      meta: { title: "日志查询" }
    }
  ]
});

router.afterEach((to) => {
  const title = to.meta?.title ? `${to.meta.title} - EasyTesting` : "测试场景编排 - EasyTesting";
  document.title = title;
  const headerEl = document.querySelector(".page-title");
  if (headerEl) {
    headerEl.textContent = to.meta?.title || "测试场景编排";
  }
});

export default router;
