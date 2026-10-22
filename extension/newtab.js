const dateElement = document.getElementById('date')
const loadingElement = document.getElementById('loading')
const gridElement = document.getElementById('grid')
const emptyElement = document.getElementById('empty')
const setupElement = document.getElementById('setup')
const errorElement = document.getElementById('error')
const errorText = document.getElementById('errorText')
const searchForm = document.getElementById('searchForm')
const searchInput = document.getElementById('searchInput')
const openAllButton = document.getElementById('openAll')
const openSettingsButton = document.getElementById('openSettings')
const setupButton = document.getElementById('setupButton')
const retryButton = document.getElementById('retryButton')

let config = null

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

function show(element) {
  ;[loadingElement, gridElement, emptyElement, setupElement, errorElement].forEach(
    (item) => item.classList.add('hidden'),
  )
  element.classList.remove('hidden')
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

const statusLabels = {
  ok: '正常',
  error: '异常',
  timeout: '超时',
  unknown: '未检测',
}

function renderCard(item) {
  const card = document.createElement('a')
  card.className = 'card'
  card.href = item.url
  card.target = '_blank'
  card.rel = 'noopener noreferrer'
  card.addEventListener('click', () => {
    send({ type: 'VISIT_BOOKMARK', id: item.id })
  })

  const head = document.createElement('div')
  head.className = 'card-head'

  const favicon = document.createElement('div')
  favicon.className = 'favicon'
  favicon.textContent = (hostOf(item.url)[0] || '?').toUpperCase()

  const title = document.createElement('div')
  title.className = 'card-title'
  title.textContent = item.title || hostOf(item.url)

  head.appendChild(favicon)
  head.appendChild(title)

  const meta = document.createElement('div')
  meta.className = 'card-meta'

  const badge = document.createElement('span')
  const status = item.status || 'unknown'
  badge.className = 'badge ' + status
  badge.textContent = statusLabels[status] || '未检测'
  meta.appendChild(badge)

  if (item.category && item.category.name) {
    const category = document.createElement('span')
    category.className = 'category'
    category.textContent = item.category.name
    meta.appendChild(category)
  }

  const visits = document.createElement('span')
  visits.className = 'visits'
  visits.textContent = `访问 ${item.visit_count || 0} 次`
  meta.appendChild(visits)

  const host = document.createElement('div')
  host.className = 'card-host'
  host.textContent = hostOf(item.url)

  card.appendChild(head)
  card.appendChild(meta)
  card.appendChild(host)
  return card
}

async function loadRecent() {
  show(loadingElement)
  const response = await send({ type: 'GET_RECENT', limit: 12 })
  if (!response.ok) {
    errorText.textContent = response.error || '请检查服务器是否可访问'
    show(errorElement)
    return
  }

  const items = response.data && response.data.items ? response.data.items : []
  if (!items.length) {
    show(emptyElement)
    return
  }

  gridElement.innerHTML = ''
  items.forEach((item) => gridElement.appendChild(renderCard(item)))
  show(gridElement)
}

function openH5(search) {
  if (!config || !config.serverUrl || !config.token) {
    chrome.tabs.create({ url: chrome.runtime.getURL('popup.html') })
    return
  }
  let url =
    config.serverUrl +
    '/#/h5?token=' +
    encodeURIComponent(config.token)
  if (search) url += '&q=' + encodeURIComponent(search)
  window.location.href = url
}

async function boot() {
  dateElement.textContent = new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })

  const response = await send({ type: 'GET_CONFIG' })
  if (!response.ok) {
    errorText.textContent = response.error || '读取插件配置失败'
    show(errorElement)
    return
  }

  config = response.data
  if (!config.serverUrl || !config.token) {
    show(setupElement)
    return
  }

  await loadRecent()
}

searchForm.addEventListener('submit', (event) => {
  event.preventDefault()
  openH5(searchInput.value.trim())
})

openAllButton.addEventListener('click', () => openH5(''))

openSettingsButton.addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('popup.html') })
})

setupButton.addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('popup.html') })
})

retryButton.addEventListener('click', () => {
  if (config && config.serverUrl && config.token) loadRecent()
  else boot()
})

boot()

chrome.storage.onChanged.addListener((changes) => {
  if ('serverUrl' in changes || 'token' in changes || 'enabled' in changes) {
    boot()
  }
})
