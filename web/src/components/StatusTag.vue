<script setup lang="ts">
import { computed } from 'vue'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons-vue'
import type { BookmarkStatus } from '../types'
import { timeAgo } from '../utils/format'

const props = defineProps<{
  status: BookmarkStatus
  httpStatus?: number | null
  lastError?: string | null
  lastCheckedAt?: string | null
}>()

const meta = computed(() => {
  switch (props.status) {
    case 'ok':
      return { label: '正常', color: 'success', icon: CheckCircleOutlined }
    case 'error':
      return { label: '异常', color: 'error', icon: CloseCircleOutlined }
    case 'timeout':
      return { label: '超时', color: 'warning', icon: ClockCircleOutlined }
    default:
      return { label: '未检测', color: 'default', icon: QuestionCircleOutlined }
  }
})

const tipLines = computed(() => {
  const lines: string[] = []
  if (props.httpStatus) lines.push(`HTTP ${props.httpStatus}`)
  if (props.lastError) lines.push(props.lastError)
  lines.push(`检测时间：${timeAgo(props.lastCheckedAt ?? null)}`)
  return lines
})
</script>

<template>
  <a-tooltip>
    <template #title>
      <div v-for="line in tipLines" :key="line">{{ line }}</div>
    </template>
    <a-tag :color="meta.color" class="status-tag">
      <component :is="meta.icon" />
      <span>{{ meta.label }}</span>
    </a-tag>
  </a-tooltip>
</template>

<style scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-inline-end: 0;
}
</style>
