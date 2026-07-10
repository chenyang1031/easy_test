const DEFAULT_TIMEOUT_MS = 15000;

function csrfToken() {
  const cookie = `; ${document.cookie}`;
  const parts = cookie.split("; csrftoken=");
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return "";
}

function resolveApiUrl(path) {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const base = typeof window !== "undefined" && window.location?.origin ? window.location.origin : "";
  return base ? `${base}${path.startsWith("/") ? path : `/${path}`}` : path;
}

async function request(url, options = {}) {
  const resolvedUrl = resolveApiUrl(url);
  const headers = {
    ...(options.headers || {})
  };
  const hasBody = options.body !== undefined && options.body !== null;
  if (hasBody && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (!headers["X-CSRFToken"]) {
    headers["X-CSRFToken"] = csrfToken();
  }
  const timeoutMs = Number(options.timeoutMs || DEFAULT_TIMEOUT_MS);
  const controller = new AbortController();
  const timeoutHandle = window.setTimeout(() => {
    controller.abort();
  }, timeoutMs);
  const fetchOptions = {
    ...options,
    headers,
    signal: controller.signal
  };
  delete fetchOptions.timeoutMs;
  let response;
  try {
    response = await fetch(resolvedUrl, fetchOptions);
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(`请求超时(${timeoutMs}ms)：${url}`);
    }
    throw new Error(error?.message || "网络请求失败");
  } finally {
    window.clearTimeout(timeoutHandle);
  }
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    // 检测是否为 HTML 响应（服务器错误页、登录页等）
    const trimmed = text.trim();
    if (trimmed.startsWith("<!") || trimmed.startsWith("<html") || trimmed.startsWith("<HTML")) {
      data = { detail: `服务器返回了异常页面 (${response.status})` };
    } else {
      data = { detail: text || "响应解析失败" };
    }
  }
  if (!response.ok) {
    const msg = formatErrorMessage(data, response.status);
    throw new Error(msg);
  }
  return data;
}

/**
 * 将服务器返回的错误数据格式化为可读字符串，便于用户排查问题
 */
function formatErrorMessage(data, statusCode) {
  const detail = data.detail;
  const error = data.error;
  if (typeof detail === "string" && detail) return detail;
  if (typeof error === "string" && error) return error;
  if (detail && typeof detail === "object") {
    if (Array.isArray(detail)) return detail.join("; ");
    const parts = [];
    for (const [key, val] of Object.entries(detail)) {
      const v = Array.isArray(val) ? val.join(", ") : String(val);
      parts.push(`${key}: ${v}`);
    }
    if (parts.length) return parts.join("; ");
  }
  return `请求失败 (${statusCode})`;
}

export const http = {
  get(url, options = {}) {
    return request(url, options);
  },
  post(url, payload, options = {}) {
    const body = payload instanceof FormData ? payload : JSON.stringify(payload || {});
    return request(url, { ...options, method: "POST", body });
  },
  put(url, payload, options = {}) {
    const body = payload instanceof FormData ? payload : JSON.stringify(payload || {});
    return request(url, { ...options, method: "PUT", body });
  },
  patch(url, payload, options = {}) {
    return request(url, { ...options, method: "PATCH", body: JSON.stringify(payload || {}) });
  },
  delete(url, options = {}) {
    return request(url, { ...options, method: "DELETE" });
  }
};
