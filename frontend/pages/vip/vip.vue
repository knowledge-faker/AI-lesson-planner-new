<template>
  <div class="page">
    <!-- 支付宝同步回跳：手机 WebView 无 localStorage，登录态为空 -->
    <div v-if="payReturnBanner" class="pay-return-banner">
      <template v-if="payReturnState === 'polling'">正在确认支付结果…</template>
      <template v-else-if="payReturnState === 'success'">
        支付已成功，权益可能稍有延迟；请登录后在「我的」查看 VIP。
      </template>
      <template v-else-if="payReturnState === 'pending'">
        若已付款，服务器回调稍有延迟；请稍后登录「我的」刷新。
      </template>
      <text class="banner-login" @click="goLogin">去登录</text>
    </div>

    <div class="header">
      <div class="title">VIP套餐</div>
      <div class="subtitle">购买VIP，享受无限生成备课内容的特权</div>
    </div>

    <!-- 支付联调：0.01 元，订单生效后为 +1 天 VIP -->
    <div class="vip-card test-pack">
      <div class="card-title">支付联调（测试）</div>
      <div class="card-price test-price">¥0.01 <span class="days">/ 验证收款流程</span></div>
      <div class="features">
        <div class="f-item">✓ 支付宝最小金额，用于沙箱或正式联调</div>
        <div class="f-item">✓ 支付成功后延长 1 天 VIP</div>
      </div>
      <p class="test-pack-hint">线上默认关闭；服务器需在 <code>.env.prod</code> 设置 <code>VIP_TEST_PENNY_ENABLED=1</code> 后本入口才可用。</p>
      <button type="button" class="buy-btn test-buy-btn" @click="openPayMenu(1, true)">测试支付 ¥0.01</button>
    </div>

    <!-- 7天VIP -->
    <div class="vip-card">
      <div class="card-title">7天VIP</div>
      <div class="card-price">¥9.9 <span class="days">/ 7天</span></div>
      <div class="features">
        <div class="f-item">✓ 无限生成备课内容</div>
        <div class="f-item">✓ 优先生成通道</div>
      </div>
      <button class="buy-btn" @click="openPayMenu(7)">立即购买</button>
    </div>

    <!-- 月度VIP (推荐) -->
    <div class="vip-card recommend">
      <div class="badge">推荐</div>
      <div class="card-title">月度VIP</div>
      <div class="card-price highlight">¥19.9 <span class="days">/ 30天</span></div>
      <div class="features">
        <div class="f-item">✓ 无限生成备课内容</div>
        <div class="f-item">✓ 优先生成通道</div>
      </div>
      <button class="buy-btn highlight-btn" @click="openPayMenu(30)">立即购买</button>
    </div>

    <!-- 年度VIP -->
    <div class="vip-card">
      <div class="card-title">年度VIP</div>
      <div class="card-price">¥199 <span class="days">/ 365天</span></div>
      <div class="features">
        <div class="f-item">✓ 专属客服支持</div>
      </div>
      <button class="buy-btn" @click="openPayMenu(365)">立即购买</button>
    </div>

    <div v-if="showPaySheet" class="pay-sheet-mask" @click="closePaySheet">
      <div class="pay-sheet" @click.stop>
        <div class="sheet-title">请选择支付方式</div>
        <div class="pay-method-list">
          <div
            v-for="item in paymentOptions"
            :key="item.value"
            class="pay-method-item"
            @click="selectedPayMode = item.value"
          >
            <div class="method-left">
              <div class="method-icon" :class="item.iconClass">{{ item.icon }}</div>
              <div class="method-info">
                <div class="method-name">{{ item.label }}</div>
                <div class="method-desc">{{ item.desc }}</div>
              </div>
            </div>
            <div class="radio-dot" :class="{ checked: selectedPayMode === item.value }"></div>
          </div>
        </div>
        <button class="confirm-pay-btn" @click="confirmPay">确认支付</button>
      </div>
    </div>

    <!-- 支付宝当面付：展示扫码二维码 -->
    <div v-if="showQrModal" class="qr-mask" @click="closeQrModal">
      <div class="qr-dialog" @click.stop>
        <div class="qr-title">支付宝扫码支付</div>
        <img v-if="qrImageUrl" class="qr-img" :src="qrImageUrl" alt="支付二维码" />
        <p class="qr-tip">请使用支付宝「扫一扫」完成支付</p>
        <button type="button" class="qr-close-btn" @click="closeQrModal">关闭</button>
      </div>
    </div>
  </div>
  
  <!-- 自定义底部栏 -->
  <view class="footer-tabbar">
    <view class="tab-item" @click="navTo('index')">首页</view>
    <view class="tab-item" @click="navTo('prepare')">备课</view>
    <view class="tab-item active">会员卡</view> <!-- 这里会员卡设为 active -->
    <view class="tab-item" @click="navTo('mine')">我的</view>
  </view>
  
  
