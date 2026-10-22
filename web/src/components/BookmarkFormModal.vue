<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import type { Bookmark, Category } from '../types'
import { createBookmark, updateBookmark } from '../api/bookmarks'
import TagInput from './TagInput.vue'

const props = defineProps<{
  open: boolean
  bookmark: Bookmark | null
  categories: Category[]
  width?: number | string
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  saved: []
}>()

const submitting = ref(false)
const urlError = ref('')

const form = reactive({
  url: '',
  title: '',
  categoryId: undefined as number | undefined,
  tags: [] as string[],
})

watch(
  () => props.open,
  (open) => {
    if (!open) return
    urlError.value = ''
    if (props.bookmark) {
      form.url = props.bookmark.url
      form.title = props.bookmark.title
      form.categoryId = props.bookmark.category?.id
      form.tags = [...props.bookmark.tags]
    } else {
      form.url = ''
      form.title = ''
      form.categoryId = undefined
      form.tags = []
    }
  },
)

function close() {
  emit('update:open', false)
}

function validate(): boolean {
  const value = form.url.trim()
  if (!value) {
    urlError.value = '请输入网址'
    return false
  }
  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol)) {
      urlError.value = '仅支持 http/https 网址'
      return false
    }
  } catch {
    urlError.value = '请输入合法的网址'
    return false
  }
  urlError.value = ''
  return true
}

async function submit() {
  if (!validate() || submitting.value) return

  submitting.value = true
  try {
    const payload = {
      url: form.url.trim(),
      title: form.title.trim(),
      category_id: form.categoryId ?? null,
      tags: form.tags,
    }
    if (props.bookmark) {
      await updateBookmark(props.bookmark.id, payload)
      message.success('书签已更新')
    } else {
      await createBookmark(payload)
      message.success('收藏成功')
    }
    emit('saved')
    close()
  } catch {
    // error messages are handled by the axios interceptor
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <a-modal
    :open="open"
    :title="bookmark ? '编辑书签' : '新增书签'"
    :width="width ?? 560"
    :confirm-loading="submitting"
    ok-text="保存"
    cancel-text="取消"
    destroy-on-close
    @ok="submit"
    @cancel="close"
  >
    <a-form layout="vertical" class="bookmark-form">
      <a-form-item
        label="网址"
        required
        :validate-status="urlError ? 'error' : undefined"
        :help="urlError || undefined"
      >
        <a-input
          v-model:value="form.url"
          placeholder="https://example.com/article"
          allow-clear
        />
      </a-form-item>

      <a-form-item label="标题">
        <a-input
          v-model:value="form.title"
          placeholder="留空则使用网页标题或域名"
          :maxlength="500"
          allow-clear
        />
      </a-form-item>

      <a-form-item label="分类">
        <a-select
          v-model:value="form.categoryId"
          placeholder="选择分类（可留空）"
          allow-clear
          show-search
          option-filter-prop="label"
        >
          <a-select-option
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
            :label="category.name"
          >
            {{ category.name }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="标签">
        <TagInput v-model="form.tags" :max="10" />
      </a-form-item>
    </a-form>

    <template #footer>
      <a-space>
        <a-button @click="close">取消</a-button>
        <a-button type="primary" :loading="submitting" @click="submit">
          保存
        </a-button>
      </a-space>
    </template>
  </a-modal>
</template>
