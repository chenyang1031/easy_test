// 多标签栏(TagsView)的持久化键。
// 标签列表只允许在同一登录会话内保留：登录成功 / 登出时必须清空，
// 否则换账号或重新登录后会看到上一会话打开的页面。
export const VISITED_TABS_KEY = 'appShellVisitedTabs'

export function clearVisitedTabs() {
  localStorage.removeItem(VISITED_TABS_KEY)
}
