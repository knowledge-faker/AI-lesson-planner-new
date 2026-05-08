<template>
  <view class="page">
    <view class="brand">
      <img class="logo" src="/logo.png" alt="AI备课" width="72" height="72" />
      <view class="app-name">注册账号</view>
      <view class="tagline">创建账号后即可生成全套备课资源</view>
    </view>

    <view class="card">
      <view class="field">
        <text class="label">登录账号</text>
        <input v-model="username" class="input" placeholder="3～50 位" />
      </view>
      <view class="field">
        <text class="label">密码</text>
        <input v-model="password" class="input" type="password" placeholder="至少 6 位" />
      </view>
      <view class="field">
        <text class="label">昵称（可选）</text>
        <input v-model="nickname" class="input" placeholder="默认与账号相同" />
      </view>
      <button class="btn-primary" @click="doRegister">注 册</button>
      <view class="row-foot">
        <text class="link" @click="goLogin">已有账号？去登录</text>
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
const nickname = ref('')

const apiDetailText = (data) => {
  const d = data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length) {
    return d.map((e) => (typeof e?.msg === 'string' ? e.msg : '')).filter(Boolean).join('；') || ''
  }
  return ''
}

const doRegister = () => {
  const u = username.value.trim()
  const p = password.value
  if (u.length < 3) {
    return uni.showToast({ title: '账号至少 3 位', icon: 'none' })
  }
  if (p.length < 6) {
    return uni.showToast({ title: '密码至少 6 位', icon: 'none' })
  }
  uni.showLoading({ title: '注册中...' })
  uni.request({
    url: `${API_BASE}/api/auth/register`,
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: {
      username: u,
      password: p,
      nickname: nickname.value.trim() || undefined,
    },
    success: (res) => {
      uni.hideLoading()
      if (res.statusCode === 200 && res.data?.code === 200) {
        const d = res.data.data
        setAuth(d.access_token, d.nickname)
        uni.showToast({ title: '注册成功', icon: 'success' })
        setTimeout(() => {
          uni.reLaunch({ url: '/pages/index/index' })
        }, 400)
      } else {
        const hint = apiDetailText(res.data)
        let title = hint
        if (!title) {
          if (res.statusCode === 400) title = '注册失败，账号可能已存在'
          else if (res.statusCode >= 500) title = '服务异常，请稍后重试'
          else title = '注册失败'
        }
        uni.showToast({ title, icon: 'none' })
      }
    },
    fail: () => {
      uni.hideLoading()
      uni.showToast({ title: '网络错误', icon: 'none' })
    },
  })
}

const goLogin = () => {
  uni.reLaunch({ url: '/pages/login/login' })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(165deg, #5c6ac4 0%, #7b88d6 38%, #f5f7fa 38%);
  padding: 40px 24px 32px;
  box-sizing: border-box;
}
.brand {
  text-align: center;
  color: #fff;
  margin-bottom: 28px;
}
.logo {
  display: block;
  width: 72px;
  height: 72px;
  margin: 0 auto 10px;
  border-radius: 16px;
  object-fit: cover;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
.app-name {
  font-size: 22px;
  font-weight: 800;
}
.tagline {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 8px;
}
.card {
  background: #fff;
  border-radius: 20px;
  padding: 26px 22px;
  box-shadow: 0 16px 40px rgba(92, 106, 196, 0.15);
}
.field {
  margin-bottom: 16px;
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
  margin-top: 6px;
}
.row-foot {
  text-align: center;
  margin-top: 18px;
}
.link {
  color: #5c6ac4;
  font-size: 14px;
  text-decoration: underline;
  cursor: pointer;
}
</style>
