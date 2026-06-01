<template>
  <view class="page">
    <!-- 顶部标题栏 -->
    <view class="header">
      <view class="title">开始备课</view>
    </view>

    <!-- 主操作卡片 -->
    <view class="card">
      <view class="form-title">AI 全能备课助手</view>
      
      <!-- 1. 学段选择（H5 用原生 select；uni 小程序仍可用下方 picker 分支） -->
      <view class="input-group">
        <view class="label">所属学段</view>
        <select v-model="grade" class="picker-box select-native">
          <option value="" disabled>点击选择（小学/初中/高中）</option>
          <option v-for="g in grades" :key="g" :value="g">{{ g }}</option>
        </select>
      </view>

      <!-- 2. 学科选择 -->
      <view class="input-group">
        <view class="label">教学学科</view>
        <select v-model="subject" class="picker-box select-native">
          <option value="" disabled>点击选择学科（语数外等）</option>
          <option v-for="s in subjects" :key="s" :value="s">{{ s }}</option>
        </select>
      </view>

      <!-- 3. 课题名称 -->
      <view class="input-group">
        <view class="label">课题名称</view>
        <input 
          class="input" 
          placeholder="如：勾股定理、赤壁赋" 
          v-model="topic" 
          placeholder-style="color: #CCC;"
        />
      </view>

      <!-- 生成按钮 -->
      <button class="submit-btn" @click="doGenerate">立即生成全套资源</button>

      <!-- 底部提示区 -->
      <view class="result-preview">
        <view class="preview-title">生成内容包括：</view>
        <view class="preview-item">• 1. 教学教案 (标准的 Word 文档)</view>
        <view class="preview-item">• 2. 100分制练习题 (带解析 Word)</view>
        <view class="preview-item">• 3. 交互式 H5 课件 (课堂演示网页)</view>
      </view>
    </view>

    <!-- 自定义底部栏 (保持一致) -->
    <view class="footer-tabbar">
      <view class="tab-item" @click="navTo('index')">首页</view>
      <view class="tab-item active">备课</view>
      <view class="tab-item" @click="navTo('vip')">会员卡</view>
      <view class="tab-item" @click="navTo('mine')">我的</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue';
import { API_BASE } from '../../src/apiBase.js';
import { apiRequest } from '../../src/http.js';

const topic = ref('');
const grade = ref('');
const subject = ref('');

const grades = ['小学', '初中', '高中'];
const subjects = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治'];

const navTo = (name) => {
  uni.reLaunch({ url: `/pages/${name}/${name}` });
};

const doGenerate = async () => {
  if (!topic.value || !grade.value || !subject.value) {
    return uni.showToast({ title: '请填写完整信息', icon: 'none' });
  }

  uni.showLoading({ title: 'AI 正在编写中...' });

  try {
    const res = await apiRequest({
      url: '/api/generate',
      method: 'POST',
      timeout: 120000,
      data: {
        topic: topic.value,
        grade: grade.value,
        subject: subject.value,
      },
    });
    uni.hideLoading();
    if (res.statusCode === 200 && res.data?.code === 200) {
      const baseUrl = `${API_BASE}/static/`;
      const planUrl = baseUrl + res.data.data.plan;
      const quizUrl = baseUrl + res.data.data.quiz;
      const htmlUrl = baseUrl + res.data.data.html;

      uni.showModal({
        title: '生成成功',
        content: '全套资源已准备就绪，是否立即查看下载链接？',
        confirmText: '去查看',
        success: (modalRes) => {
          if (modalRes.confirm) {
            const history = uni.getStorageSync('history') || [];
            history.unshift({
              topic: topic.value,
              subject: subject.value,
              time: new Date().toLocaleString(),
              planUrl,
              quizUrl,
              htmlUrl,
            });
            uni.setStorageSync('history', history);
            uni.reLaunch({ url: '/pages/index/index' });
          }
        },
      });
    } else {
      const d = res.data?.detail;
      uni.showToast({
        title: typeof d === 'string' ? d : '生成失败',
        icon: 'none',
      });
    }
  } catch (err) {
    uni.hideLoading();
    const msg = err?.errMsg || '';
    if (msg.indexOf('timeout') !== -1) {
      uni.showToast({ title: 'AI思考时间较长，请稍后在记录中查看', icon: 'none' });
    } else {
      uni.showToast({ title: '请求失败', icon: 'none' });
    }
  }
};
</script>

<style scoped>
/* 保持背景色一致 */
.page { 
  min-height: 100vh; 
  background-color: #F8F9FB; 
  padding: 20px; 
  padding-bottom: 120rpx;
  box-sizing: border-box; 
}

.header { margin-bottom: 20px; margin-top: 10px; }
.title { font-size: 24px; font-weight: bold; color: #333; }

/* 卡片样式：保持跟首页、VIP页完全一致 */
.card { 
  background: #ffffff; 
  border-radius: 16px; 
  padding: 25px; 
  box-shadow: 0 8px 24px rgba(0,0,0,0.04); 
}

.form-title { font-size: 18px; font-weight: bold; margin-bottom: 25px; color: #333; }

/* 输入组样式 */
.input-group { margin-bottom: 20px; }
.label { font-size: 14px; font-weight: bold; color: #444; margin-bottom: 10px; display: block; }

/* 选择框和输入框样式统一 */
.input, .picker-box {
  width: 100%; 
  height: 50px; 
  background: #FDFDFD;
  border: 1px solid #E0E0E0; 
  border-radius: 10px; 
  padding: 0 15px;
  box-sizing: border-box; 
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 原生下拉（H5 / 浏览器） */
.select-native {
  cursor: pointer;
  color: #333;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%23BBB' d='M1 1l5 5 5-5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 14px center;
  padding-right: 36px;
}
.select-native:invalid,
.select-native option[value=""] {
  color: #ccc;
}
.select-native option:not([value=""]) {
  color: #333;
}

/* 按钮样式：使用招牌紫色 #5C6AC4 */
.submit-btn {
  background: #5C6AC4;
  color: #fff; 
  border-radius: 10px; 
  height: 52px; 
  line-height: 52px;
  font-size: 16px; 
  font-weight: bold; 
  margin-top: 30px; 
  border: none;
  box-shadow: 0 4px 12px rgba(92, 106, 196, 0.3);
}
.submit-btn:active { transform: scale(0.98); opacity: 0.9; }

/* 预览区样式 */
.result-preview {
  margin-top: 30px; 
  background: #F0F4F8; 
  padding: 20px; 
  border-radius: 12px;
}
.preview-title { font-size: 14px; font-weight: bold; color: #333; margin-bottom: 10px; }
.preview-item { font-size: 13px; color: #666; line-height: 2; }

/* 底部导航栏（固定样式） */
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
.tab-item { color: #FFFFFF; font-size: 28rpx; flex: 1; text-align: center; opacity: 0.7; }
.tab-item.active { opacity: 1; font-weight: bold; }
</style>