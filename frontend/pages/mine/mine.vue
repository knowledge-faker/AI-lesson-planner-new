<template>
	<view class="page">
		<view class="header-title">个人中心</view>

		<!-- 用户信息卡片 -->
		<view class="user-card">
			<view class="info-row">
				<text class="label">昵称：</text>
				<text class="value">{{ userInfo.nickname }}</text>
			</view>
			<view class="info-row">
				<text class="label">VIP状态：</text>
				<!-- 根据后端返回的 is_vip 动态切换类名 -->
				<text :class="userInfo.is_vip ? 'tag-vip active' : 'tag-vip'">
					{{ userInfo.is_vip ? 'VIP会员' : '普通用户' }}
				</text>
			</view>
			<view class="info-row" v-if="userInfo.is_vip">
				<text class="label">有效期至：</text>
				<text class="value-sm">{{ userInfo.vip_expiry_str }}</text>
			</view>

			<view class="btn-row">
				<button class="btn-upgrade" @click="navTo('vip')">升级VIP</button>
				<button class="btn-logout" @click="logout">退出登录</button>
			</view>
		</view>

		<!-- 使用统计 -->
		<view class="stats-container">
			<view class="section-title">使用统计</view>
			<view class="stats-grid">
				<view class="stat-item">
					<view class="stat-label">生成次数</view>
					<view class="stat-num">{{ userInfo.stats.total }}</view>
				</view>
				<view class="stat-item">
					<view class="stat-label">已生成课件</view>
					<view class="stat-num">{{ userInfo.stats.lesson }}</view>
				</view>
				<view class="stat-item">
					<view class="stat-label">已生成练习题</view>
					<view class="stat-num">{{ userInfo.stats.quiz }}</view>
				</view>
				<view class="stat-item">
					<view class="stat-label">已生成网页</view>
					<view class="stat-num">{{ userInfo.stats.html }}</view>
				</view>
			</view>
		</view>

		<button class="history-btn" @click="navTo('index')">查看生成记录</button>

		<!-- 自定义底部栏 -->
		<view class="footer-tabbar">
			<view class="tab-item" @click="navTo('index')">首页</view>
			<view class="tab-item" @click="navTo('prepare')">备课</view>
			<view class="tab-item" @click="navTo('vip')">会员卡</view>
			<view class="tab-item active">我的</view>
		</view>
	</view>
</template>

<script setup>
	import { ref } from 'vue';
	import { onMounted } from 'vue';
	import { apiRequest } from '../../src/http.js';
	import { clearAuth } from '../../src/auth.js';

	const userInfo = ref({
		nickname: '加载中...',
		is_vip: false,
		vip_expiry_str: '',
		stats: { total: 0, lesson: 0, quiz: 0, html: 0 }
	});

	onMounted(async () => {
		try {
			const res = await apiRequest({ url: '/api/user/info', method: 'GET' });
			if (res.statusCode === 200 && res.data?.code === 200) {
				const data = res.data.data;
				userInfo.value = data;
				if (data.vip_expiry) {
					userInfo.value.vip_expiry_str = data.vip_expiry.split('T')[0];
				}
			}
		} catch (_) {
			uni.showToast({ title: '无法连接到服务器', icon: 'none' });
		}
	});

	const navTo = (name) => {
		uni.reLaunch({ url: `/pages/${name}/${name}` });
	};

	const logout = () => {
		clearAuth();
		uni.reLaunch({ url: '/pages/login/login' });
	};
</script>

<style scoped>
	.page {
		min-height: 100vh;
		background-color: #F5F7FA;
		padding: 20px;
		padding-bottom: 140rpx;
	}

	.header-title {
		font-size: 24px;
		font-weight: bold;
		color: #333;
		margin-bottom: 20px;
	}

	.user-card {
		background: #fff;
		border-radius: 12px;
		padding: 25px;
		margin-bottom: 20px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
	}

	.info-row {
		display: flex;
		align-items: center;
		margin-bottom: 15px;
	}

	.label {
		width: 160rpx;
		font-size: 16px;
		color: #666;
		font-weight: bold;
	}

	.value {
		font-size: 16px;
		color: #333;
	}
	
	.value-sm { font-size: 14px; color: #999; }

	.tag-vip {
		background: #F5F5F5;
		color: #999;
		padding: 4rpx 20rpx;
		border-radius: 6rpx;
		font-size: 14px;
	}

	.tag-vip.active {
		background: #FFF3E0;
		color: #FF9800;
	}

	.btn-row {
		display: flex;
		gap: 15px;
		margin-top: 25px;
	}

	.btn-upgrade {
		flex: 1;
		background: #5C6AC4;
		color: #fff;
		border: none;
		height: 40px;
		line-height: 40px;
		border-radius: 6px;
		font-size: 15px;
	}

	.btn-logout {
		flex: 1;
		background: #F5F5F5;
		color: #333;
		border: none;
		height: 40px;
		line-height: 40px;
		border-radius: 6px;
		font-size: 15px;
	}

	.section-title {
		font-size: 18px;
		font-weight: bold;
		color: #333;
		margin-bottom: 15px;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 15px;
		margin-bottom: 30px;
	}

	.stat-item {
		background: #fff;
		padding: 20px;
		border-radius: 8px;
		text-align: center;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
	}

	.stat-label {
		font-size: 13px;
		color: #666;
		margin-bottom: 5px;
	}

	.stat-num {
		font-size: 24px;
		font-weight: bold;
		color: #5C6AC4;
	}

	.history-btn {
		width: 100%;
		height: 44px;
		line-height: 44px;
		background: #EEE;
		color: #333;
		border: none;
		border-radius: 6px;
		font-size: 15px;
	}

	/* 底部栏样式 */
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