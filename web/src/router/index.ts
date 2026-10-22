import { createRouter, createWebHashHistory } from 'vue-router'
import BasicLayout from '../layouts/BasicLayout.vue'
import BookmarksView from '../views/BookmarksView.vue'
import CategoriesView from '../views/CategoriesView.vue'
import H5View from '../views/H5View.vue'
import SettingsView from '../views/SettingsView.vue'
import StatsView from '../views/StatsView.vue'
import TagsView from '../views/TagsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      component: BasicLayout,
      children: [
        { path: '', redirect: '/bookmarks' },
        { path: 'bookmarks', name: 'bookmarks', component: BookmarksView },
        { path: 'categories', name: 'categories', component: CategoriesView },
        { path: 'tags', name: 'tags', component: TagsView },
        { path: 'stats', name: 'stats', component: StatsView },
        { path: 'settings', name: 'settings', component: SettingsView },
      ],
    },
    { path: '/h5', name: 'h5', component: H5View },
    { path: '/:pathMatch(.*)*', redirect: '/bookmarks' },
  ],
})

export default router
