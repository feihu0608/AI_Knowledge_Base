<script setup>
import { computed, ref } from 'vue'

const activeTab = ref('recommend')
const notice = ref('')
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
function publish(item){ item.status='已采纳'; notice.value=`已采纳「${item.question}」，正在生成标准 FAQ。`; setTimeout(()=>notice.value='', 2600) }
function reject(item){ recommendations.value=recommendations.value.filter(row=>row.id!==item.id); notice.value='已驳回该推荐问题'; setTimeout(()=>notice.value='', 2200) }
function createTask(item){ gaps.value=gaps.value.filter(row=>row.question!==item.question); notice.value=`已创建知识补充任务：${item.question}`; setTimeout(()=>notice.value='', 2600) }
</script>

<template>
  <section class="operations-page">
    <div class="title-row"><div><div class="eyebrow">KNOWLEDGE OPERATIONS</div><h1>知识沉淀与运营</h1><p>把高频对话沉淀成标准答案，持续补齐知识缺口。</p></div><span class="pilot-tag">试点演示数据</span></div>
    <p v-if="notice" class="notice">{{notice}}</p>
    <div class="tab-bar card"><button :class="{active:activeTab==='recommend'}" @click="activeTab='recommend'">FAQ 挖掘与审核 <b>{{recommendations.length}}</b></button><button :class="{active:activeTab==='published'}" @click="activeTab='published'">已发布 FAQ <b>{{published.length}}</b></button><button :class="{active:activeTab==='gaps'}" @click="activeTab='gaps'">知识缺口 <b>{{gaps.length}}</b></button></div>

    <article class="card operations-panel"><div class="panel-heading"><div><b>{{tabLabel}}</b><small v-if="activeTab==='recommend'">基于历史对话聚类，按频次和相似度排序</small><small v-else-if="activeTab==='published'">标准问答对与缓存生效控制</small><small v-else>检索未命中或置信度偏低的问题</small></div><button v-if="activeTab==='published'" class="secondary">批量刷新缓存</button></div>
      <div v-if="activeTab==='recommend'" class="faq-list"><div v-for="item in recommendations" :key="item.id" class="faq-row"><div class="faq-count"><strong>{{item.count}}</strong><small>聚合频次</small></div><div class="faq-body"><div class="faq-meta"><span>{{item.id}}</span><span>{{item.time}}</span><span class="status pending">{{item.status}}</span></div><h3>{{item.question}}</h3><p>{{item.answer}}</p></div><div class="row-actions"><button class="secondary" @click="publish(item)">采纳编辑</button><button class="ghost small-button" @click="reject(item)">驳回</button></div></div></div>
      <div v-else-if="activeTab==='published'" class="faq-list"><div v-for="item in published" :key="item.id" class="faq-row published-row"><div class="doc-mark faq-mark">问</div><div class="faq-body"><div class="faq-meta"><span>{{item.id}}</span><span>更新于 {{item.updated}}</span></div><h3>{{item.question}}</h3><p>{{item.answer}}</p></div><label class="switch-label"><input v-model="item.enabled" type="checkbox"><i></i><span>{{item.enabled?'缓存已生效':'缓存已暂停'}}</span></label><button class="secondary">编辑</button></div></div>
      <div v-else class="faq-list"><div v-for="item in gaps" :key="item.question" class="faq-row gap-row"><div class="gap-signal"><span></span><strong>{{item.confidence}}</strong><small>置信度</small></div><div class="faq-body"><div class="faq-meta"><span>最近提问 {{item.last}}</span><span>出现 {{item.count}} 次</span></div><h3>{{item.question}}</h3><p>当前检索结果不足，建议补充制度或 FAQ 内容。</p></div><button class="primary-action" @click="createTask(item)">建补充任务</button></div></div>
    </article>
  </section>
</template>
