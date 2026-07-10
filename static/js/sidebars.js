/* global bootstrap: false */
(() => {
  'use strict'

  const SCROLL_KEY = 'easytesting_sidebar_sticky_scroll'
  const sticky = document.querySelector('.sidebar-sticky')

  function persistSidebarScroll() {
    if (!sticky) return
    sessionStorage.setItem(SCROLL_KEY, String(sticky.scrollTop))
  }

  function restoreSidebarScroll() {
    if (!sticky) return
    const raw = sessionStorage.getItem(SCROLL_KEY)
    if (raw === null) return
    const y = parseInt(raw, 10)
    if (Number.isNaN(y) || y < 0) return
    const apply = () => {
      sticky.scrollTop = y
    }
    apply()
    requestAnimationFrame(apply)
    window.addEventListener('load', apply, { once: true })
  }

  if (sticky) {
    restoreSidebarScroll()

    let scrollTimer
    sticky.addEventListener(
      'scroll',
      () => {
        clearTimeout(scrollTimer)
        scrollTimer = setTimeout(persistSidebarScroll, 80)
      },
      { passive: true }
    )

    sticky.addEventListener('click', (e) => {
      const a = e.target.closest('a')
      if (!a || !sticky.contains(a)) return
      const href = a.getAttribute('href')
      if (href && href !== '#' && !href.startsWith('javascript:')) {
        persistSidebarScroll()
      }
    })

    window.addEventListener('pagehide', persistSidebarScroll)
  }

  const tooltipTriggerList = Array.from(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  tooltipTriggerList.forEach(tooltipTriggerEl => {
    new bootstrap.Tooltip(tooltipTriggerEl)
  })
})()
