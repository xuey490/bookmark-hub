<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listTags } from '../api/tags'
import type { TagCount } from '../types'

const router = useRouter()
const tags = ref<TagCount[]>([])
const loading = ref(false)
const keyword = ref('')

const colors = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta']

const filtered = computed(() => {
  const value = keyword.value.trim().toLowerCase()
  if (!value) return tags.value
  return tags.value.filter((item) => item.name.toLowerCase().includes(value))
})

const maxCount = computed(() =>
  tags.value.reduce((max, item) => Math.max(max, item.count), 1),
)

function go(name: string) {
  router.push({ path: '/bookmarks', query: { tag: name } })
}

onMounted(async () => {
  loading.value = true
  try {
    tags.value = await listTags()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">标签</h1>
        <p class="page-subtitle">共 {{ tags.length }} 个标签，点击任意标签筛选书签</p>
      </div>
      <a-input-search
        v-model:value="keyword"
        placeholder="过滤标签"
        allow-clear
        class="tag-search"
      />
    </div>

    <a-spin :spinning="loading">
      <a-card :bordered="false" class="tag-cloud-card">
        <div v-if="filtered.length" class="tag-cloud">
          <a-tag
            v-for="(item, index) in filtered"
            :key="item.name"
            :color="colors[index % colors.length]"
            class="tag-cloud__item"
            @click="go(item.name)"
          >
            {{ item.name }}
            <span class="tag-cloud__count">{{ item.count }}</span>
          </a-tag>
        </div>
        <a-empty v-else description="还没有标签，保存书签时添加标签即可" />
      </a-card>

      <a-card
        v-if="tags.length"
        :bordered="false"
        title="热门标签"
        class="tag-rank-card"
      >
        <div v-for="item in tags.slice(0, 10)" :key="item.name" class="rank-row">
          <span class="rank-name" @click="go(item.name)">{{ item.name }}</span>
          <a-progress
            :percent="Math.round((item.count / maxCount) * 100)"
            :show-info="false"
            size="small"
            class="rank-progress"
          />
          <span class="rank-count">{{ item.count }}</span>
        </div>
      </a-card>
    </a-spin>
  </div>
</template>
