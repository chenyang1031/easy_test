/**
 * 性能测试前端共享工具（与后端 extra_config / 结果结构对齐）
 */

let _uid = 0;
export function nextLocalId() {
  _uid += 1;
  return `row-${Date.now()}-${_uid}`;
}

/** 简易 CSV 预览解析（表头 + 前 N 行，不支持复杂引号内逗号） */
export function parseCsvPreview(text, maxRows = 5) {
  if (!text || !String(text).trim()) {
    return { headers: [], rows: [] };
  }
  const lines = String(text)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return { headers: [], rows: [] };
  const splitLine = (line) => line.split(",").map((c) => c.replace(/^"|"$/g, "").trim());
  const headers = splitLine(lines[0]);
  const rows = [];
  for (let i = 1; i < lines.length && rows.length < maxRows; i++) {
    rows.push(splitLine(lines[i]));
  }
  return { headers, rows };
}

export function taskLoadType(row) {
  const st = row?.extra_config?.stages;
  return Array.isArray(st) && st.length > 0 ? "staged" : "fixed";
}

export function taskHasAssertions(row) {
  const a = row?.extra_config?.assertions;
  return Array.isArray(a) && a.length > 0;
}

export function taskHasCsv(row) {
  return !!(row?.csv_file || row?.csv_file_url);
}

/** 阶梯负载：根据 executed_at 与当前时间推算阶段（仅 running 时有意义） */
export function computeStageProgress(task, nowMs = Date.now()) {
  const stages = task?.extra_config?.stages;
  if (!Array.isArray(stages) || !stages.length) {
    return null;
  }
  const started = task?.executed_at ? new Date(task.executed_at).getTime() : null;
  if (!started) {
    return { index: 0, total: stages.length, stage: stages[0], elapsedInStage: 0, remainingInStage: stages[0].duration_sec };
  }
  const elapsedSec = Math.max(0, (nowMs - started) / 1000);
  let acc = 0;
  for (let i = 0; i < stages.length; i++) {
    const dur = Number(stages[i].duration_sec) || 0;
    if (elapsedSec < acc + dur) {
      return {
        index: i,
        total: stages.length,
        stage: stages[i],
        elapsedInStage: elapsedSec - acc,
        remainingInStage: Math.max(0, acc + dur - elapsedSec)
      };
    }
    acc += dur;
  }
  return { index: stages.length - 1, total: stages.length, stage: stages[stages.length - 1], done: true, remainingInStage: 0 };
}

/** 从采样序列估算总请求数（每秒 RPS 近似积分） */
export function estimateTotalRequests(results) {
  if (!Array.isArray(results) || !results.length) return 0;
  return results.reduce((s, r) => s + (Number(r.requests_per_second) || 0), 0);
}

/** 错误分类键 → 中文 */
export const ERROR_LABELS = {
  http_status_error: "HTTP错误",
  timeout: "超时",
  connection_error: "连接失败",
  assertion_failure: "业务断言失败"
};
