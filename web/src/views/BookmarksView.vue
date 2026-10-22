<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  DeleteOutlined,
  ImportOutlined,
  PlusOutlined,
} from '@ant-design/icons-vue'
import type {
  Bookmark,
  BookmarkStatus,
  Category,
  TagCount,
} from '../types'
import {
  checkBookmark,
  deleteBookmark,
  deleteBookmarks,
  listBookmarks,
  visitBookmark,
} from '../api/bookmarks'
import { listCategories } from '../api/categories'
import { listTags } from '../api/tags'
import BookmarkTable from '../components/BookmarkTable.vue'
import BookmarkFormModal from '../components/BookmarkFormModal.vue'
import ImportExportModal from '../components/ImportExportModal.vue'

const route = useRoute()
const router = useRouter()

const items = ref<Bookmark[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const q = ref('')
const categoryId = ref<number | undefined>(undefined)
const status = ref<BookmarkStatus | undefined>(undefined)
const tag = ref<string | undefined>(undefined)
const sort = ref<'created_at_desc' | 'updated_at_desc' | 'title_asc'>(
  'created_at_desc',
)

const categories = ref<Category[]>([])
const tags = ref<TagCount[]>([])

const formOpen = ref(false)
const editing = ref<Bookmark | null>(null)
const importOpen = ref(false)
const checkingId = ref<number | null>(null)
const selectedRowKeys = ref<number[]>([])
const deleting = ref(false)

let searchTimer: number | undefined

function tagFromRoute(): string | undefined {
  const value = route.query.tag
  return typeof value === 'string' && value ? value : undefined
}

async function load() {
  selectedRowKeys.value = []
  loading.value = true
  try {
    const result = await listBookmarks({
      page: page.value,
      page_size: pageSize.value,
      q: q.value.trim() || undefined,
      category_id: categoryId.value || undefined,
      status: status.value,
      tag: tag.value,
      sort: sort.value,
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

async function loadMeta() {
  try {
    const [categoryList, tagList] = await Promise.all([
      listCategories(),
      listTags(),
    ])
    categories.value = categoryList
    tags.value = tagList
  } catch {
    // interceptor already reports the failure
  }
}

function resetAndLoad() {
  if (page.value !== 1) page.value = 1
  else load()
}

watch(q, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(resetAndLoad, 300)
})

watch([categoryId, status, sort], resetAndLoad)
watch([page, pageSize], () => load())

watch(
  () => route.query.tag,
  () => {
    tag.value = tagFromRoute()
    resetAndLoad()
  },
)

onMounted(async () => {
  tag.value = tagFromRoute()
  await Promise.all([loadMeta(), load()])
})

function openCreate() {
  editing.value = null
  formOpen.value = true
}

function openEdit(bookmark: Bookmark) {
  editing.value = bookmark
  formOpen.value = true
}

async function onSaved() {
  formOpen.value = false
  await Promise.all([load(), loadMeta()])
}

async function onDelete(bookmark: Bookmark) {
  await deleteBookmark(bookmark.id)
  message.success('已删除')
  if (items.value.length === 1 && page.value > 1) {
    page.value -= 1
  } else {
    await load()
  }
  await loadMeta()
}

async function onBatchDelete() {
  const ids = [...selectedRowKeys.value]
  if (!ids.length) return

  deleting.value = true
  try {
    const result = await deleteBookmarks(ids)
    if (result.deleted > 0) {
      message.success(`已删除 ${result.deleted} 条书签`)
    } else {
      message.warning('选中的书签已不存在')
    }

    if (ids.length >= items.value.length && page.value > 1) {
      page.value -= 1
    } else {
      await load()
    }
    await loadMeta()
  } catch {
    // interceptor already reports the failure
  } finally {
    deleting.value = false
  }
}

async function onCheck(bookmark: Bookmark) {
  checkingId.value = bookmark.id
  try {
    const updated = await checkBookmark(bookmark.id)
    const index = items.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) items.value[index] = updated
    const text: Record<string, string> = {
      ok: '连接正常',
      error: '连接异常',
      timeout: '连接超时',
      unknown: '未检测',
    }
    message.success(`检测完成：${text[updated.status] ?? updated.status}`)
  } catch {
    // interceptor handles
  } finally {
    checkingId.value = null
  }
}

async function onVisit(bookmark: Bookmark) {
  try {
    const updated = await visitBookmark(bookmark.id)
    const index = items.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) items.value[index] = updated
  } catch {
    // Navigation must not be blocked by visit tracking failures.
  }
}

function applyTag(value: string | undefined) {
  const query = { ...route.query }
  if (value) query.tag = value
  else delete query.tag
  router.replace({ path: '/bookmarks', query })
}

function onTagClick(value: string) {
  applyTag(value)
}

function onImported() {
  importOpen.value = false
  load()
  loadMeta()
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">书签</h1>
        <p class="page-subtitle">共 {{ total }} 条收藏，异常链接会自动标记</p>
      </div>
      <a-space wrap>
        <a-button @click="importOpen = true">
          <ImportOutlined /> 导入 / 导出
        </a-button>
        <a-button type="primary" @click="openCreate">
          <PlusOutlined /> 新增书签
        </a-button>
      </a-space>
    </div>

    <a-card :bordered="false" class="filter-card">
      <div class="filters">
        <a-input-search
          v-model:value="q"
          placeholder="搜索标题或网址"
          allow-clear
          class="filter-search"
        />
        <a-select
          v-model:value="categoryId"
          placeholder="全部分类"
          allow-clear
          class="filter-select"
        >
          <a-select-option
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </a-select-option>
        </a-select>
        <a-select
          v-model:value="status"
          placeholder="全部状态"
          allow-clear
          class="filter-select"
        >
          <a-select-option value="ok">正常</a-select-option>
          <a-select-option value="error">异常</a-select-option>
          <a-select-option value="timeout">超时</a-select-option>
          <a-select-option value="unknown">未检测</a-select-option>
        </a-select>
        <a-select
          v-model:value="tag"
          placeholder="全部标签"
          allow-clear
          show-search
          class="filter-select"
          @change="applyTag"
        >
          <a-select-option
            v-for="item in tags"
            :key="item.name"
            :value="item.name"
          >
            {{ item.name }} ({{ item.count }})
          </a-select-option>
        </a-select>
        <a-select v-model:value="sort" class="filter-select">
          <a-select-option value="created_at_desc">最新收藏</a-select-option>
          <a-select-option value="updated_at_desc">最近更新</a-select-option>
          <a-select-option value="title_asc">标题排序</a-select-option>
        </a-select>
      </div>
    </a-card>

    <a-card :bordered="false" class="table-card">
      <div class="table-toolbar">
        <div class="table-toolbar__info">
          <span class="muted">
            {{
              selectedRowKeys.length
                ? `已选 ${selectedRowKeys.length} 条`
                : '勾选左侧复选框可批量操作'
            }}
          </span>
          <a-button
            v-if="selectedRowKeys.length"
            type="link"
            size="small"
            @click="selectedRowKeys = []"
          >
            取消选择
          </a-button>
        </div>
        <a-popconfirm
          :title="`确定删除选中的 ${selectedRowKeys.length} 条书签？`"
          ok-text="删除"
          cancel-text="取消"
          :disabled="!selectedRowKeys.length"
          @confirm="onBatchDelete"
        >
          <a-button
            danger
            :disabled="!selectedRowKeys.length"
            :loading="deleting"
          >
            <DeleteOutlined /> 删除所选
          </a-button>
        </a-popconfirm>
      </div>

      <BookmarkTable
        v-model:selected-row-keys="selectedRowKeys"
        :items="items"
        :loading="loading"
        :checking-id="checkingId"
        @edit="openEdit"
        @delete="onDelete"
        @check="onCheck"
        @visit="onVisit"
        @tag-click="onTagClick"
      />

      <div class="table-footer">
        <span class="muted">共 {{ total }} 条</span>
        <a-pagination
          v-model:current="page"
          v-model:page-size="pageSize"
          :total="total"
          :show-size-changer="true"
          :page-size-options="['10', '20', '50', '100']"
        />
      </div>
    </a-card>

    <BookmarkFormModal
      v-model:open="formOpen"
      :bookmark="editing"
      :categories="categories"
      @saved="onSaved"
    />

    <ImportExportModal
      v-model:open="importOpen"
      @imported="onImported"
    />
  </div>
</template>
