import { createApp } from 'vue'
import App from './App.vue'

const toQueryString = (obj = {}) => {
  const params = new URLSearchParams()
  Object.keys(obj).forEach((k) => {
    const v = obj[k]
    if (v !== undefined && v !== null) params.append(k, String(v))
  })
  return params.toString()
}

if (!window.uni) {
  window.uni = {
    request({ url, method = 'GET', data, header, success, fail, timeout }) {
      const controller = new AbortController()
      const upperMethod = String(method).toUpperCase()
      let finalUrl = url
      const init = {
        method: upperMethod,
        headers: {
          'Content-Type': 'application/json',
          ...(header || {}),
        },
        signal: controller.signal
      }
      if (upperMethod === 'GET' && data && typeof data === 'object') {
        const qs = toQueryString(data)
        if (qs) finalUrl += (finalUrl.includes('?') ? '&' : '?') + qs
      } else if (data !== undefined) {
        init.body = JSON.stringify(data)
      }
      const timer = timeout ? setTimeout(() => controller.abort(), timeout) : null
      fetch(finalUrl, init)
        .then(async (resp) => {
          const text = await resp.text()
          let json = {}
          try { json = text ? JSON.parse(text) : {} } catch { json = {} }
          success && success({ data: json, statusCode: resp.status })
        })
        .catch((err) => fail && fail({ errMsg: err?.message || 'request failed' }))
        .finally(() => timer && clearTimeout(timer))
    },
    showLoading({ title }) { console.log(title || 'loading') },
    hideLoading() {},
    showToast({ title }) { alert(title || '') },
    showModal({ title, content, success }) {
      const confirm = window.confirm(`${title || '提示'}\n\n${content || ''}`)
      success && success({ confirm, cancel: !confirm })
    },
    showActionSheet({ itemList = [], success, fail }) {
      const input = window.prompt(`${itemList.map((x, i) => `${i + 1}. ${x}`).join('\n')}\n请输入序号：`, '1')
      const idx = Number(input) - 1
      if (Number.isInteger(idx) && idx >= 0 && idx < itemList.length) {
        success && success({ tapIndex: idx })
      } else {
        fail && fail({ errMsg: 'cancel' })
      }
    },
    setClipboardData({ data, success }) {
      navigator.clipboard?.writeText(String(data || '')).finally(() => success && success())
    },
    setNavigationBarTitle() {},
    reLaunch({ url }) {
      window.location.hash = `#${url}`
      window.dispatchEvent(new HashChangeEvent('hashchange'))
    },
    setStorageSync(key, value) {
      localStorage.setItem(key, JSON.stringify(value))
    },
    getStorageSync(key) {
      const raw = localStorage.getItem(key)
      if (!raw) return ''
      try { return JSON.parse(raw) } catch { return raw }
    }
  }
}

createApp(App).mount('#app')
