<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { api } from '../api'

const question = ref(''), messages = ref([]), busy = ref(false), conversation = ref(null), activeHistory = ref(null), notice = ref('')
const history = ref([])
const suggestions = ['差旅怎么报销？', '如何申请远程办公 VPN？', '采购合同审批要经过哪些节点？', '新员工入职第一天需要做什么？']
const chatTitle = computed(() => messages.value.find(item => item.role === 'user')?.text || '新的知识问答')
const scroller = ref(null)
function newChat() { messages.value = []; conversation.value = null; activeHistory.value = null; question.value = '' }
async function loadHistory() { try { const rows = await api('/api/chat/conversations'); history.value = rows.map(item => ({ id: item.id, title: item.title, time: new Date(item.updated_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) })) } catch (_) { history.value = [] } }
async function openHistory(item) { try { const result = await api(`/api/chat/conversations/${item.id}`); conversation.value = item.id; activeHistory.value = item.id; messages.value = result.messages.map(message => ({ role: message.role, text: message.content, evidence: [], warnings: [] })) } catch (e) { messages.value.push({ role: 'error', text: e.message }) } }
function useSuggestion(value) { question.value = value; nextTick(() => document.querySelector('.composer textarea')?.focus()) }
function handleComposerKeydown(event) { if (event.shiftKey) return; event.preventDefault(); ask() }
function looksLikeCode(text) { return /```|function |const |SELECT |import /.test(text || '') }
async function typeAnswer(target, text) { for (const char of text) { target.text += char; await new Promise(resolve => setTimeout(resolve, 8)); await nextTick(); if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight } }
async function ask() {
  if (!question.value.trim() || busy.value) return
  const q = question.value.trim(); question.value = ''; messages.value.push({ role: 'user', text: q }); busy.value = true
  const assistant = { role: 'assistant', text: '', evidence: [], warnings: [], mode: '' }; messages.value.push(assistant)
  try {
    const result = await api('/api/chat', { method: 'POST', body: JSON.stringify({ question: q, conversation_id: conversation.value }) })
    conversation.value = result.conversation_id; assistant.mode = result.provider_mode; assistant.evidence = result.evidence || []; assistant.warnings = result.warnings || []
    await typeAnswer(assistant, result.answer || '暂未生成答案，请补充问题。')
    activeHistory.value = conversation.value
    if (!history.value.some(item => item.id === conversation.value)) history.value.unshift({ id: conversation.value, title: q, time: '刚刚' })
  } catch (e) { assistant.text = e.message; assistant.role = 'error' } finally { busy.value = false }
}
onMounted(loadHistory)
</script>

<template>
  <section class="chat-page"><div class="chat-layout">
    <aside class="history-panel card"><div class="history-head"><div><b>历史会话</b><small>仅显示当前用户</small></div><button class="icon-button" title="新建会话" @click="newChat">＋</button></div><button class="new-chat" @click="newChat">＋ 开始新对话</button><div class="history-list"><button v-for="item in history" :key="item.id" class="history-item" :class="{active:activeHistory===item.id}" @click="openHistory(item)"><span class="history-dot"></span><div><b>{{item.title}}</b><small>{{item.time}}</small></div></button></div><div class="history-foot"><span class="status-dot"></span>三路检索已启用</div></aside>
    <div class="chat-main"><div class="chat-heading"><div><div class="eyebrow">THREE-WAY ANSWERING</div><h1>AI 智能问答工作台</h1><p>本地 Milvus 知识库 + 百炼 MCP + 模型一般知识，合并生成可追溯答案。</p></div><span class="online-pill"><i></i>服务在线</span></div>
      <div ref="scroller" class="messages card"><div v-if="!messages.length" class="welcome"><span class="welcome-icon">✦</span><h2>今天想了解什么？</h2><p>先从一个常见问题开始，答案会逐字呈现并附带引用证据。</p><div class="suggestions"><button v-for="item in suggestions" :key="item" @click="useSuggestion(item)">{{item}} <span>→</span></button></div></div><article v-for="(m, i) in messages" :key="i" :class="m.role"><div class="message-avatar">{{m.role==='user'?'你':'知'}}</div><div class="message-content"><div class="message-meta"><b>{{m.role==='user'?'你':'知识助手'}}</b><small v-if="m.mode">{{m.mode}} · {{m.evidence.length}} 条引用</small></div><p v-if="!looksLikeCode(m.text)" class="answer-text">{{m.text}}<i v-if="busy && i===messages.length-1" class="typing-caret"></i></p><pre v-else class="code-block"><code>{{m.text}}</code></pre><div v-if="m.role==='assistant' && m.warnings?.length" class="security-hint">⚠ 检索范围受权限策略限制，部分资料未展示正文。</div><div v-if="m.role==='assistant' && m.evidence?.length" class="evidence-list"><b class="evidence-title">引用溯源</b><div v-for="source in m.evidence" :key="source.evidence_id" class="evidence-card"><span class="source-badge" :class="source.source_type">{{source.source_type==='local'?'本地':source.source_type==='mcp'?'MCP':'通用'}}</span><div><b>{{source.title || '未命名来源'}}</b><small>{{source.excerpt || '已通过权限校验，可查看摘要'}}</small></div><span class="score">{{source.score ? Number(source.score).toFixed(2) : '—'}}</span></div></div></div></article></div>
      <form class="composer" @submit.prevent="ask"><textarea v-model="question" :disabled="busy" placeholder="输入企业知识问题…（回车发送，Shift + 回车换行）" @keydown.enter="handleComposerKeydown"></textarea><button :disabled="busy || !question.trim()">{{busy?'生成中…':'发送 ↗'}}</button></form><small class="composer-tip">回车发送 · Shift + 回车换行 · 回答由已授权知识生成，请在使用前核对引用来源。</small>
    </div>
  </div></section>
</template>
