<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'

const bases = ref([]), selected = ref(null), docs = ref([]), jobs = ref([])
const drawerOpen = ref(false), permissionOpen = ref(false), isDragging = ref(false), files = ref([])
const error = ref(''), notice = ref('')
const currentDoc = ref(null)
const permission = ref({ global: false, departments: ['研发部'], roles: ['知识管理员'], users: [] })
let timer
const stageLabel = { queued: '排队中', validating: '校验文件', parsing: '解析中', analyzing: '内容分析', chunking: '切片中', embedding: '向量化中', indexing: '写入 Milvus', publishing: '发布版本', published: '已完成', failed: '失败' }
const errorLabel = { HTTPStatusError: '向量服务拒绝了请求', HTTPError: '模型服务请求失败', MinerUParseError: 'MinerU 解析失败' }
const ledger = computed(() => docs.value)
const selectedName = computed(() => selected.value?.name || '请选择知识库')
const terminalStage = stage => ['published', 'failed'].includes(stage)
const jobProgress = job => job.stage === 'published' ? 100 : job.total_units ? Math.min(99, Math.round(job.completed_units / job.total_units * 100)) : 0
async function loadSelected() {
  if (!selected.value) return
  const [rows, imports] = await Promise.all([
    api(`/api/knowledge-bases/${selected.value.id}/documents`),
    api(`/api/knowledge-bases/imports?knowledge_base_id=${encodeURIComponent(selected.value.id)}`),
  ])
  docs.value = rows.map(x=>({
    id:x.id,title:x.title,
    format:(x.source_filename?.split('.').pop() || 'DOC').toUpperCase(),
    category:'未分类',acl:x.acl?.length?`${x.acl.length} 条策略`:'未配置',
    updated:x.updated_at ? new Date(x.updated_at).toLocaleString('zh-CN',{hour12:false}) : '-',
    enabled:x.enabled,retrievable:x.retrievable,importStage:x.import_stage,errorCode:x.error_code,
  }))
  jobs.value = imports.map(x => ({ ...x, progress: jobProgress(x) }))
  pollJobs()
}
async function load() { try { bases.value = await api('/api/knowledge-bases'); selected.value ||= bases.value[0]; await loadSelected(); error.value = '' } catch (e) { error.value = e.message } }
function chooseFiles(list) { files.value = [...files.value, ...Array.from(list || [])].filter((f, i, all) => all.findIndex(x => x.name === f.name && x.size === f.size) === i) }
function removeFile(i) { files.value.splice(i, 1) }
function openImport() { files.value = []; drawerOpen.value = true }
async function startImport() {
  if (!selected.value || !files.value.length) return
  for (const file of files.value) {
    const body = new FormData(); body.append('file', file)
    try { const r = await api(`/api/knowledge-bases/${selected.value.id}/documents`, { method: 'POST', body }); jobs.value.unshift({ id: r.job_id, title: file.name, stage: r.stage || 'queued', completed_units: 0, total_units: 0, progress: 8 }) }
    catch (e) { error.value = `${file.name}：${e.message}` }
  }
  drawerOpen.value = false; files.value = []; notice.value = '文件已提交，解析与向量化任务正在后台执行。'; setTimeout(() => { notice.value = '' }, 3000); pollJobs()
}
async function pollJobs() {
  clearTimeout(timer)
  let completed = false
  for (const job of jobs.value.filter(x => !terminalStage(x.stage))) {
    try { const latest = await api(`/api/knowledge-bases/imports/${job.id}`); Object.assign(job, latest); job.progress = jobProgress(latest); if (latest.stage === 'published') completed = true; if (latest.stage === 'failed') error.value = `${job.title} 导入失败：${latest.error_code || '未知错误'}` } catch (e) { error.value = `读取导入进度失败：${e.message}` }
  }
  if (completed) await loadSelected()
  else if (jobs.value.some(x => !terminalStage(x.stage))) timer = setTimeout(pollJobs, 1200)
}
function formatSize(size) { return size > 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(size / 1024))} KB` }
function documentState(doc) {
  if (!doc.enabled) return { label: '已停用', tone: 'off', detail: '' }
  if (doc.retrievable) return { label: '可检索', tone: 'on', detail: '' }
  if (doc.importStage === 'failed') return { label: '导入失败', tone: 'failed', detail: errorLabel[doc.errorCode] || doc.errorCode || '处理失败' }
  return { label: stageLabel[doc.importStage] || '处理中', tone: 'processing', detail: '完成后才能在 AI 问答中检索' }
}
async function savePermission() { try { if(currentDoc.value && selected.value){ await api(`/api/knowledge-bases/${selected.value.id}/documents/${currentDoc.value.id}/acl`,{method:'PUT',body:JSON.stringify({global_public:permission.value.global,departments:permission.value.departments,roles:permission.value.roles,users:permission.value.users})}) } permissionOpen.value = false; notice.value = '权限标签已保存，将在下一次索引任务中生效。' } catch(e){ error.value=e.message } setTimeout(() => { notice.value = '' }, 2800) }
function openPermission(doc=null){ currentDoc.value=doc; permissionOpen.value=true }
watch(selected, (value, oldValue) => { if (value?.id && oldValue?.id && value.id !== oldValue.id) loadSelected().catch(e => { error.value = e.message }) })
onMounted(load); onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <section class="knowledge-page">
    <div class="title-row"><div><div class="eyebrow">KNOWLEDGE GOVERNANCE</div><h1>知识维护与导入中心</h1><p>维护知识单元台账、导入任务与四维数据权限。</p></div><div class="title-actions"><select v-model="selected" class="range-select"><option v-for="base in bases" :key="base.id" :value="base">{{base.name}}</option></select><button @click="openImport">＋导入文档</button></div></div>
    <p v-if="notice" class="notice">{{notice}}</p><p v-if="error" class="error">{{error}}</p>
    <div class="sub-toolbar"><div><b>{{selectedName}}</b><small> · {{ledger.length}} 个知识单元</small></div><div class="toolbar-meta"><span class="status-dot"></span>权限策略：部门覆盖下级</div></div>
    <article class="card settings-panel ledger-panel"><div class="panel-heading"><div><b>知识单元台账</b><small>只有标记“可检索”的文档才会进入 AI 问答</small></div><button class="secondary" @click="openPermission()">批量设置权限</button></div><div class="table-wrap"><table><thead><tr><th>编号</th><th>标题</th><th>格式</th><th>所属分类</th><th>权限标签</th><th>更新时间</th><th>检索状态</th><th></th></tr></thead><tbody><tr v-for="doc in ledger" :key="doc.id"><td><span class="mono">{{doc.id}}</span></td><td><div class="doc-title"><span class="doc-mark">{{doc.format.slice(0,1)}}</span><b>{{doc.title}}</b></div></td><td>{{doc.format}}</td><td><span class="tag neutral">{{doc.category}}</span></td><td><span class="tag acl">{{doc.acl}}</span></td><td>{{doc.updated}}</td><td><span class="state" :class="documentState(doc).tone" :title="documentState(doc).detail"><i></i>{{documentState(doc).label}}</span><small v-if="documentState(doc).detail" class="state-detail">{{documentState(doc).detail}}</small></td><td><button class="text-button" @click="openPermission(doc)">权限</button></td></tr></tbody></table></div></article>
    <article v-if="jobs.length" class="card import-jobs"><div class="panel-heading"><div><b>导入任务进度</b><small>任务会自动刷新，完成后立即进入 AI 检索范围</small></div><span class="tag neutral">{{jobs.filter(j => j.stage==='published').length}} / {{jobs.length}} 已完成</span></div><div v-for="job in jobs" :key="job.id" class="job-row" :class="{failed:job.stage==='failed'}"><div class="job-icon">↥</div><div class="job-main"><div><b>{{job.title}}</b><span class="stage-label">{{stageLabel[job.stage] || job.stage}}{{job.error_code ? ` · ${errorLabel[job.error_code] || job.error_code}` : ''}}</span></div><div class="progress"><i :style="{width: `${job.progress || 0}%`}"></i></div></div><strong>{{job.progress || 0}}%</strong></div></article>
    <div v-if="drawerOpen" class="overlay" @click.self="drawerOpen=false"><aside class="drawer"><div class="drawer-head"><div><b>导入文档</b><small>支持 PDF、Word（含 .doc）、Markdown、TXT</small></div><button class="icon-button" @click="drawerOpen=false">×</button></div><div class="dropzone" :class="{dragging:isDragging}" @dragover.prevent="isDragging=true" @dragleave.prevent="isDragging=false" @drop.prevent="isDragging=false; chooseFiles($event.dataTransfer.files)"><span class="upload-cloud">⇧</span><b>拖拽文件到此处</b><small>或 <label class="text-link">点击选择<input type="file" multiple accept=".pdf,.md,.txt,.doc,.docx" @change="chooseFiles($event.target.files)"></label>，单个文件不超过 50 MB</small></div><div class="file-list"><div v-for="(file, i) in files" :key="file.name+file.size" class="file-row"><span class="doc-mark">{{file.name.split('.').pop().toUpperCase().slice(0,1)}}</span><div><b>{{file.name}}</b><small>{{formatSize(file.size)}}</small></div><button class="icon-button" @click="removeFile(i)">×</button></div><div v-if="!files.length" class="empty compact-empty">尚未选择文件</div></div><div class="drawer-foot"><button class="secondary" @click="drawerOpen=false">取消</button><button :disabled="!files.length || !selected" @click="startImport">开始导入（{{files.length}}）</button></div></aside></div>
    <div v-if="permissionOpen" class="overlay" @click.self="permissionOpen=false"><div class="modal card permission-modal"><div class="drawer-head"><div><b>数据权限分配</b><small>四维权限同时满足时可读取正文</small></div><button class="icon-button" @click="permissionOpen=false">×</button></div><label class="check-line"><input v-model="permission.global" type="checkbox"><span><b>全局公开</b><small>租户内所有已启用用户可检索</small></span></label><div class="permission-grid"><label><b>部门</b><small>部门权限覆盖下级</small><select v-model="permission.departments" multiple><option>研发部</option><option>运营部</option><option>财务部</option><option>人事部</option></select></label><label><b>角色</b><small>按功能角色限制访问</small><select v-model="permission.roles" multiple><option>知识管理员</option><option>审计员</option><option>业务用户</option></select></label><label><b>人员</b><small>用户只能归属一个部门</small><select v-model="permission.users" multiple><option>林晓（研发部）</option><option>周宁（运营部）</option><option>赵敏（财务部）</option></select></label></div><div class="drawer-foot"><button class="secondary" @click="permissionOpen=false">取消</button><button @click="savePermission">保存权限</button></div></div></div>
  </section>
</template>
