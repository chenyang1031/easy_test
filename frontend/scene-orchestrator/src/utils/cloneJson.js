const CLONE_MAX_SIZE = 10 * 1024 * 1024; // 10MB

export function cloneJson(value, fallback) {
  if (value === null || value === undefined) {
    return fallback;
  }
  try {
    const str = JSON.stringify(value);
    if (str && str.length > CLONE_MAX_SIZE) {
      console.warn("cloneJson: 数据过大已截断", str.length);
      return fallback;
    }
    return JSON.parse(str);
  } catch (err) {
    console.error("cloneJson error:", err);
    return fallback;
  }
}
