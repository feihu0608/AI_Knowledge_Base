<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const activeTab = ref('recommend')
const notice = ref('')
const error = ref('')
const editItem = ref(null)
const editKind = ref('candidate')
const editDraft = ref({ question: '', answer: '' })
const search = ref('')
const recommendations = ref([
  { id: 'FAQ-2026-031', question: '差旅报销需要哪些材料？', count: 186, time: '近 7 天', answer: '请提供发票、行程单及审批单，按差旅制度提交至费用系统。', status: '待审核' },
  { id: 'FAQ-2026-030', question: '如何申请远程办公 VPN？', count: 142, time: '近 7 天', answer: '在 IT 服务台提交远程办公申请，审批通过后按指引安装客户端。', status: '待审核' },
  { id: 'FAQ-2026-029', question: '采购合同审批要经过哪些节点？', count: 97, time: '近 30 天', answer: '需求部门、采购、法务和财务依次完成审核，金额较大时需总经理审批。', status: '待审核' },
])
const published = ref([
  { id: 'FAQ-2026-021', question: '忘记密码如何处理？', answer: '联系 IT 服务台核验身份后重置密码。', updated: '今天 09:32', enabled: true },
  { id: 'FAQ-2026-018', question: '员工入职第一天需要做什么？', answer: '完成人事资料、门禁和设备领取，参加新员工培训。', updated: '昨天 16:08', enabled: true },
])
const gaps = ref([
  { question: '海外出差的保险如何购买？', count: 31, confidence: '0.31', last: '今天 10:24' },
  { question: '研发设备报废审批在哪个系统？', count: 18, confidence: '0.42', last: '昨天 18:41' },
  { question: '供应商发票抬头可以修改吗？', count: 12, confidence: '0.45', last: '昨天 14:16' },
])
const tabLabel = computed(() => ({recommend:'FAQ 挖掘与审核', published:'已发布 FAQ', gaps:'知识缺口清单'}[activeTab.value]))
const filteredPublished = computed(() => published.value.filter(item => `${item.question} ${item.answer}`.toLowerCase().includes(search.value.toLowerCase())))
async function loadData(){ try { const [c, p, g] = await Promise.all([api('/api/operations/faq/candidates'), api('/api/operations/faq/published'), api('/api/operations/gaps')]); if(c.length) recommendations.value=c.map(x=>({id:x.id,question:x.question,answer:x.answer,count:x.frequency,time:'实时聚合',status:x.state==='draft'?'待审核':x.state})); if(p.length) published.value=p.map(x=>({id:x.id,question:x.question,answer:x.answer,updated:new Date(x.updated_at).toLocaleString('zh-CN'),enabled:x.status==='enabled'})); if(g.length) gaps.value=g.map(x=>({id:x.id,question:x.question,count:x.frequency,confidence:x.reason==='no_hit'?'0.00':'0.42',last:new Date(x.updated_at).toLocaleString('zh-CN')})) } catch(e) { error.value=e.message } }
function openEdit(item){ editItem.value=item; editKind.value=recommendations.value.includes(item)?'candidate':'published'; editDraft.value={question:item.question, answer:item.answer} }
async function saveEdit(){ if(!editItem.value)return; try { if(editKind.value==='candidate'){ const result=await api(`/api/operations/faq/candidates/${editItem.value.id}/publish`,{method:'POST',body:JSON.stringify(editDraft.value)}); published.value.unshift({id:result.id,question:result.question,answer:result.answer,updated:'刚刚',enabled:true}); recommendations.value=recommendations.value.filter(x=>x.id!==editItem.value.id); notice.value=`FAQ「${result.question}」已保存并发布。` } else { await api(`/api/operations/faq/published/${editItem.value.id}`,{method:'PATCH',body:JSON.stringify({status:editItem.value.enabled?'enabled':'disabled',question:editDraft.value.question,answer:editDraft.value.answer})}); editItem.value.question=editDraft.value.question; editItem.value.answer=editDraft.value.answer; notice.value='已保存 FAQ 内容。' } editItem.value=null } catch(e) { error.value=e.message } setTimeout(()=>notice.value='', 2600) }
function publish(item){ openEdit(item) }
async function reject(item){ try { await api(`/api/operations/faq/candidates/${item.id}/reject`); recommendations.value=recommendations.value.filter(row=>row.id!==item.id); notice.value='已驳回该推荐问题' } catch(e) { error.value=e.message } setTimeout(()=>notice.value='', 2200) }
async function toggleCache(item){ try { const result=await api(`/api/operations/faq/published/${item.id}`,{method:'PATCH',body:JSON.stringify({status:item.enabled?'enabled':'disabled'})}); item.enabled=result.status==='enabled'; notice.value=item.enabled?'FAQ 缓存已生效':'FAQ 缓存已暂停' } catch(e) { item.enabled=!item.enabled; error.value=e.message } }
async function createTask(item){ try { await api(`/api/operations/gaps/${item.id}/task`,{method:'POST'}); gaps.value=gaps.value.filter(row=>row.id!==item.id); notice.value=`已创建知识补充任务：${item.question}` } catch(e) { error.value=e.message } setTimeout(()=>notice.value='', 2600) }
onMounted(loadData)
</script>

