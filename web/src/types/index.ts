export type BookmarkStatus = 'unknown' | 'ok' | 'error' | 'timeout'

export interface Category {
  id: number
  name: string
  bookmark_count?: number
  created_at?: string
}

export interface Bookmark {
  id: number
  url: string
  title: string
  category: Pick<Category, 'id' | 'name'> | null
  tags: string[]
  status: BookmarkStatus
  http_status: number | null
  response_ms: number | null
  last_error: string | null
  last_checked_at: string | null
  visit_count: number
  last_visited_at: string | null
  description?: string | null
  cover_url?: string | null
  screenshot_url?: string | null
  created_at: string
  updated_at: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface TagCount {
  name: string
  count: number
}

export interface Stats {
  total: number
  ok: number
  error: number
  timeout: number
  unknown: number
  categories: number
  tags: number
  last_check_at: string | null
}

export interface BookmarkPayload {
  url: string
  title?: string
  category_id?: number | null
  tags?: string[]
}

export interface ListQuery {
  page?: number
  page_size?: number
  q?: string
  category_id?: number
  tag?: string
  status?: BookmarkStatus
  sort?: 'created_at_desc' | 'updated_at_desc' | 'title_asc'
}
