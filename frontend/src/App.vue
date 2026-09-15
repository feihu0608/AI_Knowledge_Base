<script setup>
import { useRoute, useRouter } from 'vue-router'
import { session } from './api'
const route = useRoute(); const router = useRouter()
function logout(){ session.token = null; router.push('/login') }
</script>
<template>
  <div v-if="route.path === '/login'"><router-view /></div>
  <div v-else class="shell">
    <aside><div class="brand">知汇台 <small>AI Knowledge</small></div>
      <nav><router-link to="/knowledge">知识库管理</router-link><router-link to="/chat">智能问答</router-link></nav>
      <button class="ghost" @click="logout">退出登录</button>
    </aside>
    <main><header><b>企业知识工作台</b><span>多租户 · 权限隔离 · 可追溯引用</span></header><router-view /></main>
  </div>
</template>
