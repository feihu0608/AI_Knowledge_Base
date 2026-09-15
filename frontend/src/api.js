const tokenKey = 'knowledge_access_token'

export const session = {
  get token() { return sessionStorage.getItem(tokenKey) },
  set token(value) { value ? sessionStorage.setItem(tokenKey, value) : sessionStorage.removeItem(tokenKey) },
}

function errorMessage(detail) {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(item => errorMessage(item)).filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message.trim()) return detail.message
    if (typeof detail.msg === 'string' && detail.msg.trim()) return detail.msg
    if (typeof detail.detail === 'string' && detail.detail.trim()) return detail.detail
    const location = Array.isArray(detail.loc) ? detail.loc.filter(Boolean).join('.') : ''
    if (location && typeof detail.type === 'string') return `${location}: ${detail.type}`
  }
  return ''
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (session.token) headers.set('Authorization', `Bearer ${session.token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  let response
  try {
    response = await fetch(path, {...options, headers})
  } catch (exception) {
    throw new Error('网络请求失败，请检查服务是否启动')
  }
  const body = await response.json().catch(() => ({}))
  if (response.status === 401 && session.token) {
    session.token = null
    if (window.location.pathname !== '/') window.location.assign('/')
  }
  if (!response.ok) {
    const message = errorMessage(body.detail) || errorMessage(body.error) || errorMessage(body.message)
    throw new Error(message || `请求失败（${response.status}）`)
  }
  return body
}
