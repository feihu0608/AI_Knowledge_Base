<script setup>
import { onMounted, ref } from 'vue'; import { api } from '../api'
const bases=ref([]), selected=ref(null), message=ref(''), error=ref('')
async function load(){try{bases.value=await api('/api/knowledge-bases');selected.value ||= bases.value[0]}catch(e){error.value=e.message}}
async function upload(event){const file=event.target.files[0];if(!file||!selected.value)return;const body=new FormData();body.append('file',file);try{const r=await api(`/api/knowledge-bases/${selected.value.id}/documents`,{method:'POST',body});message.value=`已进入导入队列：${r.job_id}（${r.provider_mode}）`}catch(e){error.value=e.message}}
onMounted(load)
</script>
<template><section><div class="title-row"><div><div class="eyebrow">KNOWLEDGE GOVERNANCE</div><h1>知识库管理</h1><p>原文、版本、权限和索引任务全程留痕。</p></div><label class="upload">导入文档<input type="file" accept=".pdf,.md,.txt,.doc,.docx" @change="upload"></label></div><p v-if="message" class="notice">{{message}}</p><p v-if="error" class="error">{{error}}</p><div class="grid"><button v-for="item in bases" :key="item.id" class="card kb" :class="{selected:selected?.id===item.id}" @click="selected=item"><span class="kb-icon">文</span><div><b>{{item.name}}</b><small>{{item.id}} · {{item.enabled?'已启用':'已停用'}}</small></div></button></div></section></template>
