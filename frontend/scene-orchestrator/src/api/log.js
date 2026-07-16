/**
 * 日志查询 API
 */
import { http } from "./http";

export const logApi = {
  /** 获取可用日志文件列表 */
  listFiles: () => http.get("/api/v1/logs/"),

  /** 读取日志文件（最后 N 行） */
  read: (file = "django.log", lines = 500) =>
    http.get(`/api/v1/logs/read/?file=${encodeURIComponent(file)}&lines=${lines}`),

  /** 执行 Shell 命令 */
  execute: (command) => http.post("/api/v1/logs/execute/", { command }),

  /** 获取 SSE 日志流 URL */
  streamUrl: (file = "django.log") =>
    `/api/v1/logs/stream/?file=${encodeURIComponent(file)}`,
};
