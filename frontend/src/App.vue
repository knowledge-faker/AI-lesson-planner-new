<template>
  <component :is="currentComp" />
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import IndexPage from '../pages/index/index.vue'
import PreparePage from '../pages/prepare/prepare.vue'
import VipPage from '../pages/vip/vip.vue'
import MinePage from '../pages/mine/mine.vue'
import LoginPage from '../pages/login/login.vue'
import RegisterPage from '../pages/register/register.vue'
import { getToken, isPublicPath, hashPathOnly } from './auth.js'

const routePath = ref('/pages/login/login')

/** 完整 hash 路由（含 query）；routePath 只用「无 query」的路径以匹配页面 map */
const normalizeFull = () => {
  const hash = window.location.hash || ''
  return hash.replace(/^#/, '') || '/pages/index/index'
}

const onHashChange = () => {
  const full = normalizeFull()
  const pathOnly = hashPathOnly(full)
  if (!getToken() && !isPublicPath(full)) {
    if (window.location.hash !== '#/pages/login/login') {
      window.location.hash = '#/pages/login/login'
    }
    return
  }
  routePath.value = pathOnly
}

onMounted(() => {
  if (!window.location.hash) {
    window.location.hash = getToken() ? '#/pages/index/index' : '#/pages/login/login'
  }
  const full = normalizeFull()
  const pathOnly = hashPathOnly(full)
  if (!getToken() && !isPublicPath(full)) {
    window.location.hash = '#/pages/login/login'
    routePath.value = '/pages/login/login'
  } else {
    routePath.value = pathOnly
  }
  window.addEventListener('hashchange', onHashChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', onHashChange)
})

const map = {
  '/pages/index/index': IndexPage,
  '/pages/prepare/prepare': PreparePage,
  '/pages/vip/vip': VipPage,
  '/pages/mine/mine': MinePage,
  '/pages/login/login': LoginPage,
  '/pages/register/register': RegisterPage,
}

const currentComp = computed(() => map[routePath.value] || LoginPage)
</script>

<style>
* {
  box-sizing: border-box;
}

html, body, #app {
  margin: 0;
  padding: 0;
  width: 100%;
  min-height: 100%;
  background: #f8f9fb;
}

view {
  display: block;
}

text {
  display: inline;
}

button {
  font: inherit;
  color: inherit;
  background: transparent;
  border: none;
  margin: 0;
  padding: 0;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
}
</style>
