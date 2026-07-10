/**
 * 通用时间格式化：将 ISO 8601 时间戳转为 "YYYY-MM-DD HH:mm" 格式
 * 输入: "2026-05-21T15:50:33.123456+08:00"
 * 输出: "2026-05-21 15:50"
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  if (typeof dateStr !== 'string') return String(dateStr)
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
