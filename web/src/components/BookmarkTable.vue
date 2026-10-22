<script setup lang="ts">
import { computed } from 'vue'
import {
  DeleteOutlined,
  EditOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import type { Bookmark } from '../types'
import StatusTag from './StatusTag.vue'
import { formatTime, hostOf, timeAgo } from '../utils/format'

const props = defineProps<{
  items: Bookmark[]
  loading: boolean
  checkingId: number | null
  selectedRowKeys: number[]
}>()

const emit = defineEmits<{
  edit: [bookmark: Bookmark]
  delete: [bookmark: Bookmark]
  check: [bookmark: Bookmark]
  visit: [bookmark: Bookmark]
  'tag-click': [tag: string]
  'update:selectedRowKeys': [keys: number[]]
}>()

const rowSelection = computed(() => ({
  selectedRowKeys: props.selectedRowKeys,
  fixed: 'left' as const,
  preserveSelectedRowKeys: false,
  onChange: (keys: (string | number)[]) => {
    emit('update:selectedRowKeys', keys.map((key) => Number(key)))
  },
}))

const columns = [
  { title: '标题', key: 'title', width: 320 },
  { title: '分类', key: 'category', width: 120 },
  { title: '标签', key: 'tags', width: 220 },
  { title: '访问次数', key: 'visits', width: 100, align: 'center' as const },
  { title: '状态', key: 'status', width: 110 },
  { title: '最近检测', key: 'checked', width: 130 },
  { title: '收藏时间', key: 'created', width: 130 },
  { title: '操作', key: 'actions', width: 140, align: 'right' as const },
]

function confirmDelete(bookmark: Bookmark) {
  emit('delete', bookmark)
}
</script>

<template>
  <a-table
    :columns="columns"
    :data-source="items"
    :loading="loading"
    :pagination="false"
    :row-selection="rowSelection"
    row-key="id"
    size="middle"
    :scroll="{ x: 1330 }"
  >
    <template #emptyText>
      <a-empty description="还没有收藏，点击右上角新增，或安装 Chrome 插件开始收藏" />
    </template>

    <template #bodyCell="{ column, record }">
      <template v-if="column.key === 'title'">
        <a
          :href="record.url"
          target="_blank"
          rel="noopener noreferrer"
          class="bookmark-title"
          :title="record.url"
          @click="emit('visit', record)"
        >
          {{ record.title || hostOf(record.url) }}
        </a>
        <div class="bookmark-host">{{ hostOf(record.url) }}</div>
        <a-tooltip
          :title="
            record.last_visited_at
              ? formatTime(record.last_visited_at)
              : '尚未访问'
          "
        >
          <div class="bookmark-last-visit">
            {{
              record.last_visited_at
                ? `上次访问：${timeAgo(record.last_visited_at)}`
                : '尚未访问'
            }}
          </div>
        </a-tooltip>
      </template>

      <template v-else-if="column.key === 'category'">
        <a-tag v-if="record.category" color="blue">
          {{ record.category.name }}
        </a-tag>
        <span v-else class="muted">—</span>
      </template>

      <template v-else-if="column.key === 'tags'">
        <template v-if="record.tags.length">
          <a-tag
            v-for="tag in record.tags.slice(0, 3)"
            :key="tag"
            class="clickable-tag"
            @click="emit('tag-click', tag)"
          >
            {{ tag }}
          </a-tag>
          <a-tooltip v-if="record.tags.length > 3" :title="record.tags.join('、')">
            <a-tag>+{{ record.tags.length - 3 }}</a-tag>
          </a-tooltip>
        </template>
        <span v-else class="muted">—</span>
      </template>

      <template v-else-if="column.key === 'visits'">
        <span :class="{ muted: !record.visit_count }">
          {{ record.visit_count || 0 }}
        </span>
      </template>

      <template v-else-if="column.key === 'status'">
        <StatusTag
          :status="record.status"
          :http-status="record.http_status"
          :last-error="record.last_error"
          :last-checked-at="record.last_checked_at"
        />
      </template>

      <template v-else-if="column.key === 'checked'">
        <a-tooltip :title="record.last_checked_at || '尚未检测'">
          {{ timeAgo(record.last_checked_at) }}
        </a-tooltip>
      </template>

      <template v-else-if="column.key === 'created'">
        {{ timeAgo(record.created_at) }}
      </template>

      <template v-else-if="column.key === 'actions'">
        <a-space :size="2">
          <a-tooltip title="立即检测">
            <a-button
              type="text"
              size="small"
              :loading="checkingId === record.id"
              @click="emit('check', record)"
            >
              <ReloadOutlined />
            </a-button>
          </a-tooltip>
          <a-tooltip title="编辑">
            <a-button type="text" size="small" @click="emit('edit', record)">
              <EditOutlined />
            </a-button>
          </a-tooltip>
          <a-popconfirm
            title="确定删除该书签？"
            ok-text="删除"
            cancel-text="取消"
            @confirm="confirmDelete(record)"
          >
            <a-button type="text" size="small" danger>
              <DeleteOutlined />
            </a-button>
          </a-popconfirm>
        </a-space>
      </template>
    </template>
  </a-table>
</template>

<style scoped>
.bookmark-title {
  font-weight: 500;
  display: inline-block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.bookmark-host {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: 2px;
}
.bookmark-last-visit {
  color: #bfbfbf;
  font-size: 12px;
  margin-top: 2px;
}
.clickable-tag {
  cursor: pointer;
}
.muted {
  color: #bfbfbf;
}
</style>
