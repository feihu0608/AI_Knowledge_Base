<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, session } from '../api'

const router = useRouter()
const busy = ref(false), error = ref(''), showPassword = ref(false)
const form = reactive({ tenant_id: 'demo-acme', username: 'admin_acme', password: 'DemoOnly!2026' })
async function submit() {
  busy.value = true; error.value = ''
  try { const result = await api('/api/auth/login', { method: 'POST', body: JSON.stringify(form) }); session.token = result.access_token; router.push('/dashboard') }
  catch (e) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <div class="login-page">
    <div class="login-glow glow-one"></div><div class="login-glow glow-two"></div>
    <div class="login-layout">
      <section class="login-intro"><div class="login-brand"><span class="brand-mark">知</span><div><b>知汇台</b><small>AI KNOWLEDGE HUB</small></div></div><div class="intro-copy"><span class="intro-kicker">ENTERPRISE KNOWLEDGE</span><h1>让每一份知识<br><em>都能被正确使用。</em></h1><p>统一沉淀企业文档、制度与经验，让团队在可信的知识边界内快速获得答案。</p></div><div class="intro-footer"><span><i>✓</i> 多租户隔离</span><span><i>✓</i> 权限可追溯</span><span><i>✓</i> 三路智能检索</span></div></section>
      <section class="login-panel"><div class="login-card"><div class="mobile-brand"><span class="brand-mark">知</span><b>知汇台</b></div><div class="login-card-head"><span class="eyebrow">SECURE WORKSPACE</span><h2>欢迎回来</h2><p>登录你的企业知识空间</p></div><form @submit.prevent="submit"><label><span>租户 ID</span><div class="field"><i>⌂</i><input v-model="form.tenant_id" autocomplete="organization" placeholder="输入租户 ID"></div></label><label><span>账号</span><div class="field"><i>◎</i><input v-model="form.username" autocomplete="username" placeholder="输入账号"></div></label><label><span>密码</span><div class="field"><i>●</i><input v-model="form.password" :type="showPassword?'text':'password'" autocomplete="current-password" placeholder="输入密码"><button type="button" class="password-toggle" @click="showPassword=!showPassword">{{showPassword?'隐藏':'显示'}}</button></div></label><p v-if="error" class="login-error"><b>!</b>{{error}}</p><button class="login-submit" :disabled="busy">{{busy?'正在验证…':'进入知识空间'}}<span v-if="!busy">↗</span></button></form><div class="login-note"><span class="status-dot"></span><span>当前为试点环境 · 演示账号已预填</span></div></div><div class="login-bottom">© 2026 知汇台 · 企业知识管理平台</div></section>
    </div>
  </div>
</template>
