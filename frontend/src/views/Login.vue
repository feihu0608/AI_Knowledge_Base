<script setup>
import { reactive, ref } from 'vue'; import { useRouter } from 'vue-router'; import { api, session } from '../api'
const router=useRouter(), busy=ref(false), error=ref('')
const form=reactive({tenant_id:'demo-acme',username:'admin_acme',password:'DemoOnly!2026'})
async function submit(){busy.value=true;error.value='';try{const r=await api('/api/auth/login',{method:'POST',body:JSON.stringify(form)});session.token=r.access_token;router.push('/knowledge')}catch(e){error.value=e.message}finally{busy.value=false}}
</script>
<template><div class="login"><form class="card login-card" @submit.prevent="submit"><div class="eyebrow">ENTERPRISE KNOWLEDGE</div><h1>登录知汇台</h1><p>进入所属租户的知识空间</p><label>租户 ID<input v-model="form.tenant_id"></label><label>账号<input v-model="form.username"></label><label>密码<input v-model="form.password" type="password"></label><p v-if="error" class="error">{{error}}</p><button :disabled="busy">{{busy?'登录中…':'安全登录'}}</button><small>当前预填为虚构演示账号</small></form></div></template>