</template>

<script setup>
import { ref, onMounted } from 'vue' // ✅ 必须导入 ref，否则脚本会报错中断
import QRCode from 'qrcode'
import { API_BASE } from '../../src/apiBase.js'
import { apiRequest } from '../../src/http.js'
import { getToken } from '../../src/auth.js'

const currentDays = ref(0)
const currentTestPenny = ref(false)
const showPaySheet = ref(false)
const selectedPayMode = ref('alipay')
const showQrModal = ref(false)
const qrImageUrl = ref('')

const payReturnBanner = ref(false)
const payReturnState = ref('') // polling | success | pending

/** hash ? 后与地址栏 ?query 合并（支付宝回跳常把参数放在 # 前面） */
function parsePayReturnQuery() {
  if (typeof window === 'undefined') return {}
  const hash = window.location.hash || ''
  const hi = hash.indexOf('?')
  const fromHash = hi === -1 ? '' : hash.slice(hi + 1)
  const fromSearch = (window.location.search || '').replace(/^\?/, '')
  const merged = [fromHash, fromSearch].filter(Boolean).join('&')
  if (!merged) return {}
  return Object.fromEntries(new URLSearchParams(merged))
}

const goLogin = () => {
  uni.reLaunch({ url: '/pages/login/login' })
}

onMounted(async () => {
  const q = parsePayReturnQuery()
  const orderNo = q.out_trade_no || q.order_no
  if (!orderNo || getToken()) return
  payReturnBanner.value = true
  payReturnState.value = 'polling'
  for (let i = 0; i < 20; i++) {
    try {
      const r = await fetch(
        `${API_BASE}/api/pay/order_result/${encodeURIComponent(orderNo)}`
      )
      const j = await r.json()
      if (j.code === 200 && j.data?.status === 'SUCCESS') {
        payReturnState.value = 'success'
        return
      }
    } catch (_) {
      /* ignore */
    }
    await new Promise((res) => setTimeout(res, 1000))
  }
  payReturnState.value = 'pending'
})

const paymentOptions = [
  { value: 'alipay', label: '支付宝支付', desc: '电脑网站支付（跳转收银台，可扫码）', icon: '支', iconClass: 'alipay' },
  { value: 'wxpay', label: '微信支付', desc: '可在微信环境内拉起支付', icon: '微', iconClass: 'wxpay' },
  { value: 'h5', label: '手机直接打开', desc: '直接跳转到支付链接', icon: '开', iconClass: 'h5' }
]

// 1. 打开支付选择菜单（testPenny：0.01 元测试单，见后端 test_penny）
const openPayMenu = (days, testPenny = false) => {
  currentDays.value = days
  currentTestPenny.value = testPenny
  selectedPayMode.value = 'alipay'
  showPaySheet.value = true
}

const closePaySheet = () => {
  showPaySheet.value = false
}

const confirmPay = () => {
  showPaySheet.value = false
  startPay(selectedPayMode.value)
}

const closeQrModal = () => {
  showQrModal.value = false
  qrImageUrl.value = ''
}

const showAlipayQr = async (payload) => {
  const raw = payload.qr_code
  if (!raw || typeof raw !== 'string') {
    uni.showToast({ title: '未获取到二维码数据', icon: 'none' })
    return
  }
  try {
    qrImageUrl.value = await QRCode.toDataURL(raw, { margin: 2, width: 240 })
    showQrModal.value = true
  } catch (e) {
    console.error(e)
    openExternalUrl(raw)
  }
}

const openExternalUrl = (url) => {
  // H5: 浏览器直接跳转，手机可直接打开
  if (typeof window !== 'undefined' && window.location) {
    window.location.href = url
    return
  }
  // App: 调用原生能力打开外链
  if (typeof plus !== 'undefined' && plus.runtime && plus.runtime.openURL) {
    plus.runtime.openURL(url)
    return
  }
  // 兜底：复制链接提示用户手动打开
  uni.setClipboardData({
    data: url,
    success: () => uni.showToast({ title: '已复制支付链接', icon: 'none' })
  })
}

