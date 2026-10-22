<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  BarChartOutlined,
  BookOutlined,
  KeyOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  TagsOutlined,
} from '@ant-design/icons-vue'
import { clearToken, getToken } from '../api/token'
import TokenGate from '../components/TokenGate.vue'

const route = useRoute()
const router = useRouter()

const token = ref(getToken())
const collapsed = ref(false)
const selectedKeys = computed(() => [route.path])

function syncToken() {
  token.value = getToken()
}

onMounted(() => window.addEventListener('bookmark-auth-changed', syncToken))
onUnmounted(() =>
  window.removeEventListener('bookmark-auth-changed', syncToken),
)

function onMenuClick({ key }: { key: string | number }) {
  router.push(String(key))
}

function logout() {
  clearToken()
  token.value = ''
  if (route.path !== '/bookmarks') router.replace('/bookmarks')
}

const h5Url = computed(() => {
  // depend on token so the link refreshes after re-login
  void token.value
  const base = `${window.location.origin}${window.location.pathname}`
  return `${base}#/h5?token=${encodeURIComponent(getToken())}`
})
</script>

<template>
  <TokenGate v-if="!token" @saved="syncToken" />

  <a-layout v-else class="app-layout">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      :trigger="null"
      breakpoint="lg"
      :collapsed-width="0"
      class="app-sider"
    >
      <div class="brand">
        <span class="brand-mark">B</span>
        <span class="brand-name">Bookmark Hub</span>
      </div>
      <a-menu
        theme="dark"
        mode="inline"
        :selected-keys="selectedKeys"
        @click="onMenuClick"
      >
        <a-menu-item key="/bookmarks">
          <BookOutlined />
          <span>书签</span>
        </a-menu-item>
        <a-menu-item key="/categories">
          <AppstoreOutlined />
          <span>分类</span>
        </a-menu-item>
        <a-menu-item key="/tags">
          <TagsOutlined />
          <span>标签</span>
        </a-menu-item>
        <a-menu-item key="/stats">
          <BarChartOutlined />
          <span>统计</span>
        </a-menu-item>
        <a-menu-item key="/settings">
          <KeyOutlined />
          <span>Token 设置</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="app-header">
        <div class="header-left">
          <a-button
            type="text"
            class="sider-toggle"
            :title="collapsed ? '展开菜单' : '收起菜单'"
            @click="collapsed = !collapsed"
          >
            <MenuUnfoldOutlined v-if="collapsed" />
            <MenuFoldOutlined v-else />
          </a-button>
          <span class="header-title">网络书签</span>
        </div>
        <a-space :size="4">
          <a-button
            type="link"
            :href="h5Url"
            target="_blank"
            class="h5-link"
          >
            H5 临时访问
          </a-button>
          <a-button type="link" class="logout-link" @click="logout">
            <LogoutOutlined />
            <span class="logout-text">退出</span>
          </a-button>
        </a-space>
      </a-layout-header>

      <a-layout-content class="app-content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>
