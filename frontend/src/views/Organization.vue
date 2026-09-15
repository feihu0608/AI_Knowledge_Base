<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { api } from '../api'

const tab = ref('departments')
const saved = ref(false)
const notice = ref('')
const error = ref('')
const loading = ref(false)
const busy = ref(false)
const departmentModal = ref(false)
const inviteModal = ref(false)
const roleModal = ref(false)
const roleEditor = ref(null)
const editingUser = ref(null)
const departmentDraft = ref({ name: '', parent_id: '' })
const inviteDraft = ref({ username: '', password: '', department_id: '', role_id: '' })
const roleDraft = ref({ name: '', code: '' })
const departments = ref([])
const users = ref([])
const roles = ref([])
const permissionOptions = ['organization.read','organization.admin','knowledge.read','knowledge.write','knowledge.admin','chat.use','faq.review','audit.read']

const DepartmentNode = {
  props: { item: Object, level: Number },
  setup(props) {
    return () => h('div', { class: props.level === 0 ? 'tree-root' : 'tree-child' }, [
      h('span', { class: 'tree-caret' }, props.item.children?.length ? '⌄' : ''),
      h('span', { class: props.level === 0 ? 'folder' : 'folder light' }, '▰'),
      h('b', props.item.name),
      h('small', `${props.item.code}${props.level > 0 ? ` · ${props.item.members || 0} 人` : ''}`),
      ...(props.item.children || []).map(child => h(DepartmentNode, { key: child.id, item: child, level: props.level + 1 })),
    ])
  },
}

const flatDepartments = computed(() => {
  const result = []
  const visit = (items, depth = 0) => items.forEach(item => {
    result.push({ id: item.id, name: `${'　'.repeat(depth)}${item.name}` })
    visit(item.children || [], depth + 1)
  })
  visit(departments.value)
  return result
})

function emptyInviteDraft() {
  return {
    username: '',
    password: '',
    department_id: flatDepartments.value[0]?.id || '',
    role_id: roles.value[0]?.id || '',
  }
}

function showError(exception) {
  if (exception instanceof Error && exception.message) {
    error.value = exception.message
    return
  }
  if (exception && typeof exception === 'object') {
    error.value = exception.message || exception.detail || JSON.stringify(exception)
    return
  }
  error.value = String(exception || '操作失败')
}

function closeModals() {
  departmentModal.value = false
  inviteModal.value = false
  roleModal.value = false
  editingUser.value = null
}

async function load() {
  loading.value = true
  try {
    error.value = ''
    const [dept, user, role] = await Promise.all([
      api('/api/organization/departments'),
      api('/api/organization/users'),
      api('/api/organization/roles'),
    ])
    const byParent = new Map()
    dept.forEach(item => {
      const parent = item.parent_id || null
      if (!byParent.has(parent)) byParent.set(parent, [])
      byParent.get(parent).push(item)
    })
    const build = (parentId = null, visited = new Set()) => (byParent.get(parentId) || [])
      .filter(item => !visited.has(item.id))
      .map(item => {
        const nextVisited = new Set(visited).add(item.id)
        return {
          ...item,
          code: item.id ? item.id.slice(-2).toUpperCase() : '',
          members: user.filter(u => u.department_id === item.id).length,
          children: build(item.id, nextVisited),
        }
      })
    departments.value = build()
    users.value = user
    roles.value = role
  } catch (exception) {
    showError(exception)
  } finally {
    loading.value = false
  }
}

function openDepartment() {
  error.value = ''
  departmentDraft.value = { name: '', parent_id: '' }
  departmentModal.value = true
}

function openInvite() {
  error.value = ''
  editingUser.value = null
  inviteDraft.value = emptyInviteDraft()
  inviteModal.value = true
}

function openUserEditor(user) {
  error.value = ''
  editingUser.value = user
  inviteDraft.value = {
    username: user.username,
    password: '',
    department_id: user.department_id || flatDepartments.value[0]?.id || '',
    role_id: user.role_id || user.role_ids?.[0] || roles.value[0]?.id || '',
  }
  inviteModal.value = true
}

async function createDepartment() {
  const name = departmentDraft.value.name.trim()
  if (!name) {
    error.value = '部门名称不能为空'
    return
  }
  busy.value = true
  try {
    const result = await api('/api/organization/departments', {
      method: 'POST',
      body: JSON.stringify({ name, parent_id: departmentDraft.value.parent_id || null }),
    })
    notice.value = `部门「${result.name}」已创建`
    closeModals()
    await load()
  } catch (exception) {
    showError(exception)
  } finally {
    busy.value = false
  }
}