const payErrorText = (data) => {
  const d = data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length) {
    return d.map((e) => (typeof e?.msg === 'string' ? e.msg : '')).filter(Boolean).join('；') || ''
  }
  return ''
}

// 2. 发起支付请求
const startPay = async (payMode) => {
  uni.showLoading({ title: '创建订单...' });
  let provider = 'alipay'
  let channel = 'pc'

  if (payMode === 'wxpay') {
    provider = 'wxpay'
    channel = 'h5'
  } else if (payMode === 'h5') {
    provider = 'h5'
    channel = 'h5'
  }

  try {
    const payload = {
      days: currentDays.value,
      test_penny: currentTestPenny.value,
      provider,
      channel,
    }
    if (provider === 'alipay' && typeof window !== 'undefined') {
      payload.return_url = window.location.href.split('?')[0]
    }
    const res = await apiRequest({
      url: '/api/pay/create_order',
      method: 'POST',
      data: payload,
    })
    uni.hideLoading()
    if (res.statusCode === 200 && res.data?.code === 200) {
      const payData = res.data || {}
      if (provider === 'alipay' && payData.qr_code) {
        await showAlipayQr(payData)
        return
      }
      if (payData.pay_url) {
        openExternalUrl(payData.pay_url)
        return
      }
      if (payData.qr_code) {
        openExternalUrl(payData.qr_code)
        return
      }

      const orderInfo = payData.orderInfo || ''
      if (typeof orderInfo === 'string' && (orderInfo.includes('simulation') || orderInfo.includes('MOCK'))) {
        uni.showModal({
          title: '模拟支付',
          content: '检测到未配置真实支付Key，是否模拟支付成功？',
          success: (mockRes) => {
            if (mockRes.confirm) mockSuccess()
          },
        })
        return
      }

      uni.showToast({ title: '暂未获取到可用支付链接', icon: 'none' })
    } else {
      const hint = payErrorText(res.data)
      uni.showToast({
        title: hint || (res.statusCode === 403 ? '无权限（如线上未开放测试单）' : '订单创建失败'),
        icon: 'none',
      })
    }
  } catch (_) {
    uni.hideLoading()
    uni.showToast({ title: '网络异常，请稍后重试', icon: 'none' })
  }
}

// 3. 支付成功后的处理
const mockSuccess = async () => {
  try {
    const res = await apiRequest({
      url: '/api/pay/mock_success',
      method: 'POST',
      data: { days: currentDays.value },
    })
    if (res.statusCode === 200 && res.data?.code === 200) {
      uni.showToast({ title: '开通成功！', icon: 'success' })
      setTimeout(() => {
        uni.reLaunch({ url: '/pages/mine/mine' })
      }, 1500)
    }
  } catch (_) {
    uni.showToast({ title: '模拟支付失败', icon: 'none' })
  }
}

