const TOKEN_KEY = 'alp_access_token'
const NICK_KEY = 'alp_nickname'

export function getToken() {
  if (typeof localStorage === 'undefined') return ''
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setAuth(token, nickname) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
  if (nickname != null) localStorage.setItem(NICK_KEY, nickname)
}

export function clearAuth() {
  if (typeof localStorage === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(NICK_KEY)
}

export function authHeaders() {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export function getStoredNickname() {
  if (typeof localStorage === 'undefined') return ''
  return localStorage.getItem(NICK_KEY) || ''
}

/** 仅路径段，不含 ?query（用于路由表匹配） */
export function hashPathOnly(fullHashWithoutLeadingHash) {
  const raw = fullHashWithoutLeadingHash || ''
  const path = raw.split('?')[0]
  return path || '/pages/index/index'
}

/**
 * 登录、注册；以及支付宝同步回跳（手机 WebView 无本站 localStorage）
 * 注意：支付宝可能把参数写在 window.location.search（# 前面），hash 里只有路径无 query，
 * 必须把 search + hash 片段合并判断，否则会误判未登录并跳到登录页。
 */
export function isPublicPath(fullHashWithoutLeadingHash) {
  const path = hashPathOnly(fullHashWithoutLeadingHash)
  if (path.includes('/pages/login/') || path.includes('/pages/register/')) {
    return true
  }
  if (path === '/pages/vip/vip') {
    const search = typeof window !== 'undefined' ? window.location.search || '' : ''
    const combined = `${fullHashWithoutLeadingHash || ''}${search}`
    if (/[?&]out_trade_no=/.test(combined)) return true
    if (/[?&]trade_no=/.test(combined)) return true
    if (/[?&]order_no=/.test(combined) && /PROD_/.test(combined)) return true
    return false
  }
  return false
}
