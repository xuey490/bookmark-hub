<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import type { Bookmark, Category } from '../types'
import { deleteBookmark, listBookmarks, visitBookmark } from '../api/bookmarks'
import { listCategories } from '../api/categories'
import { clearToken, getToken, setToken } from '../api/token'
import BookmarkFormModal from '../components/BookmarkFormModal.vue'
import StatusTag from '../components/StatusTag.vue'
import { hostOf, timeAgo } from '../utils/format'

const route = useRoute()
const router = useRouter()

const hasToken = ref(false)
const tokenInput = ref('')
const tokenLoading = ref(false)

const items = ref<Bookmark[]>([])
const categories = ref<Category[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = ref('')
const categoryId = ref<number | undefined>(undefined)

const formOpen = ref(false)
const editing = ref<Bookmark | null>(null)

let searchTimer: number | undefined

async function load() {
  loading.value = true
  try {
    const result = await listBookmarks({
      page: page.value,
      page_size: pageSize.value,
      q: q.value.trim() || undefined,
      category_id: categoryId.value || undefined,
      sort: 'created_at_desc',
    })
    items.value = result.items
    total.value = result.total
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function init() {
  try {
    categories.value = await listCategories()
  } catch {
    categories.value = []
  }
  await load()
}

function reload() {
  if (page.value !== 1) page.value = 1
  else load()
}

watch(q, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(reload, 300)
})
watch(categoryId, reload)
watch(page, () => load())

async function saveToken() {
  const value = tokenInput.value.trim()
  if (!value) {
    message.warning('请输入 Token')
    return
  }
  tokenLoading.value = true
  setToken(value, false)
  try {
    await listBookmarks({ page: 1, page_size: 1 })
    hasToken.value = true
    tokenInput.value = ''
    message.success('连接成功')
    await init()
  } catch {
    hasToken.value = false
  } finally {
    tokenLoading.value = false
  }
}

function onAuthChanged() {
  hasToken.value = Boolean(getToken())
}

async function onSaved() {
  formOpen.value = false
  await load()
}

function openEdit(bookmark: Bookmark) {
  editing.value = bookmark
  formOpen.value = true
}

async function remove(bookmark: Bookmark) {
  try {
    await deleteBookmark(bookmark.id)
    message.success('已删除')
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    } else {
      await load()
    }
  } catch {
    // handled by interceptor
  }
}

async function recordVisit(bookmark: Bookmark) {
  try {
    const updated = await visitBookmark(bookmark.id)
    const index = items.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) items.value[index] = updated
  } catch {
    // Navigation must not be blocked by visit tracking failures.
  }
}

function logout() {
  clearToken()
  hasToken.value = false
}

onMounted(async () => {
  const queryToken =
    typeof route.query.token === 'string' ? route.query.token : ''
  const queryQ = typeof route.query.q === 'string' ? route.query.q : ''
  if (queryQ) q.value = queryQ
  if (queryToken) {
    setToken(queryToken, false)
    await router.replace({
      path: '/h5',
      query: queryQ ? { q: queryQ } : {},
    })
  }
  hasToken.value = Boolean(getToken())
  if (hasToken.value) await init()

  window.addEventListener('bookmark-auth-changed', onAuthChanged)
})

onUnmounted(() => {
  window.removeEventListener('bookmark-auth-changed', onAuthChanged)
})
</script>

<template>
  <div class="h5-page">
    <header class="h5-header">
      <div>
        <div class="h5-brand">Bookmark Hub</div>
        <div class="h5-sub">远程收藏夹 · 临时电脑访问</div>
      </div>
      <a-button
        v-if="hasToken"
        type="link"
        size="small"
        class="h5-logout"
        @click="logout"
      >
        退出
      </a-button>
    </header>

    <a-card v-if="!hasToken" :bordered="false" class="h5-token-card">
      <h2 class="h5-token-title">输入 Token</h2>
      <p class="h5-token-desc">
        Token 只保存在当前标签页会话中，关闭标签页即失效。建议在地址栏使用
        <code>#/h5?token=xxx</code> 一次性打开。
      </p>
      <a-input-password
        v-model:value="tokenInput"
        size="large"
        placeholder="API Token"
        @press-enter="saveToken"
      />
      <a-button
        type="primary"
        block
        size="large"
        class="h5-token-button"
        :loading="tokenLoading"
        @click="saveToken"
      >
        打开收藏夹
      </a-button>
    </a-card>

    <template v-else>
      <div class="h5-toolbar">
        <a-input-search
          v-model:value="q"
          placeholder="搜索标题或网址"
          allow-clear
        />
        <a-select
          v-model:value="categoryId"
          placeholder="全部分类"
          allow-clear
        >
          <a-select-option
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </a-select-option>
        </a-select>
      </div>

      <a-spin :spinning="loading">
        <div v-if="items.length" class="h5-list">
          <a-card
            v-for="item in items"
            :key="item.id"
            :bordered="false"
            class="h5-item-card"
          >
            <div class="h5-item-head">
              <a
                :href="item.url"
                target="_blank"
                rel="noopener noreferrer"
                class="h5-item-title"
                @click="recordVisit(item)"
              >
                {{ item.title || hostOf(item.url) }}
              </a>
              <StatusTag
                :status="item.status"
                :http-status="item.http_status"
                :last-error="item.last_error"
                :last-checked-at="item.last_checked_at"
              />
            </div>
            <div class="h5-item-host">{{ hostOf(item.url) }}</div>
            <div class="h5-item-meta">
              <a-tag v-if="item.category" color="blue">
                {{ item.category.name }}
              </a-tag>
              <a-tag v-for="tag in item.tags" :key="tag">{{ tag }}</a-tag>
              <span class="h5-item-visits">
                访问 {{ item.visit_count || 0 }} 次
              </span>
              <span class="h5-item-time">{{ timeAgo(item.created_at) }}</span>
            </div>
            <div class="h5-item-actions">
              <a-button size="small" @click="openEdit(item)">编辑</a-button>
              <a-popconfirm
                title="确定删除该书签？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="remove(item)"
              >
                <a-button size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </a-card>
        </div>
        <a-empty v-else description="没有收藏，或筛选条件无结果" />

        <div class="h5-footer">
          <a-pagination
            v-model:current="page"
            v-model:page-size="pageSize"
            :total="total"
            :show-size-changer="false"
            :simple="true"
          />
        </div>
      </a-spin>
    </template>

    <BookmarkFormModal
      v-model:open="formOpen"
      :bookmark="editing"
      :categories="categories"
      width="92vw"
      @saved="onSaved"
    />
  </div>
</template>
