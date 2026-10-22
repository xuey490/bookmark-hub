<script setup lang="ts">
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  KeyOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons-vue'
import {
  resetServerToken as requestTokenReset,
  updateServerToken,
} from '../api/auth'
import { clearToken, getToken, setToken } from '../api/token'

const MIN_TOKEN_LENGTH = 16
const MAX_TOKEN_LENGTH = 128

const currentToken = ref(getToken())
const newToken = ref('')
const saving = ref(false)
const resetting = ref(false)

const maskedToken = computed(() => {
  const value = currentToken.value
  if (!value) return '未设置'
  if (value.length <= 12) return `${value.slice(0, 4)}…${value.slice(-2)}`
  return `${value.slice(0, 6)}…${value.slice(-4)}`
})

const tokenLength = computed(() => currentToken.value.length)

async function saveToken() {
  const value = newToken.value.trim()
  if (value.length < MIN_TOKEN_LENGTH) {
    message.warning(`Token 至少 ${MIN_TOKEN_LENGTH} 个字符`)
    return
  }
  if (/\s/.test(value)) {
    message.warning('Token 不能包含空格')
    return
  }
  if (value === currentToken.value) {
    message.info('新 Token 与当前 Token 相同')
    return
  }

  saving.value = true
  try {
    const result = await updateServerToken(value)
    setToken(result.token)
    currentToken.value = result.token
    newToken.value = ''
    message.success('服务端 Token 已更新，其他设备请使用新 Token')
  } catch {
    // The shared axios interceptor reports validation and network errors.
  } finally {
    saving.value = false
  }
}

async function rotateToken() {
  resetting.value = true
  try {
    const result = await requestTokenReset()
    setToken(result.token)
    currentToken.value = result.token
    message.success('服务端 Token 已重置，当前浏览器已自动更新')
  } catch {
    // The shared axios interceptor reports the failure.
  } finally {
    resetting.value = false
  }
}

function clearLocalToken() {
  clearToken()
  currentToken.value = ''
  newToken.value = ''
  message.success('已清除本地登录，请重新输入 Token')
}
</script>

<template>
  <div class="page settings-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Token 设置</h1>
        <p class="page-subtitle">
          管理服务端 API Token；修改后插件、H5 和其他浏览器需要同步更新
        </p>
      </div>
    </div>

    <a-card :bordered="false" class="settings-card">
      <h2 class="settings-title">
        <KeyOutlined /> 当前 Token
      </h2>
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="登录状态">
          <a-tag color="green">已登录</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="Token">
          <span class="token-mask">{{ maskedToken }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="长度">
          {{ tokenLength }} 个字符
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card :bordered="false" class="settings-card">
      <h2 class="settings-title">设置新的 Token</h2>
      <p class="settings-hint">
        自定义 Token 会立即替换服务端当前 Token。长度至少
        {{ MIN_TOKEN_LENGTH }} 个字符，不能包含空格。
      </p>
      <a-input-password
        v-model:value="newToken"
        size="large"
        :maxlength="MAX_TOKEN_LENGTH"
        placeholder="输入新的 Token"
        autocomplete="new-password"
        @press-enter="saveToken"
      />
      <div class="settings-actions">
        <a-space wrap>
          <a-button
            type="primary"
            :loading="saving"
            :disabled="!newToken.trim()"
            @click="saveToken"
          >
            <SaveOutlined /> 保存并应用
          </a-button>
          <a-button @click="clearLocalToken">清除本地登录</a-button>
        </a-space>
      </div>
    </a-card>

    <a-card :bordered="false" class="settings-card">
      <h2 class="settings-title">重置服务端 Token</h2>
      <a-alert
        type="warning"
        show-icon
        message="重置后会立即生成一个新的随机 Token"
        description="旧 Token 会立即失效，插件、H5 和其他浏览器需要重新配置 Token。当前浏览器会自动更新。"
      />
      <a-popconfirm
        title="确定重置服务端 Token？旧 Token 将立即失效。"
        ok-text="重置"
        cancel-text="取消"
        @confirm="rotateToken"
      >
        <a-button
          danger
          :loading="resetting"
          class="settings-reset-button"
        >
          <ReloadOutlined /> 重置 Token
        </a-button>
      </a-popconfirm>
    </a-card>
  </div>
</template>

<style scoped>
.settings-card {
  border-radius: 12px;
  margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.settings-title {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 600;
}

.settings-hint {
  margin: 0 0 14px;
  color: #8c8c8c;
  font-size: 13px;
  line-height: 1.7;
}

.settings-actions {
  margin-top: 16px;
}

.settings-reset-button {
  margin-top: 16px;
}

.token-mask {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono',
    monospace;
  letter-spacing: 0.4px;
}
</style>
