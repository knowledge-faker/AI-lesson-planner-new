/**
 * 后端 API 根地址（不含末尾 /）
 * - 生产构建：默认与当前页面同源（https://域名 + Nginx 反代 /api）
 * - 本地 vite dev：默认连本机 8000 端口
 * - 可覆盖：前端目录建 .env.production / .env.development，写 VITE_API_BASE=https://xxx
 */
export function getApiBase() {
  const explicit = import.meta.env.VITE_API_BASE
  if (explicit !== undefined && String(explicit).trim() !== '') {
    return String(explicit).trim().replace(/\/$/, '')
  }
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000'
  }
  if (import.meta.env.DEV) {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }
  return window.location.origin
}

export const API_BASE = getApiBase()
