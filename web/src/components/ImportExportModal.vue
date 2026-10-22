<script setup lang="ts">
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  DownloadOutlined,
  InboxOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import {
  downloadBlob,
  exportBookmarks,
  importFile,
  type ImportResult,
} from '../api/bookmarks'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  imported: []
}>()

const selectedFile = ref<File | null>(null)
const mode = ref<'skip' | 'update'>('skip')
const importing = ref(false)
const exporting = ref(false)
const result = ref<ImportResult | null>(null)

const fileName = computed(() => selectedFile.value?.name ?? '')

function close() {
  emit('update:open', false)
}

function onBeforeUpload(file: File) {
  selectedFile.value = file
  result.value = null
  return false
}

function clearFile() {
  selectedFile.value = null
  result.value = null
}

async function runImport() {
  if (!selectedFile.value) {
    message.warning('请先选择 .json 或 .html 文件')
    return
  }
  importing.value = true
  try {
    result.value = await importFile(selectedFile.value, mode.value)
    message.success(
      `导入完成：新增 ${result.value.imported}，更新 ${result.value.updated}，跳过 ${result.value.skipped}`,
    )
    emit('imported')
  } catch {
    // handled by interceptor
  } finally {
    importing.value = false
  }
}

async function runExport(format: 'json' | 'html') {
  exporting.value = true
  try {
    const blob = await exportBookmarks(format)
    const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    downloadBlob(blob, `bookmarks-${stamp}.${format}`)
    message.success(`已导出 ${format.toUpperCase()} 文件`)
  } catch {
    // handled by interceptor
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <a-modal
    :open="props.open"
    title="导入 / 导出书签"
    :width="600"
    :footer="null"
    @cancel="close"
  >
    <a-divider orientation="left">导入</a-divider>

    <a-upload-dragger
      accept=".json,.html"
      :show-upload-list="false"
      :before-upload="onBeforeUpload"
      :disabled="importing"
    >
      <p class="ant-upload-drag-icon"><InboxOutlined /></p>
      <p class="ant-upload-text">点击或拖拽文件到这里</p>
      <p class="ant-upload-hint">
        支持本系统导出的 JSON 文件，以及 Chrome/Edge/Firefox 导出的 HTML 书签文件
      </p>
    </a-upload-dragger>

    <div v-if="selectedFile" class="selected-file">
      <span>已选择：{{ fileName }}</span>
      <a-button type="link" size="small" @click="clearFile">移除</a-button>
    </div>

    <div class="import-row">
      <a-radio-group v-model:value="mode">
        <a-radio value="skip">跳过已存在</a-radio>
        <a-radio value="update">覆盖更新</a-radio>
      </a-radio-group>
      <a-button
        type="primary"
        :loading="importing"
        :disabled="!selectedFile"
        @click="runImport"
      >
        <UploadOutlined /> 开始导入
      </a-button>
    </div>

    <a-alert
      v-if="result"
      class="import-result"
      type="info"
      show-icon
      :message="`新增 ${result.imported} 条，更新 ${result.updated} 条，跳过 ${result.skipped} 条，失败 ${result.failed} 条`"
    >
      <template v-if="result.errors.length" #description>
        <div v-for="item in result.errors.slice(0, 5)" :key="item.url">
          {{ item.url }}：{{ item.reason }}
        </div>
      </template>
    </a-alert>

    <a-divider orientation="left">导出</a-divider>
    <a-space wrap>
      <a-button :loading="exporting" @click="runExport('json')">
        <DownloadOutlined /> 导出 JSON
      </a-button>
      <a-button :loading="exporting" @click="runExport('html')">
        <DownloadOutlined /> 导出 HTML（浏览器书签格式）
      </a-button>
    </a-space>
    <p class="export-hint">
      导出文件不包含 Token，请妥善保管；HTML 文件可直接导入 Chrome 书签管理器。
    </p>
  </a-modal>
</template>

<style scoped>
.selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  color: #595959;
}
.import-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.import-result {
  margin-top: 16px;
}
.export-hint {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: 12px;
}
</style>
