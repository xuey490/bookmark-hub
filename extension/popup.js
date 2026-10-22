const serverInput = document.getElementById('serverUrl')
const tokenInput = document.getElementById('token')
const enabledInput = document.getElementById('enabled')
const statusElement = document.getElementById('status')
const toggleTokenButton = document.getElementById('toggleToken')
const testButton = document.getElementById('testBtn')
const saveButton = document.getElementById('saveBtn')
const openH5Button = document.getElementById('openH5')

function send(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: chrome.runtime.lastError.message })
      } else {
        resolve(response || { ok: false, error: 'empty response' })
      }
    })
  })
}

function setStatus(text, type = '') {
  statusElement.textContent = text
  statusElement.className = 'status' + (type ? ' ' + type : '')
}

function setLoading(button, loading, label) {
  button.disabled = loading
  if (loading) {
    button.dataset.label = button.textContent
    button.textContent = label
  } else if (button.dataset.label) {
    button.textContent = button.dataset.label
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
  return new URL(value).href.replace(/\/+$/, '')
}

async function loadConfig() {
  const response = await send({ type: 'GET_CONFIG' })
  if (!response.ok) {
    setStatus('读取配置失败：' + response.error, 'error')
    return
  }
  const config = response.data
  serverInput.value = config.serverUrl || ''
  tokenInput.value = config.token || ''
  enabledInput.checked = config.enabled !== false
  if (config.serverUrl && config.token) {
    setStatus('已配置：' + config.serverUrl, 'ok')
  } else {
    setStatus('尚未配置服务器和 Token')
  }
}

toggleTokenButton.addEventListener('click', () => {
  const showing = tokenInput.type === 'text'
  tokenInput.type = showing ? 'password' : 'text'
  toggleTokenButton.textContent = showing ? '显示' : '隐藏'
})

testButton.addEventListener('click', async () => {
  setLoading(testButton, true, '测试中…')
  setStatus('正在连接服务器…')
  try {
    const response = await send({
      type: 'TEST_CONNECTION',
      serverUrl: serverInput.value,
      token: tokenInput.value,
    })
    if (response.ok) {
      const total = response.data ? response.data.total : 0
      setStatus('连接成功，当前共有 ' + total + ' 条书签', 'ok')
    } else {
      setStatus('连接失败：' + (response.error || '未知错误'), 'error')
    }
  } catch (error) {
    setStatus('连接失败：' + error.message, 'error')
  } finally {
    setLoading(testButton, false)
  }
})

saveButton.addEventListener('click', async () => {
  setLoading(saveButton, true, '保存中…')
  try {
    const response = await send({
      type: 'SAVE_CONFIG',
      serverUrl: serverInput.value,
      token: tokenInput.value,
      enabled: enabledInput.checked,
    })
    if (response.ok) {
      serverInput.value = response.data.serverUrl
      setStatus('配置已保存，插件已生效', 'ok')
    } else {
      setStatus('保存失败：' + (response.error || '未知错误'), 'error')
    }
  } catch (error) {
    setStatus('保存失败：' + error.message, 'error')
  } finally {
    setLoading(saveButton, false)
  }
})

openH5Button.addEventListener('click', async () => {
  const response = await send({ type: 'GET_CONFIG' })
  if (!response.ok || !response.data.serverUrl || !response.data.token) {
    setStatus('请先保存服务器地址和 Token', 'error')
    return
  }
  const url =
    response.data.serverUrl +
    '/#/h5?token=' +
    encodeURIComponent(response.data.token)
  chrome.tabs.create({ url })
})

loadConfig()
