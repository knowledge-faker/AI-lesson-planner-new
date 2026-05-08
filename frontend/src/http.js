import { API_BASE } from './apiBase.js'
import { authHeaders, clearAuth, isPublicPath } from './auth.js'

/**
 * 带 Authorization 的请求；401 时清空登录并跳转登录页（公开页除外）
 */
export function apiRequest(options) {
  const path = options.url || ''
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`

  return new Promise((resolve, reject) => {
    uni.request({
      ...options,
      url,
      header: {
        'Content-Type': 'application/json',
        ...authHeaders(),
        ...(options.header || {}),
      },
      success: (res) => {
        if (res.statusCode === 401 && typeof window !== 'undefined') {
          clearAuth()
          const raw = (window.location.hash || '').replace(/^#/, '')
          if (!isPublicPath(raw)) {
            window.location.hash = '#/pages/login/login'
          }
        }
        resolve(res)
      },
      fail: (err) => reject(err),
    })
  })
}
