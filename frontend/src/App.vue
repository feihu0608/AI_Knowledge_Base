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
      <div class="nav-label">工作台</div>
      <nav>
        <router-link to="/dashboard"><span>⌂</span>运营看板</router-link>
        <router-link to="/knowledge"><span>▤</span>知识维护与导入</router-link>
        <router-link to="/chat"><span>✦</span>AI 智能问答</router-link>
        <router-link to="/operations"><span>◈</span>知识沉淀与运营</router-link>
      </nav>
      <div class="nav-label nav-label-bottom">系统管理</div>
      <nav>
        <router-link to="/organization"><span>⌘</span>组织与系统配置</router-link>
      </nav>
      <div class="tenant-badge"><span class="status-dot"></span><div><b>远航科技</b><small>demo-acme · 试点租户</small></div></div>
      <button class="ghost" @click="logout">退出登录</button>
    </aside>
    <main :class="{'chat-shell-main': route.path === '/chat'}"><header><b>企业知识工作台</b><span>多租户 · 权限隔离 · 可追溯引用</span></header><router-view /></main>
  </div>
</template>
