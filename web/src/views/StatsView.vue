<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { SyncOutlined } from '@ant-design/icons-vue'
import type { Stats } from '../types'
import { checkAll } from '../api/bookmarks'
import { getStats } from '../api/stats'
import { formatTime, timeAgo } from '../utils/format'

const stats = ref<Stats | null>(null)
const loading = ref(false)
const checking = ref(false)

const abnormal = computed(
  () => (stats.value?.error ?? 0) + (stats.value?.timeout ?? 0),
)
const okPercent = computed(() => {
  if (!stats.value?.total) return 0
  return Math.round((stats.value.ok / stats.value.total) * 100)
})

async function load() {
  loading.value = true
  try {
    stats.value = await getStats()
  } finally {
    loading.value = false
  }
}

async function runCheck() {
  checking.value = true
  try {
    const result = await checkAll()
    message.success(
      `检测完成：共 ${result.checked} 条，正常 ${result.ok}，异常 ${result.error}，超时 ${result.timeout}`,
    )
    await load()
  } catch {
    // handled by interceptor
  } finally {
    checking.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">统计</h1>
        <p class="page-subtitle">
          最近检测：{{ timeAgo(stats?.last_check_at ?? null) }}
        </p>
      </div>
      <a-popconfirm
        title="将对全部书签执行连通性检测，可能需要几十秒，确认继续？"
        ok-text="开始检测"
        cancel-text="取消"
        @confirm="runCheck"
      >
        <a-button type="primary" :loading="checking">
          <SyncOutlined /> 立即检测全部
        </a-button>
      </a-popconfirm>
    </div>

    <a-spin :spinning="loading">
      <a-row :gutter="[16, 16]">
        <a-col :xs="12" :md="6">
          <a-card :bordered="false" class="stat-card">
            <a-statistic title="书签总数" :value="stats?.total ?? 0" />
          </a-card>
        </a-col>
        <a-col :xs="12" :md="6">
          <a-card :bordered="false" class="stat-card">
            <a-statistic
              title="正常"
              :value="stats?.ok ?? 0"
              :value-style="{ color: '#389e0d' }"
            />
          </a-card>
        </a-col>
        <a-col :xs="12" :md="6">
          <a-card :bordered="false" class="stat-card">
            <a-statistic
              title="异常 / 超时"
              :value="abnormal"
              :value-style="{ color: '#cf1322' }"
            />
          </a-card>
        </a-col>
        <a-col :xs="12" :md="6">
          <a-card :bordered="false" class="stat-card">
            <a-statistic
              title="未检测"
              :value="stats?.unknown ?? 0"
              :value-style="{ color: '#8c8c8c' }"
            />
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="[16, 16]" class="stat-row">
        <a-col :xs="24" :md="12">
          <a-card :bordered="false" title="健康度">
            <a-progress
              type="dashboard"
              :percent="okPercent"
              :stroke-color="okPercent >= 90 ? '#52c41a' : okPercent >= 70 ? '#faad14' : '#ff4d4f'"
            />
            <p class="stat-hint">
              正常书签占比 {{ okPercent }}%，异常和超时链接会在书签列表中标记红色/橙色标签。
            </p>
          </a-card>
        </a-col>
        <a-col :xs="24" :md="12">
          <a-card :bordered="false" title="内容概览">
            <div class="overview-row">
              <span>分类数量</span>
              <strong>{{ stats?.categories ?? 0 }}</strong>
            </div>
            <div class="overview-row">
              <span>标签数量</span>
              <strong>{{ stats?.tags ?? 0 }}</strong>
            </div>
            <div class="overview-row">
              <span>最近检测时间</span>
              <strong>{{ formatTime(stats?.last_check_at ?? null) }}</strong>
            </div>
            <div class="overview-row">
              <span>定时检测</span>
              <strong>由服务端定时执行</strong>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>
