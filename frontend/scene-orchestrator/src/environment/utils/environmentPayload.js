/**
 * 与环境 Django EnvironmentForm 的 variables_json / request_headers_json 一致。
 */
export const VAR_DESC_META = "__var_descriptions__";

export function safeJsonParse(str, fallback) {
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
}

export function rowsFromVariables(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) {
    return [{ key: "", value: "", description: "" }];
  }
  const descriptions = obj[VAR_DESC_META] || {};
  const keys = Object.keys(obj).filter((k) => k !== VAR_DESC_META);
  if (!keys.length) {
    return [{ key: "", value: "", description: "" }];
  }
  return keys.map((k) => {
    const val = obj[k];
    let valueStr = "";
    if (val === null || val === undefined) {
      valueStr = "";
    } else if (typeof val === "object") {
      valueStr = JSON.stringify(val);
    } else {
      valueStr = String(val);
    }
    return { key: k, value: valueStr, description: descriptions[k] || "" };
  });
}

export function buildVariablesObject(rows) {
  const obj = {};
  const descriptions = {};
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const k = String(row.key || "").trim();
    if (!k || k === VAR_DESC_META) {
      continue;
    }
    const raw = row.value;
    const s = String(raw === null || raw === undefined ? "" : raw).trim();
    let v;
    if (s.startsWith("{") || s.startsWith("[")) {
      try {
        v = JSON.parse(s);
      } catch {
        v = raw;
      }
    } else {
      v = raw;
    }
    obj[k] = v;
    const d = String(row.description || "").trim();
    if (d) {
      descriptions[k] = d;
    }
  }
  if (Object.keys(descriptions).length) {
    obj[VAR_DESC_META] = descriptions;
  }
  return obj;
}

export function rowsFromHeaders(raw) {
  if (Array.isArray(raw)) {
    if (!raw.length) {
      return [{ key: "", value: "", description: "", required: true, type: "string" }];
    }
    return raw.map((h) => ({
      key: h.key || "",
      value: h.value != null ? String(h.value) : "",
      description: h.description || "",
      required: h.required !== false,
      type: h.type || "string",
    }));
  }
  if (raw && typeof raw === "object") {
    return Object.keys(raw).map((k) => ({
      key: k,
      value: raw[k] != null ? String(raw[k]) : "",
      description: "",
      required: true,
      type: "string",
    }));
  }
  return [{ key: "", value: "", description: "", required: true, type: "string" }];
}

export function buildHeadersArray(rows) {
  const out = [];
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const k = String(row.key || "").trim();
    if (!k) {
      continue;
    }
    out.push({
      key: k,
      value: row.value,
      description: String(row.description || "").trim(),
      required: row.required !== false,
      type: row.type || "string",
    });
  }
  return out;
}
