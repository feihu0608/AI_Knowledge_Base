import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Knowledge from './views/Knowledge.vue'
import Chat from './views/Chat.vue'
import Dashboard from './views/Dashboard.vue'
import Operations from './views/Operations.vue'
import Organization from './views/Organization.vue'
import { session } from './api'
import './style.css'

const router = createRouter({history: createWebHistory(), routes: [
  {path: '/login', component: Login},
  {path: '/', redirect: '/knowledge'},
  {path: '/dashboard', component: Dashboard, meta: {auth: true}},
  {path: '/knowledge', component: Knowledge, meta: {auth: true}},
  {path: '/chat', component: Chat, meta: {auth: true}},
  {path: '/operations', component: Operations, meta: {auth: true}},
  {path: '/organization', component: Organization, meta: {auth: true}},
]})
router.beforeEach(to => to.meta.auth && !session.token ? '/login' : true)
createApp(App).use(router).mount('#app')