<template>
  <section class="operations-page">
    <div class="title-row"><div><div class="eyebrow">KNOWLEDGE OPERATIONS</div><h1>知识沉淀与运营</h1><p>把高频对话沉淀成标准答案，持续补齐知识缺口。</p></div><span class="pilot-tag">试点演示数据</span></div>
    <p v-if="notice" class="notice">{{notice}}</p><p v-if="error" class="error">{{error}}</p>
    <div class="tab-bar card"><button :class="{active:activeTab==='recommend'}" @click="activeTab='recommend'">FAQ 挖掘与审核 <b>{{recommendations.length}}</b></button><button :class="{active:activeTab==='published'}" @click="activeTab='published'">已发布 FAQ <b>{{published.length}}</b></button><button :class="{active:activeTab==='gaps'}" @click="activeTab='gaps'">知识缺口 <b>{{gaps.length}}</b></button></div>

    <article class="card operations-panel"><div class="panel-heading"><div><b>{{tabLabel}}</b><small v-if="activeTab==='recommend'">基于历史对话聚类，按频次和相似度排序</small><small v-else-if="activeTab==='published'">标准问答对与缓存生效控制</small><small v-else>检索未命中或置信度偏低的问题</small></div><div class="panel-tools"><input v-if="activeTab==='published'" v-model="search" class="inline-search" placeholder="检索 FAQ…"><button v-if="activeTab==='published'" class="secondary">批量刷新缓存</button></div></div>
      <div v-if="activeTab==='recommend'" class="faq-list"><div v-for="item in recommendations" :key="item.id" class="faq-row"><div class="faq-count"><strong>{{item.count}}</strong><small>聚合频次</small></div><div class="faq-body"><div class="faq-meta"><span>{{item.id}}</span><span>{{item.time}}</span><span class="status pending">{{item.status}}</span></div><h3>{{item.question}}</h3><p>{{item.answer}}</p></div><div class="row-actions"><button class="secondary" @click="publish(item)">采纳编辑</button><button class="ghost small-button" @click="reject(item)">驳回</button></div></div></div>
      <div v-else-if="activeTab==='published'" class="faq-list"><div v-for="item in filteredPublished" :key="item.id" class="faq-row published-row"><div class="doc-mark faq-mark">问</div><div class="faq-body"><div class="faq-meta"><span>{{item.id}}</span><span>更新于 {{item.updated}}</span></div><h3>{{item.question}}</h3><p>{{item.answer}}</p></div><label class="switch-label"><input v-model="item.enabled" type="checkbox" @change="toggleCache(item)"><i></i><span>{{item.enabled?'缓存已生效':'缓存已暂停'}}</span></label><button class="secondary" @click="openEdit(item)">编辑</button></div><div v-if="!filteredPublished.length" class="empty compact-empty">没有匹配的 FAQ</div></div>
      <div v-else class="faq-list"><div v-for="item in gaps" :key="item.question" class="faq-row gap-row"><div class="gap-signal"><span></span><strong>{{item.confidence}}</strong><small>置信度</small></div><div class="faq-body"><div class="faq-meta"><span>最近提问 {{item.last}}</span><span>出现 {{item.count}} 次</span></div><h3>{{item.question}}</h3><p>当前检索结果不足，建议补充制度或 FAQ 内容。</p></div><button class="primary-action" @click="createTask(item)">建补充任务</button></div></div>
    </article>
    <div v-if="editItem" class="overlay" @click.self="editItem=null"><div class="modal card faq-editor"><div class="drawer-head"><div><b>采纳并编辑 FAQ</b><small>保存后进入已发布 FAQ，并按开关控制问答缓存</small></div><button class="icon-button" @click="editItem=null">×</button></div><label>标准问题<input v-model="editDraft.question"></label><label>参考答案<textarea v-model="editDraft.answer" rows="6"></textarea></label><div class="drawer-foot"><button class="secondary" @click="editItem=null">取消</button><button @click="saveEdit">保存并发布</button></div></div></div>
  </section>
</template>
