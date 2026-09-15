const tokenKey = 'knowledge_access_token'

export const session = {
  get token() { return sessionStorage.getItem(tokenKey) },
  set token(value) { value ? sessionStorage.setItem(tokenKey, value) : sessionStorage.removeItem(tokenKey) },
}

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  if (session.token) headers.set('Authorization', `Bearer ${session.token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, {...options, headers})
  const body = await response.json().catch(() => ({}))
  if (response.status === 401 && session.token) {
    session.token = null
    if (window.location.pathname !== '/') window.location.assign('/')
  }
  if (!response.ok) throw new Error(body.detail || `请求失败（${response.status}）`)
  return body
}
