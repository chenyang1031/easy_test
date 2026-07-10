/**
 * CSRF Token 处理 composable
 * 从页面隐藏input或cookie中读取 Django CSRF token
 * 统一版本，各子应用从此文件引用
 */
export function useCsrf() {
  function getToken() {
    // 1. 尝试从页面隐藏input读取
    const el = document.querySelector('input[name="csrfmiddlewaretoken"]')
    if (el) return el.value

    // 2. 从cookie读取
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';')
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim()
        if (cookie.substring(0, 10) === 'csrftoken=') {
          return decodeURIComponent(cookie.substring(10))
        }
      }
    }
    return ''
  }

  return { getToken }
}
