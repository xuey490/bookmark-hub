<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { listBookmarks } from '../api/bookmarks'
import { setToken } from '../api/token'

const emit = defineEmits<{
  saved: []
}>()

const value = ref('Uhr5-HU3Nzqk5jYm54143xgqTHpoq1dpZYUBrux_jZY')
const loading = ref(false)

async function submit() {
  const token = value.value.trim()
  if (!token) {
    message.warning('请输入 API Token')
    return
  }

  loading.value = true
  setToken(token)
  try {
    await listBookmarks({ page: 1, page_size: 1 })
    message.success('连接成功')
    emit('saved')
  } catch {
    // 401 is handled by the axios interceptor, which clears the token
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="token-gate">
    <a-card class="token-card" :bordered="false">
      <div class="token-brand">Bookmark Hub</div>
      <p class="token-desc">输入服务器生成的 API Token，开始管理你的远程收藏夹。</p>

      <a-input-password
        v-model:value="value"
        size="large"
        placeholder="API Token"
        @press-enter="submit"
      />

      <a-button
        type="primary"
        size="large"
        block
        :loading="loading"
        class="token-submit"
        @click="submit"
      >
        连接
      </a-button>

      <a-alert
        type="info"
        show-icon
        message="Token 在哪里？"
        description="服务器首次启动时生成，位于 backend/data/api_token.txt，可执行 cat data/api_token.txt 查看。"
      />
    </a-card>
  </div>
</template>
