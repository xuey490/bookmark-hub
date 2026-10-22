import { del, get, post, put } from './client'
import type {
  Bookmark,
  BookmarkPayload,
  ListQuery,
  PageResult,
} from '../types'

export async function listBookmarks(
  params: ListQuery,
): Promise<PageResult<Bookmark>> {
  return get('/bookmarks', { params })
}

export async function getBookmark(id: number): Promise<Bookmark> {
  return get(`/bookmarks/${id}`)
}

export async function createBookmark(
  payload: BookmarkPayload,
): Promise<Bookmark> {
  return post('/bookmarks', payload)
}

export async function updateBookmark(
  id: number,
  payload: Partial<BookmarkPayload>,
): Promise<Bookmark> {
  return put(`/bookmarks/${id}`, payload)
}

export async function deleteBookmark(id: number): Promise<void> {
  await del(`/bookmarks/${id}`)
}

export async function deleteBookmarks(
  ids: number[],
): Promise<{ deleted: number }> {
  return post('/bookmarks/batch-delete', { ids })
}

export async function checkBookmark(id: number): Promise<Bookmark> {
  return post(`/bookmarks/${id}/check`)
}

export async function visitBookmark(id: number): Promise<Bookmark> {
  return post(`/bookmarks/${id}/visit`)
}

export async function checkAll(): Promise<{
  checked: number
  ok: number
  error: number
  timeout: number
  duration_ms: number
}> {
  return post('/check/urls', {})
}

export interface ImportResult {
  imported: number
  updated: number
  skipped: number
  failed: number
  errors: Array<{ url: string; reason: string }>
}

export async function importFile(
  file: File,
  mode: 'skip' | 'update',
): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('mode', mode)
  return post('/bookmarks/import', form, {
    timeout: 60000,
  })
}

export async function exportBookmarks(format: 'json' | 'html'): Promise<Blob> {
  return get('/bookmarks/export', { params: { format }, responseType: 'blob' })
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
