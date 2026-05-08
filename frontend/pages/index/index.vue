<template>
  <view class="page">
    <!-- 顶部品牌区 -->
    <view class="hero">
      <view class="hero-inner">
        <view class="hero-badge">AI Lesson Planner</view>
        <view class="hero-title">智能备课工作台</view>
        <view class="hero-sub">全学段 · 全学科 · 教案 / 试卷 / H5 课件一键生成</view>
        <view class="hero-user" v-if="greetingName">
          <text class="hi">你好，{{ greetingName }}</text>
        </view>
      </view>
    </view>

    <!-- 快捷入口 -->
    <view class="section-label">快捷开始</view>
    <view class="card-container">
      <view class="big-card" @click="handleAction('plan')">
        <view class="icon-emoji">📚</view>
        <view class="card-title">智能教案</view>
        <view class="card-desc">Word 标准教案</view>
      </view>
      <view class="big-card" @click="handleAction('quiz')">
        <view class="icon-emoji">✏️</view>
        <view class="card-title">达标测试</view>
        <view class="card-desc">100 分制试卷</view>
      </view>
      <view class="big-card" @click="handleAction('html')">
        <view class="icon-emoji">🌐</view>
        <view class="card-title">互动课件</view>
        <view class="card-desc">H5 课堂演示</view>
      </view>
    </view>

    <!-- VIP -->
    <view class="banner">
      <view class="banner-content">
        <view class="banner-icon">📢</view>
        <view class="banner-text">
          <view class="b-title">开通 VIP</view>
          <view class="b-desc">无限次生成，优先生成通道</view>
        </view>
        <button class="vip-btn" @click="goVip">去开通</button>
      </view>
    </view>

    <view class="section-label">最近生成</view>
    <view class="recent-list">
      <view class="recent-item" v-for="(item, index) in historyList" :key="index">
        <view class="recent-tag">{{ item.subject }}</view>
        <view class="recent-info">
          <view class="recent-main">{{ item.topic }}</view>
          <view class="recent-time">{{ item.time }}</view>
          <view class="action-btns">
            <text class="btn-text" @click="downloadFile(item.planUrl)">教案</text>
            <text class="btn-text" @click="downloadFile(item.quizUrl)">试卷</text>
            <text class="btn-text" @click="openH5(item.htmlUrl)">课件</text>
          </view>
        </view>
      </view>
      <view v-if="historyList.length === 0" class="empty-hint">暂无生成记录，去「备课」试试吧</view>
    </view>

    <view class="footer-tabbar">
      <view class="tab-item active">首页</view>
      <view class="tab-item" @click="navTo('prepare')">备课</view>
      <view class="tab-item" @click="navTo('vip')">会员卡</view>
      <view class="tab-item" @click="navTo('mine')">我的</view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { API_BASE } from '../../src/apiBase.js'
import { apiRequest } from '../../src/http.js'
import { getStoredNickname } from '../../src/auth.js'

const historyList = ref([])
const greetingName = ref(getStoredNickname() || '')

const loadHistory = async () => {
  try {
    const res = await apiRequest({ url: '/api/history', method: 'GET' })
    if (res.statusCode === 200 && res.data?.code === 200) {
      const baseUrl = `${API_BASE}/static/`
      historyList.value = res.data.data.map((item) => {
        const files = item.files || {}
        return {
          topic: item.topic,
          subject: item.subject,
          time: (item.created_at || '').replace('T', ' '),
          planUrl: files.plan ? baseUrl + files.plan : '',
          quizUrl: files.quiz ? baseUrl + files.quiz : '',
          htmlUrl: files.html ? baseUrl + files.html : '',
        }
      })
    }
  } catch (_) {
    /* 401 由 http.js 处理 */
  }
}

const loadProfile = async () => {
  try {
    const res = await apiRequest({ url: '/api/user/info', method: 'GET' })
    if (res.statusCode === 200 && res.data?.code === 200) {
      const n = res.data.data?.nickname
      if (n) greetingName.value = n
    }
  } catch (_) {}
}

onMounted(() => {
  loadProfile()
  loadHistory()
  uni.setNavigationBarTitle({ title: 'AI 备课' })
})

const openH5 = (url) => {
  if (!url) return uni.showToast({ title: '链接不存在', icon: 'none' })
  window.open(url)
}

const downloadFile = (url) => {
  if (!url) return uni.showToast({ title: '链接不存在', icon: 'none' })
  window.open(url)
}

