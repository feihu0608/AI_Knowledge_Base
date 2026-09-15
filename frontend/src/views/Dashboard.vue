<script setup>
import { computed, ref } from 'vue'

const range = ref('近 7 天')
const bars = [42, 55, 48, 72, 61, 84, 68]
const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const topics = [
  { name: '差旅报销标准', count: 186, delta: '+18%' },
  { name: 'VPN 与远程办公', count: 142, delta: '+11%' },
  { name: '采购审批流程', count: 97, delta: '+7%' },
  { name: '员工入职办理', count: 83, delta: '+4%' },
]
const citations = [
  { title: '员工差旅管理制度', refs: 238, type: '制度' },
  { title: 'IT 服务台常见问题', refs: 176, type: 'FAQ' },
  { title: '采购与合同审批手册', refs: 119, type: '手册' },
]
const maxBar = computed(() => Math.max(...bars))
</script>

<template>
  <section class="dashboard-page">
    <div class="title-row dashboard-heading">
      <div><div class="eyebrow">OPERATIONS OVERVIEW</div><h1>运营看板</h1><p>掌握知识资产、问答质量与平台运行状态。</p></div>
      <select v-model="range" class="range-select"><option>近 7 天</option><option>近 30 天</option><option>本季度</option></select>
    </div>

    <div class="metric-grid">
      <article class="metric-card card"><span class="metric-icon mint">↗</span><div><small>平台访问量（PV）</small><strong>12,846</strong><em>较上周期 +12.6%</em></div></article>
      <article class="metric-card card"><span class="metric-icon blue">◉</span><div><small>独立用户（UV）</small><strong>1,284</strong><em>较上周期 +8.4%</em></div></article>
      <article class="metric-card card"><span class="metric-icon orange">▤</span><div><small>知识单元总数</small><strong>2,486</strong><em>本周新增 36</em></div></article>
      <article class="metric-card card"><span class="metric-icon purple">⌁</span><div><small>平均响应时长</small><strong>2.8s</strong><em>较上周期 -0.4s</em></div></article>
    </div>

    <div class="dashboard-grid">
      <article class="card chart-card traffic-card"><div class="card-heading"><div><b>访问量趋势</b><small>PV / UV 统计</small></div><span class="legend"><i class="legend-pv"></i>PV <i class="legend-uv"></i>UV</span></div><div class="bar-chart"><div v-for="(bar, i) in bars" :key="days[i]" class="bar-column"><div class="bar-pair"><i class="bar pv" :style="{height: `${bar / maxBar * 150}px`}"></i><i class="bar uv" :style="{height: `${bar / maxBar * 105}px`}"></i></div><small>{{days[i]}}</small></div></div></article>
      <article class="card chart-card token-card"><div class="card-heading"><div><b>Token 消耗趋势</b><small>模型调用成本监控</small></div><strong class="chart-value">1.24M <small>tokens</small></strong></div><div class="sparkline"><span v-for="(bar, i) in bars" :key="i" :style="{height: `${bar}%`}"></span></div><div class="chart-foot"><span>输入 824K</span><span>输出 416K</span><span class="positive">较上周 -6.8%</span></div></article>
    </div>

    <div class="dashboard-grid lower-grid">
      <article class="card list-card"><div class="card-heading"><div><b>高频问题 TOP 榜</b><small>用户真实提问聚合</small></div><router-link to="/operations" class="text-link">查看全部 →</router-link></div><div v-for="(item, i) in topics" :key="item.name" class="rank-row"><span class="rank" :class="{top:i<3}">{{String(i+1).padStart(2,'0')}}</span><div class="rank-main"><b>{{item.name}}</b><div class="rank-track"><i :style="{width: `${item.count / topics[0].count * 100}%`}"></i></div></div><strong>{{item.count}}</strong><em>{{item.delta}}</em></div></article>
      <article class="card list-card"><div class="card-heading"><div><b>高频引用知识 TOP 榜</b><small>被答案引用次数</small></div><router-link to="/knowledge" class="text-link">管理知识 →</router-link></div><div v-for="(item, i) in citations" :key="item.title" class="citation-row"><span class="doc-mark">{{item.type.slice(0,1)}}</span><div><b>{{item.title}}</b><small>最近 24 小时持续被引用</small></div><strong>{{item.refs}}<small>次</small></strong></div></article>
    </div>
  </section>
</template>