// 4. ✅ 补全导航函数 (否则点击底部导航会报错)
const navTo = (page) => {
  const routes = {
    'index': '/pages/index/index',
    'prepare': '/pages/prepare/prepare',
    'mine': '/pages/mine/mine'
  }
  uni.reLaunch({ url: routes[page] });
}
</script>
<style scoped>
.pay-return-banner {
  background: #e8f4ff;
  border: 1px solid #b3d7ff;
  color: #1a1a1a;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
  font-size: 14px;
  line-height: 1.5;
}
.banner-login {
  color: #5c6ac4;
  font-weight: 700;
  text-decoration: underline;
  margin-left: 8px;
  cursor: pointer;
}
.page { min-height: 100vh; background-color: #F5F7FA; padding: 20px; }
.header { text-align: center; margin-bottom: 30px; }
.title { font-size: 22px; font-weight: bold; color: #333; margin-bottom: 10px; }
.subtitle { font-size: 14px; color: #666; margin-bottom: 5px; }
.subtitle-sm { font-size: 12px; color: #999; }

.vip-card {
  background: #fff; border-radius: 16px; padding: 30px 20px; margin-bottom: 20px;
  text-align: center; position: relative; border: 1px solid #eee;
}
.vip-card.test-pack {
  border: 1px dashed #e6a23c;
  background: #fffaf3;
}
.vip-card.recommend { border: 2px solid #FF6B6B; position: relative; }
.badge {
  position: absolute; top: -10px; right: 20px; background: #FF6B6B; color: #fff;
  padding: 4px 12px; border-radius: 12px; font-size: 12px;
}

.card-title { font-size: 18px; font-weight: bold; color: #555; margin-bottom: 10px; }
.card-price { font-size: 32px; font-weight: bold; color: #5C6AC4; margin-bottom: 10px; }
.card-price.test-price { color: #c77a16; }
.card-price.highlight { color: #5C6AC4; }
.days { font-size: 14px; color: #999; font-weight: normal; }
.card-desc { font-size: 14px; color: #666; margin-bottom: 20px; }

.features { text-align: left; padding-left: 20px; margin-bottom: 16px; }
.f-item { font-size: 14px; color: #333; margin-bottom: 8px; }
.test-pack-hint {
  font-size: 12px;
  color: #a67c00;
  line-height: 1.45;
  margin: 0 8px 16px;
  text-align: left;
}
.test-pack-hint code {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 4px;
}

.buy-btn {
  background: #5C6AC4; color: #fff; border-radius: 8px; border: none;
  height: 44px; line-height: 44px; width: 60%; font-size: 16px;
}
.buy-btn.test-buy-btn { background: #e6a23c; }

.pay-sheet-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.42);
  display: flex;
  align-items: flex-end;
  z-index: 1200;
}

.pay-sheet {
  width: 100%;
  background: #fff;
  border-radius: 20px 20px 0 0;
  padding: 18px 16px 24px;
}

.sheet-title {
  font-size: 16px;
  font-weight: 700;
  color: #222;
  margin-bottom: 10px;
}

.pay-method-list {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.pay-method-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 12px;
  border-bottom: 1px solid #f2f2f2;
  background: #fff;
}

.pay-method-item:last-child { border-bottom: none; }

.method-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.method-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  font-size: 14px;
  line-height: 30px;
  text-align: center;
  font-weight: 700;
}

.method-icon.alipay { background: #2f7cff; }
.method-icon.wxpay { background: #17b24a; }
.method-icon.h5 { background: #5c6ac4; }

.method-name {
  font-size: 16px;
  color: #222;
  font-weight: 600;
}

.method-desc {
  font-size: 12px;
  color: #8b8b8b;
  margin-top: 2px;
}

.radio-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1.5px solid #d7d7d7;
  position: relative;
}

.radio-dot.checked {
  border-color: #f0d992;
  background: #f5e3a7;
}

.radio-dot.checked::after {
  content: '✓';
  position: absolute;
  inset: 0;
  text-align: center;
  line-height: 22px;
  font-size: 14px;
  color: #222;
  font-weight: 700;
}

.confirm-pay-btn {
  width: 100%;
  height: 44px;
  line-height: 44px;
  margin-top: 14px;
  border-radius: 10px;
  border: none;
  background: #2f5fd3;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.qr-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1300;
  padding: 20px;
}
.qr-dialog {
  background: #fff;
  border-radius: 16px;
  padding: 24px 20px;
  max-width: 320px;
  width: 100%;
  text-align: center;
}
.qr-title {
  font-size: 17px;
  font-weight: 700;
  color: #222;
  margin-bottom: 16px;
}
.qr-img {
  width: 240px;
  height: 240px;
  display: block;
  margin: 0 auto;
}
.qr-tip {
  font-size: 13px;
  color: #666;
  margin: 14px 0 18px;
}
.qr-close-btn {
  width: 100%;
  height: 42px;
  line-height: 42px;
  border-radius: 10px;
  border: none;
  background: #eef1f6;
  color: #333;
  font-size: 15px;
}

.pay-info { text-align: center; margin-top: 40px; padding-bottom: 30px; }
.pay-title { font-size: 16px; font-weight: bold; color: #5C6AC4; margin-bottom: 10px; }
.pay-desc { font-size: 12px; color: #666; margin-bottom: 5px; }
.pay-tip { font-size: 10px; color: #999; }


/* 确保 .page 有底部内边距，防止内容被遮挡 */
.page { padding-bottom: 120rpx !important; }

.footer-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 100rpx;
  background-color: #5C6AC4;
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 999;
}
.tab-item {
  color: #FFFFFF;
  font-size: 28rpx;
  flex: 1;
  text-align: center;
  opacity: 0.7;
}
.tab-item.active {
  opacity: 1;
  font-weight: bold;
}
</style>