const handleAction = (type) => {
  uni.setStorageSync('genType', type)
  uni.reLaunch({ url: '/pages/prepare/prepare' })
}

const navTo = (name) => {
  uni.reLaunch({ url: `/pages/${name}/${name}` })
}

const goVip = () => {
  uni.reLaunch({ url: '/pages/vip/vip' })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px) + 20px);
  box-sizing: border-box;
}

.hero {
  background: linear-gradient(135deg, #5c6ac4 0%, #4a56a8 100%);
  padding: 32px 20px 40px;
  border-radius: 20px;
  margin: max(12px, env(safe-area-inset-top, 0px)) auto 0;
  max-width: 560px;
  width: 100%;
  box-shadow: 0 8px 28px rgba(76, 86, 160, 0.28);
  color: #fff;
  box-sizing: border-box;
}
.hero-inner {
  max-width: 520px;
  margin: 0 auto;
}
.hero-badge {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.85;
  margin-bottom: 10px;
}
.hero-title {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.25;
  margin-bottom: 8px;
}
.hero-sub {
  font-size: 13px;
  opacity: 0.92;
  line-height: 1.5;
}
.hero-user {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.25);
}
.hi {
  font-size: 15px;
  font-weight: 600;
}

.section-label {
  font-size: 15px;
  font-weight: 700;
  color: #333;
  margin: 26px 20px 14px;
  letter-spacing: 0.02em;
}

.card-container {
  display: flex;
  flex-wrap: nowrap;
  justify-content: space-between;
  align-items: stretch;
  gap: 10px;
  padding: 0 16px;
  margin-bottom: 24px;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
}

.big-card {
  flex: 1 1 0;
  min-width: 0;
  background: #fff;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.07);
  border: 1px solid rgba(0, 0, 0, 0.04);
  aspect-ratio: 1 / 1;
  padding: 12px 4px;
  justify-content: center;
  box-sizing: border-box;
}

.icon-emoji {
  font-size: 26px;
  line-height: 1;
  margin-bottom: 6px;
}
.card-title {
  font-size: 13px;
  font-weight: 800;
  color: #333;
  margin-bottom: 2px;
  line-height: 1.3;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-desc {
  font-size: 10px;
  color: #888;
  line-height: 1.25;
  word-break: break-all;
}

.banner {
  background: #5c6ac4;
  border-radius: 14px;
  padding: 16px 18px;
  margin: 0 16px 22px;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
  box-shadow: 0 6px 18px rgba(92, 106, 196, 0.2);
  color: #fff;
  box-sizing: border-box;
}
.banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.banner-icon {
  font-size: 22px;
  margin-right: 10px;
}
.banner-text {
  flex: 1;
  text-align: left;
  min-width: 0;
}
.b-title {
  font-size: 16px;
  font-weight: bold;
}
.b-desc {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 2px;
}
.vip-btn {
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.45);
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  padding: 0 14px;
  height: 34px;
  line-height: 32px;
}

.recent-list {
  padding: 0 16px 28px;
  max-width: 560px;
  margin: 0 auto;
}
.recent-item {
  background: #fff;
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
}
.recent-tag {
  background: #f0f2f5;
  color: #333;
  padding: 8px 12px;
  border-radius: 8px;
  font-weight: bold;
  font-size: 14px;
  margin-right: 14px;
}
.recent-info {
  flex: 1;
}
.recent-main {
  font-size: 15px;
  color: #333;
  margin-bottom: 4px;
}
.recent-time {
  font-size: 12px;
  color: #999;
}
.action-btns {
  margin-top: 8px;
}
.btn-text {
  color: #5c6ac4;
  font-size: 13px;
  margin-right: 14px;
  font-weight: 600;
  cursor: pointer;
}

.empty-hint {
  text-align: center;
  color: #aaa;
  padding: 36px 20px;
  font-size: 14px;
  line-height: 1.6;
}

.footer-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  min-height: 52px;
  padding: 8px 0 calc(8px + env(safe-area-inset-bottom, 0px));
  box-sizing: border-box;
  background-color: #5c6ac4;
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 999;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.08);
}
.tab-item {
  color: #fff;
  font-size: 15px;
  flex: 1;
  text-align: center;
  opacity: 0.72;
  padding: 6px 4px;
}
.tab-item.active {
  opacity: 1;
  font-weight: 700;
}
</style>
