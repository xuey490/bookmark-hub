const STORAGE_KEYS = ['serverUrl', 'token', 'enabled', 'buttonPos']

async function readConfig() {
  const stored = await chrome.storage.local.get(STORAGE_KEYS)
  return {
    serverUrl: stored.serverUrl || '',
    token: stored.token || '',
    enabled: stored.enabled !== false,
    buttonPos: stored.buttonPos || null,
  }
}

function normalizeServer(raw) {
  let value = String(raw || '').trim()
  if (!value) return ''
  if (!/^https?:\/\//i.test(value)) {
    const host = value.split('/')[0].split(':')[0]
    const local =
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host === '::1' ||
      /^10\./.test(host) ||
      /^192\.168\./.test(host) ||
      /^172\.(1[6-9]|2\d|3[01])\./.test(host)
    value = (local ? 'http://' : 'https://') + value
  }
  const parsed = new URL(value)
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('服务器地址必须以 http/https 开头')
  }
  return parsed.href.replace(/\/+$/, '')
}

async function apiFetch(path, options = {}) {
  const config = await readConfig()
  if (!config.serverUrl || !config.token) {
    throw new Error('请先在插件设置中配置服务器地址和 Token')
  }

  const response = await fetch(`${config.serverUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.token}`,
      ...(options.headers || {}),
    },
  })

  const text = await response.text()
  let body = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }

  if (!response.ok) {
    const error = new Error(body && body.message ? body.message : `HTTP ${response.status}`)
    error.status = response.status
    error.data = body ? body.data : null
    throw error
  }

  return body && Object.prototype.hasOwnProperty.call(body, 'data') ? body.data : body
}

async function handleMessage(message) {
  switch (message.type) {
    case 'GET_CONFIG':
      return { ok: true, data: await readConfig() }

    case 'SAVE_CONFIG': {
      const serverUrl = normalizeServer(message.serverUrl)
      const token = String(message.token || '').trim()
      if (!serverUrl || !token) {
        throw new Error('服务器地址和 Token 都不能为空')
      }
      const enabled = message.enabled !== false
      await chrome.storage.local.set({ serverUrl, token, enabled })
      return { ok: true, data: { serverUrl, token, enabled } }
    }

    case 'TEST_CONNECTION': {
      const serverUrl = normalizeServer(message.serverUrl)
      const token = String(message.token || '').trim()
      if (!serverUrl || !token) throw new Error('请填写服务器地址和 Token')
      const response = await fetch(
        `${serverUrl}/api/bookmarks?page=1&page_size=1`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
      const body = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(body && body.message ? body.message : `HTTP ${response.status}`)
      }
      return { ok: true, data: body ? body.data : null }
    }

    case 'GET_CATEGORIES':
      return { ok: true, data: await apiFetch('/api/categories') }

    case 'GET_TAGS':
      return { ok: true, data: await apiFetch('/api/tags') }

    case 'SAVE_BOOKMARK':
      return {
        ok: true,
        data: await apiFetch('/api/bookmarks', {
          method: 'POST',
          body: JSON.stringify(message.payload),
        }),
      }

    case 'GET_RECENT': {
      const limit = Math.min(Math.max(Number(message.limit) || 12, 1), 50)
      return {
        ok: true,
        data: await apiFetch(
          `/api/bookmarks?page=1&page_size=${limit}&sort=created_at_desc`,
        ),
      }
    }

    case 'CHECK_BOOKMARK':
      return {
        ok: true,
        data: await apiFetch(`/api/bookmarks/${message.id}/check`, {
          method: 'POST',
        }),
      }

    case 'VISIT_BOOKMARK':
      return {
        ok: true,
        data: await apiFetch(`/api/bookmarks/${message.id}/visit`, {
          method: 'POST',
        }),
      }

    default:
      throw new Error('unknown message type')
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message)
    .then((result) => sendResponse(result))
    .catch((error) =>
      sendResponse({
        ok: false,
        error: error.message || '请求失败',
        status: error.status || null,
        data: error.data || null,
      }),
    )
  return true
})
