<template>
  <view class="page">
    <view class="brand">
      <img class="logo" src="/logo.png" alt="AI备课" width="72" height="72" />
      <view class="app-name">AI 备课助手</view>
      <view class="tagline">登录后使用智能教案 · 试卷 · 课件生成</view>
    </view>

    <view class="card">
      <view class="field">
        <text class="label">账号</text>
        <input v-model="username" class="input" placeholder="3～50 位字母/数字/下划线/中文" />
      </view>
      <view class="field">
        <text class="label">密码</text>
        <input v-model="password" class="input" type="password" placeholder="至少 6 位" />
      </view>
      <button class="btn-primary" @click="doLogin">登 录</button>
      <view class="row-foot">
        <text class="link" @click="goRegister">没有账号？去注册</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { API_BASE } from '../../src/apiBase.js'
import { setAuth } from '../../src/auth.js'

const username = ref('')
const password = ref('')

const doLogin = () => {
  const u = username.value.trim()
  const p = password.value
  if (!u || !p) {
    return uni.showToast({ title: '请输入账号和密码', icon: 'none' })
  }
  uni.showLoading({ title: '登录中...' })
  uni.request({
    url: `${API_BASE}/api/auth/login`,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: { username: u, password: p },
    success: (res) => {
      uni.hideLoading()
      if (res.statusCode === 200 && res.data?.code === 200) {
        const d = res.data.data
        setAuth(d.access_token, d.nickname)
        uni.showToast({ title: '欢迎回来', icon: 'success' })
        setTimeout(() => {
          uni.reLaunch({ url: '/pages/index/index' })
        }, 400)
      } else {
        const msg = res.data?.detail || res.data?.message || '登录失败'
        uni.showToast({ title: typeof msg === 'string' ? msg : '账号或密码错误', icon: 'none' })
      }
    },
    fail: () => {
      uni.hideLoading()
      uni.showToast({ title: '网络错误', icon: 'none' })
    },
  })
}

const goRegister = () => {
  uni.reLaunch({ url: '/pages/register/register' })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(165deg, #5c6ac4 0%, #7b88d6 42%, #f5f7fa 42%);
  padding: 48px 24px 32px;
  box-sizing: border-box;
}
.brand {
  text-align: center;
  color: #fff;
  margin-bottom: 36px;
}
.logo {
  display: block;
  width: 72px;
  height: 72px;
  margin: 0 auto 12px;
  border-radius: 16px;
  object-fit: cover;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
.app-name {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 1px;
}
.tagline {
  font-size: 13px;
  opacity: 0.92;
  margin-top: 8px;
}
.card {
  background: #fff;
  border-radius: 20px;
  padding: 28px 22px;
  box-shadow: 0 16px 40px rgba(92, 106, 196, 0.18);
}
.field {
  margin-bottom: 18px;
}
.label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 600;
}
.input {
  width: 100%;
  height: 46px;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 16px;
  box-sizing: border-box;
  background: #fafbfc;
}
.btn-primary {
  width: 100%;
  height: 48px;
  line-height: 48px;
  background: #5c6ac4;
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 17px;
  font-weight: 700;
  margin-top: 8px;
}
.row-foot {
  text-align: center;
  margin-top: 20px;
}
.link {
  color: #5c6ac4;
  font-size: 14px;
  text-decoration: underline;
  cursor: pointer;
}
</style>
