<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { Category } from '../types'
import {
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
} from '../api/categories'
import { formatDate } from '../utils/format'

const items = ref<Category[]>([])
const loading = ref(false)

const modalOpen = ref(false)
const editing = ref<Category | null>(null)
const name = ref('')
const error = ref('')
const saving = ref(false)

const columns = [
  { title: '分类名', key: 'name' },
  { title: '书签数', key: 'count', width: 120 },
  { title: '创建时间', key: 'created', width: 160 },
  { title: '操作', key: 'actions', width: 160, align: 'right' as const },
]

async function load() {
  loading.value = true
  try {
    items.value = await listCategories()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  name.value = ''
  error.value = ''
  modalOpen.value = true
}

function openEdit(category: Category) {
  editing.value = category
  name.value = category.name
  error.value = ''
  modalOpen.value = true
}

async function save() {
  const value = name.value.trim()
  if (!value) {
    error.value = '请输入分类名'
    return
  }
  if (value.length > 30) {
    error.value = '分类名不能超过 30 个字符'
    return
  }

  saving.value = true
  try {
    if (editing.value) {
      await updateCategory(editing.value.id, value)
      message.success('分类已更新')
    } else {
      await createCategory(value)
      message.success('分类已创建')
    }
    modalOpen.value = false
    await load()
  } catch {
    // handled by interceptor
  } finally {
    saving.value = false
  }
}

async function remove(category: Category) {
  try {
    await deleteCategory(category.id)
    message.success('分类已删除，原有书签变为未分类')
    await load()
  } catch {
    // handled by interceptor
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">分类</h1>
        <p class="page-subtitle">一书签最多属于一个分类，删除分类不会删除书签</p>
      </div>
      <a-button type="primary" @click="openCreate">
        <PlusOutlined /> 新建分类
      </a-button>
    </div>

    <a-card :bordered="false" class="table-card">
      <a-table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        :pagination="false"
        row-key="id"
        size="middle"
      >
        <template #emptyText>
          <a-empty description="还没有分类" />
        </template>

        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a-tag color="blue">{{ record.name }}</a-tag>
          </template>
          <template v-else-if="column.key === 'count'">
            {{ record.bookmark_count ?? 0 }}
          </template>
          <template v-else-if="column.key === 'created'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="openEdit(record)">
                重命名
              </a-button>
              <a-popconfirm
                title="删除分类后，该书签将变为未分类，确认删除？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="remove(record)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:open="modalOpen"
      :title="editing ? '重命名分类' : '新建分类'"
      :confirm-loading="saving"
      ok-text="保存"
      cancel-text="取消"
      @ok="save"
    >
      <a-form layout="vertical">
        <a-form-item
          label="分类名"
          required
          :validate-status="error ? 'error' : undefined"
          :help="error || undefined"
        >
          <a-input
            v-model:value="name"
            placeholder="例如：技术、工具、学习"
            :maxlength="30"
            show-count
            @press-enter="save"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>