async function inviteUser() {
  const username = inviteDraft.value.username.trim()
  const departmentId = inviteDraft.value.department_id
  const roleId = inviteDraft.value.role_id
  if (username.length < 2) {
    error.value = '账号至少需要 2 个字符'
    return
  }
  if (!departmentId) {
    error.value = '请选择所属部门'
    return
  }
  if (!roleId) {
    error.value = '请选择角色'
    return
  }
  if (!editingUser.value && inviteDraft.value.password.length < 10) {
    error.value = '初始密码至少需要 10 个字符'
    return
  }
  busy.value = true
  try {
    if (editingUser.value) {
      await api(`/api/organization/users/${editingUser.value.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ department_id: departmentId, role_id: roleId }),
      })
      notice.value = `账号 ${username} 已更新`
    } else {
      await api('/api/organization/users', {
        method: 'POST',
        body: JSON.stringify({ username, password: inviteDraft.value.password, department_id: departmentId, role_id: roleId }),
      })
      notice.value = '用户已创建并绑定到单一部门'
    }
    closeModals()
    await load()
  } catch (exception) {
    showError(exception)
  } finally {
    busy.value = false
  }
}

async function createRole() {
  const name = roleDraft.value.name.trim()
  const code = roleDraft.value.code.trim()
  if (!name || !code) {
    error.value = '角色名称和编码不能为空'
    return
  }
  busy.value = true
  try {
    await api('/api/organization/roles', { method: 'POST', body: JSON.stringify({ name, code }) })
    notice.value = '角色已创建'
    closeModals()
    roleDraft.value = { name: '', code: '' }
    await load()
  } catch (exception) {
    showError(exception)
  } finally {
    busy.value = false
  }
}

async function toggleUser(user) {
  const nextActive = user.active
  try {
    await api(`/api/organization/users/${user.id}`, { method: 'PATCH', body: JSON.stringify({ active: nextActive }) })
    notice.value = `账号 ${user.username} 状态已更新`
  } catch (exception) {
    user.active = !nextActive
    showError(exception)
  }
}

async function saveRole(role) {
  try {
    await api(`/api/organization/roles/${role.id}/permissions`, { method: 'PUT', body: JSON.stringify({ permissions: role.permissions }) })
    roleEditor.value = null
    notice.value = `${role.name} 权限已保存`
  } catch (exception) {
    showError(exception)
  }
}

async function deleteRole(role) {
  if (!window.confirm(`确定删除角色「${role.name}」吗？`)) return
  try {
    await api(`/api/organization/roles/${role.id}`, { method: 'DELETE' })
    if (roleEditor.value === role) roleEditor.value = null
    notice.value = `角色「${role.name}」已删除`
    await load()
  } catch (exception) {
    showError(exception)
  }
}

function save() {
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

onMounted(load)
</script>

<template>
  <section class="organization-page"><div class="title-row"><div><div class="eyebrow">ORGANIZATION & SETTINGS</div><h1>组织架构与系统配置</h1><p>管理部门范围、角色权限和底层模型接口。</p></div><button @click="save">保存配置</button></div><p v-if="saved" class="notice">配置已保存</p><p v-if="notice" class="notice">{{notice}}</p><p v-if="error" class="error">{{error}}</p>
    <div class="tab-bar card org-tabs"><button :class="{active:tab==='departments'}" @click="tab='departments'">部门架构</button><button :class="{active:tab==='users'}" @click="tab='users'">用户账号</button><button :class="{active:tab==='roles'}" @click="tab='roles'">角色权限</button><button :class="{active:tab==='models'}" @click="tab='models'">模型接口</button></div>
    <article v-if="tab==='departments'" class="card settings-panel"><div class="panel-heading"><div><b>部门树形结构</b><small>{{loading ? '正在同步组织数据…' : '部门权限默认覆盖下级，用户只能归属一个部门'}}</small></div><button class="secondary" @click="openDepartment">+ 新增部门</button></div><div class="tree"><DepartmentNode v-for="root in departments" :key="root.id || root.code" :item="root" :level="0" /></div><div v-if="!departments.length && !loading" class="empty compact-empty">暂无部门数据</div></article>
    <article v-else-if="tab==='users'" class="card settings-panel"><div class="panel-heading"><div><b>用户账号状态</b><small>支持停用、转移部门和调整角色</small></div><button class="secondary" @click="openInvite">+ 邀请用户</button></div><div class="table-wrap"><table><thead><tr><th>用户</th><th>所属部门</th><th>角色</th><th>账号状态</th><th></th></tr></thead><tbody><tr v-for="user in users" :key="user.id || user.username"><td><div class="user-cell"><span class="avatar">{{user.username.slice(0,1).toUpperCase()}}</span><div><b>{{user.username}}</b><small>{{user.id}}</small></div></div></td><td>{{user.department || '未分配'}}</td><td><span class="role-chip">{{user.role}}</span></td><td><label class="switch-label compact"><input v-model="user.active" type="checkbox" @change="toggleUser(user)"><i></i><span>{{user.active?'正常':'已停用'}}</span></label></td><td><button class="text-button" @click="openUserEditor(user)">编辑</button></td></tr></tbody></table><div v-if="!users.length && !loading" class="empty compact-empty">暂无用户数据</div></div></article>
    <article v-else-if="tab==='roles'" class="card settings-panel"><div class="panel-heading"><div><b>角色功能操作权限树</b><small>管理员可将权限赋予角色，权限变更会立即记录审计日志</small></div><button class="secondary" @click="roleModal=true">+ 新建角色</button></div><div class="role-list"><div v-for="role in roles" :key="role.id || role.name" class="role-card"><div class="role-card-head"><div><b>{{role.name}}</b><small>{{role.code}}</small></div><div><button class="text-button" @click="roleEditor=role">编辑权限</button><button class="text-button danger-text" @click="deleteRole(role)">删除</button></div></div><div v-if="roleEditor===role" class="permission-editor"><label v-for="permission in permissionOptions" :key="permission"><input v-model="role.permissions" type="checkbox" :value="permission">{{permission}}</label><button class="secondary" @click="saveRole(role)">保存权限</button></div><div v-else class="permission-chips"><span v-for="permission in role.permissions" :key="permission" class="permission-chip"><i>✓</i>{{permission}}</span></div></div></div></article>
    <article v-else class="card settings-panel"><div class="panel-heading"><div><b>底层模型接口配置</b><small>密钥仅存储在服务器环境变量，前端不展示</small></div><span class="connected"><i></i>连接正常</span></div><div class="model-grid"><label>Chat 模型<input value="deepseek-ai/DeepSeek-V3" readonly><small>硅基流动 · 用于问答与文档分析</small></label><label>Embedding 模型<input value="BAAI/bge-large-zh-v1.5" readonly><small>向量维度 1024 · Milvus</small></label><label>Rerank 模型<input value="BAAI/bge-reranker-v2-m3" readonly><small>用于候选证据重排</small></label><label>MCP 服务<input value="百炼 WebSearch MCP" readonly><small>三路检索中的联网搜索通道</small></label></div></article>
    <div v-if="departmentModal || inviteModal || roleModal" class="overlay" @click.self="closeModals"><div class="modal card faq-editor"><div class="drawer-head"><b>{{departmentModal ? '新增部门' : inviteModal ? (editingUser ? '编辑用户' : '邀请用户') : '新建角色'}}</b><button class="icon-button" @click="closeModals">×</button></div><div v-if="departmentModal"><label>部门名称<input v-model="departmentDraft.name" maxlength="120" @keyup.enter="createDepartment"></label><label>上级部门<select v-model="departmentDraft.parent_id"><option value="">无（顶级部门）</option><option v-for="item in flatDepartments" :key="item.id" :value="item.id">{{item.name}}</option></select></label><button :disabled="busy" @click="createDepartment">{{busy ? '正在创建…' : '创建部门'}}</button></div><div v-else-if="inviteModal"><label>账号<input v-model="inviteDraft.username" :disabled="!!editingUser" autocomplete="username"></label><label v-if="!editingUser">初始密码<input v-model="inviteDraft.password" type="password" minlength="10" autocomplete="new-password"><small>至少 10 个字符</small></label><label>所属部门<select v-model="inviteDraft.department_id" :disabled="!flatDepartments.length"><option value="" disabled>请选择部门</option><option v-for="item in flatDepartments" :key="item.id" :value="item.id">{{item.name}}</option></select></label><label>角色<select v-model="inviteDraft.role_id" :disabled="!roles.length"><option value="" disabled>请选择角色</option><option v-for="role in roles" :key="role.id" :value="role.id">{{role.name}}</option></select></label><p v-if="!flatDepartments.length || !roles.length" class="error">请先创建部门和角色，再添加用户。</p><button :disabled="busy || !flatDepartments.length || !roles.length" @click="inviteUser">{{busy ? '正在保存…' : editingUser ? '保存用户' : '创建用户'}}</button></div><div v-else><label>角色名称<input v-model="roleDraft.name" maxlength="120"></label><label>角色编码<input v-model="roleDraft.code" maxlength="80"></label><button :disabled="busy" @click="createRole">{{busy ? '正在创建…' : '创建角色'}}</button></div></div></div>
  </section>
</template>
