import { del, get, post, put } from './client'
import type { Category } from '../types'

export async function listCategories(): Promise<Category[]> {
  return get('/categories')
}

export async function createCategory(name: string): Promise<Category> {
  return post('/categories', { name })
}

export async function updateCategory(
  id: number,
  name: string,
): Promise<Category> {
  return put(`/categories/${id}`, { name })
}

export async function deleteCategory(id: number): Promise<void> {
  await del(`/categories/${id}`)
}
