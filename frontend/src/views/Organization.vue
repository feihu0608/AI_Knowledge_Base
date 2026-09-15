<script setup>
import { ref } from 'vue'
const tab = ref('departments'); const saved = ref(false)
const departments = [
  {name:'总部', code:'HQ', children:[{name:'研发部', code:'RD', members:28},{name:'运营部', code:'OPS', members:16},{name:'财务部', code:'FIN', members:9}]},
]
const users = ref([{name:'林晓', username:'lin.xiao', dept:'研发部', role:'知识管理员', active:true},{name:'周宁', username:'zhou.ning', dept:'运营部', role:'业务用户', active:true},{name:'赵敏', username:'zhao.min', dept:'财务部', role:'审计员', active:false}])
const roles = [{name:'系统管理员', desc:'平台配置、组织和全量审计', permissions:['组织管理','知识管理','AI 问答','运营审核','系统配置']},{name:'知识管理员', desc:'维护授权范围内知识与导入任务', permissions:['知识管理','导入审核','FAQ 审核']},{name:'业务用户', desc:'访问已授权知识并进行问答', permissions:['AI 问答','知识检索']}]
function save(){saved.value=true;setTimeout(()=>saved.value=false,2000)}
</script>

<template>
  <section class="organization-page">
    <div class="title-row"><div><div class="eyebrow">ORGANIZATION & SETTINGS</div><h1>组织架构与系统配置</h1><p>管理部门范围、角色权限和底层模型接口。</p></div><button @click="save">保存配置</button></div>
    <p v-if="saved" class="notice">配置已保存（当前为试点环境）</p>
    <div class="tab-bar card org-tabs"><button :class="{active:tab==='departments'}" @click="tab='departments'">部门架构</button><button :class="{active:tab==='users'}" @click="tab='users'">用户账号</button><button :class="{active:tab==='roles'}" @click="tab='roles'">角色权限</button><button :class="{active:tab==='models'}" @click="tab='models'">模型接口</button></div>
    <article v-if="tab==='departments'" class="card settings-panel"><div class="panel-heading"><div><b>部门树形结构</b><small>部门权限默认覆盖下级，用户只能归属一个部门</small></div><button class="secondary">+ 新增部门</button></div><div class="tree"><div v-for="root in departments" :key="root.code" class="tree-root"><span class="tree-caret">⌄</span><span class="folder">▰</span><b>{{root.name}}</b><small>{{root.code}}</small><div v-for="child in root.children" :key="child.code" class="tree-child"><span class="tree-line"></span><span class="folder light">▰</span><b>{{child.name}}</b><small>{{child.code}} · {{child.members}} 人</small><button class="icon-button">⋮</button></div></div></div></article>
    <article v-else-if="tab==='users'" class="card settings-panel"><div class="panel-heading"><div><b>用户账号状态</b><small>支持停用、转移部门和调整角色</small></div><button class="secondary">+ 邀请用户</button></div><div class="table-wrap"><table><thead><tr><th>用户</th><th>所属部门</th><th>角色</th><th>账号状态</th><th></th></tr></thead><tbody><tr v-for="user in users" :key="user.username"><td><div class="user-cell"><span class="avatar">{{user.name.slice(0,1)}}</span><div><b>{{user.name}}</b><small>{{user.username}}</small></div></div></td><td>{{user.dept}}</td><td><span class="role-chip">{{user.role}}</span></td><td><label class="switch-label compact"><input v-model="user.active" type="checkbox"><i></i><span>{{user.active?'正常':'已停用'}}</span></label></td><td><button class="text-button">编辑</button></td></tr></tbody></table></div></article>
    <article v-else-if="tab==='roles'" class="card settings-panel"><div class="panel-heading"><div><b>角色功能操作权限树</b><small>管理员可将权限赋予角色，权限变更会立即记录审计日志</small></div><button class="secondary">+ 新建角色</button></div><div class="role-list"><div v-for="role in roles" :key="role.name" class="role-card"><div class="role-card-head"><div><b>{{role.name}}</b><small>{{role.desc}}</small></div><button class="text-button">编辑权限</button></div><div class="permission-chips"><span v-for="permission in role.permissions" :key="permission" class="permission-chip"><i>✓</i>{{permission}}</span></div></div></div></article>
    <article v-else class="card settings-panel"><div class="panel-heading"><div><b>底层模型接口配置</b><small>密钥仅存储在服务器环境变量，前端不展示</small></div><span class="connected"><i></i>连接正常</span></div><div class="model-grid"><label>Chat 模型<input value="deepseek-ai/DeepSeek-V3" readonly><small>硅基流动 · 用于问答与文档分析</small></label><label>Embedding 模型<input value="BAAI/bge-large-zh-v1.5" readonly><small>向量维度 1024 · Milvus</small></label><label>Rerank 模型<input value="BAAI/bge-reranker-v2-m3" readonly><small>用于候选证据重排</small></label><label>MCP 服务<input value="百炼 WebSearch MCP" readonly><small>三路检索中的联网搜索通道</small></label></div></article>
  </section>
</template>
