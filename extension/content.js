(() => {
  const HOST_ID = 'bookmark-hub-extension-root'
  if (window.top !== window) return
  if (document.getElementById(HOST_ID)) return

  const state = {
    config: null,
    categories: [],
    categoriesLoadedAt: 0,
    tags: [],
    dialogOpen: false,
    dragging: null,
    toastTimer: null,
  }

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

  const styles = `
    :host { all: initial; }
    * { box-sizing: border-box; }
    .fab {
      width: 50px; height: 50px; border: none; border-radius: 50%;
      background: linear-gradient(135deg, #1677ff, #4096ff);
      color: #fff; cursor: pointer; display: flex; align-items: center;
      justify-content: center; box-shadow: 0 8px 24px rgba(22, 119, 255, .38);
      transition: transform .15s ease, box-shadow .15s ease;
      padding: 0; touch-action: none; user-select: none;
    }
    .fab:hover { transform: translateY(-1px) scale(1.03); box-shadow: 0 10px 28px rgba(22, 119, 255, .45); }
    .fab:active { transform: scale(.97); }
    .fab svg { width: 26px; height: 26px; pointer-events: none; }
    .fab.attached { background: linear-gradient(135deg, #52c41a, #73d13d); box-shadow: 0 8px 24px rgba(82, 196, 26, .38); }
    .overlay {
      position: fixed; inset: 0; z-index: 1; background: rgba(15, 23, 42, .45);
      display: flex; align-items: center; justify-content: center; padding: 20px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
      backdrop-filter: blur(2px);
    }
    .overlay.hidden { display: none; }
    .panel {
      width: 420px; max-width: 100%; max-height: calc(100vh - 40px); overflow-y: auto;
      background: #fff; border-radius: 16px; padding: 20px 20px 16px;
      box-shadow: 0 24px 64px rgba(15, 23, 42, .3); color: #1f1f1f;
      animation: bh-pop .18s ease;
    }
    @keyframes bh-pop { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: none; } }
    .panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .panel-title { font-size: 17px; font-weight: 650; }
    .icon-btn {
      border: none; background: transparent; font-size: 22px; line-height: 1;
      color: #8c8c8c; cursor: pointer; padding: 4px 6px; border-radius: 6px;
    }
    .icon-btn:hover { background: #f5f5f5; color: #1f1f1f; }
    .field { margin-top: 14px; }
    .field label { display: block; font-size: 12px; color: #8c8c8c; margin-bottom: 6px; }
    .url {
      font-size: 12px; color: #595959; background: #fafafa; border: 1px solid #f0f0f0;
      border-radius: 8px; padding: 8px 10px; word-break: break-all; line-height: 1.5;
      max-height: 56px; overflow: auto;
    }
    input[type="text"], select {
      width: 100%; height: 36px; border: 1px solid #d9d9d9; border-radius: 8px;
      padding: 0 10px; font-size: 14px; color: #1f1f1f; background: #fff;
      outline: none; font-family: inherit;
    }
    input[type="text"]:focus, select:focus { border-color: #1677ff; box-shadow: 0 0 0 2px rgba(22,119,255,.1); }
    .tag-box {
      display: flex; flex-wrap: wrap; gap: 6px; min-height: 36px; padding: 4px 8px;
      border: 1px solid #d9d9d9; border-radius: 8px; cursor: text; align-items: center;
    }
    .tag-box:focus-within { border-color: #1677ff; box-shadow: 0 0 0 2px rgba(22,119,255,.1); }
    .tag-box input[type="text"] { border: none; height: 26px; padding: 0; flex: 1; min-width: 130px; box-shadow: none; }
    .tag-box input[type="text"]:focus { box-shadow: none; }
    .tag {
      display: inline-flex; align-items: center; gap: 4px; background: #e6f4ff;
      color: #0958d9; border-radius: 6px; padding: 2px 8px; font-size: 12px;
    }
    .tag button { border: none; background: transparent; color: #0958d9; cursor: pointer; padding: 0; font-size: 14px; line-height: 1; }
    .error {
      margin-top: 12px; background: #fff2f0; border: 1px solid #ffccc7; color: #cf1322;
      border-radius: 8px; padding: 8px 10px; font-size: 12px; line-height: 1.5;
    }
    .error.hidden { display: none; }
    .panel-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
    .btn {
      height: 36px; padding: 0 16px; border-radius: 8px; border: 1px solid #d9d9d9;
      background: #fff; color: #1f1f1f; cursor: pointer; font-size: 14px; font-family: inherit;
    }
    .btn:hover { border-color: #1677ff; color: #1677ff; }
    .btn.primary { background: #1677ff; border-color: #1677ff; color: #fff; }
    .btn.primary:hover { background: #4096ff; border-color: #4096ff; color: #fff; }
    .btn:disabled { opacity: .6; cursor: not-allowed; }
    .panel-foot { text-align: right; color: #bfbfbf; font-size: 11px; margin-top: 8px; }
    .toast {
      position: fixed; right: 24px; bottom: 92px; z-index: 2; background: rgba(15, 23, 42, .92);
      color: #fff; font-size: 13px; padding: 9px 14px; border-radius: 8px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, .25); max-width: 300px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
      opacity: 0; transform: translateY(6px); transition: opacity .2s, transform .2s;
      pointer-events: none;
    }
    .toast.show { opacity: 1; transform: none; }
    .toast.error { background: rgba(207, 19, 34, .95); }
  `

  const panelHtml = `
    <div class="overlay hidden" id="bh-overlay">
      <div class="panel" role="dialog" aria-modal="true" aria-label="收藏到 Bookmark Hub">
        <div class="panel-head">
          <div class="panel-title">收藏到 Bookmark Hub</div>
          <button class="icon-btn" id="bh-close" type="button" title="关闭">×</button>
        </div>

        <div class="field">
          <label>网址</label>
          <div class="url" id="bh-url"></div>
        </div>

        <div class="field">
          <label>标题</label>
          <input type="text" id="bh-title" maxlength="500" placeholder="留空则使用网页标题或域名">
        </div>

        <div class="field">
          <label>分类</label>
          <select id="bh-category">
            <option value="">不分类</option>
          </select>
        </div>

        <div class="field">
          <label>标签</label>
          <div class="tag-box" id="bh-tag-box">
            <span id="bh-tag-list"></span>
            <input type="text" id="bh-tag-input" placeholder="回车或逗号添加，最多 10 个">
          </div>
        </div>

        <div class="error hidden" id="bh-error"></div>

        <div class="panel-actions">
          <button class="btn" id="bh-cancel" type="button">取消</button>
          <button class="btn primary" id="bh-save" type="button">保存</button>
        </div>
        <div class="panel-foot">Ctrl / ⌘ + Enter 保存 · Esc 关闭</div>
      </div>
    </div>
    <div class="toast" id="bh-toast"></div>
  `

  let host = null
  let shadow = null
  let fab = null
  let overlay = null
  let toast = null
  let tags = []

  function mount() {
    if (host) return

    host = document.createElement('div')
    host.id = HOST_ID
    host.style.cssText =
      'position: fixed; right: 24px; bottom: 28px; z-index: 2147483647;'

    const pos = state.config && state.config.buttonPos
    if (pos && Number.isFinite(pos.right) && Number.isFinite(pos.bottom)) {
      host.style.right = Math.max(8, pos.right) + 'px'
      host.style.bottom = Math.max(8, pos.bottom) + 'px'
    }

    shadow = host.attachShadow({ mode: 'open' })
    shadow.innerHTML = `
      <style>${styles}</style>
      <button class="fab" id="bh-fab" type="button" title="收藏当前页面">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"></path>
        </svg>
      </button>
      ${panelHtml}
    `
    document.documentElement.appendChild(host)

    fab = shadow.getElementById('bh-fab')
    overlay = shadow.getElementById('bh-overlay')
    toast = shadow.getElementById('bh-toast')

    bindEvents()
  }

  function unmount() {
    if (!host) return
    host.remove()
    host = null
    shadow = null
    fab = null
    overlay = null
    toast = null
    state.dialogOpen = false
    tags = []
  }

  function bindEvents() {
    fab.addEventListener('pointerdown', onPointerDown)
    fab.addEventListener('pointermove', onPointerMove)
    fab.addEventListener('pointerup', onPointerUp)

    shadow.getElementById('bh-close').addEventListener('click', closeDialog)
    shadow.getElementById('bh-cancel').addEventListener('click', closeDialog)
    shadow.getElementById('bh-save').addEventListener('click', saveBookmark)

    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) closeDialog()
    })

    const tagInput = shadow.getElementById('bh-tag-input')
    tagInput.addEventListener('keydown', onTagKeydown)
    tagInput.addEventListener('blur', () => commitTags(false))
    shadow.getElementById('bh-tag-box').addEventListener('click', () => tagInput.focus())

    shadow.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && state.dialogOpen) {
        event.preventDefault()
        closeDialog()
      }
      if (
        state.dialogOpen &&
        (event.ctrlKey || event.metaKey) &&
        event.key === 'Enter'
      ) {
        event.preventDefault()
        saveBookmark()
      }
    })
  }

  function onPointerDown(event) {
    if (event.button !== 0) return
    state.dragging = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      right: parseFloat(getComputedStyle(host).right) || 24,
      bottom: parseFloat(getComputedStyle(host).bottom) || 28,
      moved: false,
    }
    fab.setPointerCapture(event.pointerId)
  }

  function onPointerMove(event) {
    const drag = state.dragging
    if (!drag || event.pointerId !== drag.pointerId) return
    const dx = event.clientX - drag.startX
    const dy = event.clientY - drag.startY
    if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true
    host.style.right = Math.max(8, drag.right - dx) + 'px'
    host.style.bottom = Math.max(8, drag.bottom - dy) + 'px'
  }

  function onPointerUp(event) {
    const drag = state.dragging
    if (!drag || event.pointerId !== drag.pointerId) return
    state.dragging = null

    if (drag.moved) {
      chrome.storage.local.set({
        buttonPos: {
          right: parseFloat(host.style.right) || 24,
          bottom: parseFloat(host.style.bottom) || 28,
        },
      })
      return
    }

    openDialog()
  }

  function showToast(text, isError = false) {
    if (!toast) return
    window.clearTimeout(state.toastTimer)
    toast.textContent = text
    toast.classList.toggle('error', isError)
    toast.classList.add('show')
    state.toastTimer = window.setTimeout(() => {
      toast.classList.remove('show')
    }, 2600)
  }

  function showError(text) {
    const element = shadow.getElementById('bh-error')
    if (!element) return
    if (text) {
      element.textContent = text
      element.classList.remove('hidden')
    } else {
      element.textContent = ''
      element.classList.add('hidden')
    }
  }

  function renderTags() {
    const list = shadow.getElementById('bh-tag-list')
    list.innerHTML = ''
    tags.forEach((tag, index) => {
      const chip = document.createElement('span')
      chip.className = 'tag'
      chip.textContent = tag

      const remove = document.createElement('button')
      remove.type = 'button'
      remove.textContent = '×'
      remove.title = '移除标签'
      remove.addEventListener('click', () => {
        tags.splice(index, 1)
        renderTags()
      })

      chip.appendChild(remove)
      list.appendChild(chip)
    })
  }

  function addTagsFromInput() {
    const input = shadow.getElementById('bh-tag-input')
    const raw = input.value.trim()
    if (!raw) return
    raw
      .split(',')
      .map((item) => item.trim().replace(/^#+/, ''))
      .filter(Boolean)
      .forEach((item) => {
        const value = item.slice(0, 20)
        if (tags.length >= 10) return
        if (!tags.some((tag) => tag.toLowerCase() === value.toLowerCase())) {
          tags.push(value)
        }
      })
    input.value = ''
    renderTags()
  }

  function commitTags(keepInput) {
    if (!shadow) return
    addTagsFromInput()
    if (!keepInput) {
      const input = shadow.getElementById('bh-tag-input')
      if (input) input.value = ''
    }
  }

  function onTagKeydown(event) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      event.stopPropagation()
      addTagsFromInput()
    } else if (
      event.key === 'Backspace' &&
      !event.target.value &&
      tags.length
    ) {
      tags.pop()
      renderTags()
    }
  }

  async function ensureCategories() {
    const select = shadow.getElementById('bh-category')
    if (!select) return
    const fresh = Date.now() - state.categoriesLoadedAt < 5 * 60 * 1000
    if (fresh && state.categories.length) return

    select.innerHTML = '<option value="">不分类</option>'
    const response = await send({ type: 'GET_CATEGORIES' })
    if (!response.ok) {
      showError('获取分类失败：' + (response.error || '请检查插件配置'))
      return
    }
    state.categories = Array.isArray(response.data) ? response.data : []
    state.categoriesLoadedAt = Date.now()

    for (const category of state.categories) {
      const option = document.createElement('option')
      option.value = String(category.id)
      option.textContent = category.name
      select.appendChild(option)
    }
  }

  async function openDialog() {
    if (!state.config || !state.config.serverUrl || !state.config.token) {
      showToast('请先点击浏览器工具栏的插件图标，配置服务器和 Token', true)
      return
    }
    if (!shadow) return

    state.dialogOpen = true
    tags = []
    renderTags()
    showError('')
    fab.classList.remove('attached')
    shadow.getElementById('bh-url').textContent = location.href
    shadow.getElementById('bh-title').value = (document.title || '').slice(0, 500)
    shadow.getElementById('bh-category').value = ''
    shadow.getElementById('bh-tag-input').value = ''
    overlay.classList.remove('hidden')
    document.documentElement.style.overflow = 'hidden'

    await ensureCategories()
    shadow.getElementById('bh-title').focus()
    shadow.getElementById('bh-title').select()
  }

  function closeDialog() {
    if (!shadow || !state.dialogOpen) return
    state.dialogOpen = false
    overlay.classList.add('hidden')
    document.documentElement.style.overflow = ''
  }

  async function saveBookmark() {
    if (!shadow || !state.dialogOpen) return
    commitTags()

    const title = shadow.getElementById('bh-title').value.trim().slice(0, 500)
    const categoryValue = shadow.getElementById('bh-category').value
    const payload = {
      url: location.href,
      title,
      category_id: categoryValue ? Number(categoryValue) : null,
      tags,
    }

    const saveButton = shadow.getElementById('bh-save')
    saveButton.disabled = true
    saveButton.textContent = '保存中…'
    showError('')

    try {
      const response = await send({ type: 'SAVE_BOOKMARK', payload })
      if (response.ok) {
        closeDialog()
        fab.classList.add('attached')
        showToast('已收藏到 Bookmark Hub')
      } else if (response.status === 409) {
        showError('这个网址已经收藏过了，可以在收藏夹中编辑分类或标签。')
      } else if (response.status === 401) {
        showError('Token 无效，请点击插件图标重新配置。')
      } else {
        showError(response.error || '保存失败')
      }
    } catch (error) {
      showError(error.message || '保存失败')
    } finally {
      saveButton.disabled = false
      saveButton.textContent = '保存'
    }
  }

  chrome.storage.onChanged.addListener((changes) => {
    if (
      !('enabled' in changes) &&
      !('serverUrl' in changes) &&
      !('token' in changes)
    ) {
      return
    }
    send({ type: 'GET_CONFIG' }).then((response) => {
      if (!response.ok) return
      state.config = response.data
      if (state.config.enabled === false) {
        unmount()
      } else {
        mount()
      }
    })
  })

  send({ type: 'GET_CONFIG' }).then((response) => {
    if (!response.ok) return
    state.config = response.data
    if (state.config.enabled !== false) mount()
  })
})()
